#!/usr/bin/env python3
"""End-to-end coverage for the BOOK LANE, past the 0f gate.

`test_full_pipeline.py` drives `_drive_authoring_through_0f` and stops at the human
review gate. That covers eight of the pipeline's twenty-nine phases; everything
after the gate — the per-chapter loop, the whole book lane, finalize, publish,
trainer, merge — had no orchestration-level test at all. This file extends the same
strategy (a tiny synthetic book, the model-calling phases mocked) forward through
the book lane: 0book-design -> 0book-compose -> 0book-render.

It also pins the observability layer added on 2026-08-08, which is the point of
extending here rather than somewhere cheaper: the book lane is where the phase
review gates are actually declared, so this is the only place an end-to-end test can
prove that a phase completion really does produce a review and a step ledger. A
review architecture nothing exercises is the same "gate that cannot fail" this repo
keeps rediscovering.

The lane is NON-BLOCKING for the podcast by design — a book-phase failure records
itself and returns 0 — so the assertions are about recorded state and artifacts, not
about exit codes.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _progress
import phases.book_driver as book_driver
from _step_ledger import last_by_step, read_steps


class BookLaneE2ETests(unittest.TestCase):
    """The book lane advances design -> compose -> render and records what it did."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "tiny-book-lane"
        (self.book_dir / "_system" / "source" / "text").mkdir(parents=True)
        (self.book_dir / "book").mkdir(parents=True)

        # The lane reads refined-english.md as its source of truth.
        (self.book_dir / "_system" / "source" / "text" / "raw-extract.md").write_text(
            "Source paragraph one.\n\nSource paragraph two.\n" * 40, encoding="utf-8"
        )
        (self.book_dir / "_system" / "source" / "text" / "refined-english.md").write_text(
            "Refined paragraph one.\n\nRefined paragraph two.\n" * 40, encoding="utf-8"
        )

        # `series.enable_book_branch` is what opts a book into this lane at all.
        (self.book_dir / "meta.yml").write_text(
            "title: Tiny Book Lane\nseries:\n  enable_book_branch: true\n", encoding="utf-8"
        )

        state = _progress.initial_state("tiny-book-lane", "books")
        state["phase"] = "finalize"
        state["phase_status"] = "halted"
        for done in ("pre-flight", "branch", "scaffold", "0a", "0b", "0d"):
            state["phases"][done] = {"status": "completed"}
        _progress.write_state(self.book_dir, state)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ── mocks: everything that would call a model or render a PDF ────────────

    def _mock_design(self, book_dir: Path, log=print, **_kw) -> Path:
        out = Path(book_dir) / "book" / "book-toc.json"
        out.write_text(
            json.dumps(
                {
                    "book_title": "Tiny Book Lane",
                    "chapters": [
                        {"bk_index": 1, "title": "The First Chapter"},
                        {"bk_index": 2, "title": "The Second Chapter"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return out

    def _mock_compose(self, book_dir: Path, log=print, **_kw) -> Path:
        out = Path(book_dir) / "book" / "book.md"
        out.write_text(
            "# Tiny Book Lane\n\n## The First Chapter\n\nProse one.\n\n## The Second Chapter\n\nProse two.\n",
            encoding="utf-8",
        )
        return out

    def _mock_build_book(self, book_dir: Path, log=print, **_kw) -> Path:
        out = Path(book_dir) / "book" / "book.pdf"
        out.write_bytes(b"%PDF-1.4 mocked\n")
        return out

    def _mock_validate(self, book_dir: Path, **_kw) -> dict:
        return {"verdict": "BOOK-SOUND", "gates": [], "summary": "mocked validation"}

    def _drive(self) -> int:
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout_buf),
            redirect_stderr(stderr_buf),
            mock.patch.object(book_driver, "author_phase_book_design", self._mock_design),
            mock.patch.object(book_driver, "phase_git_commit", lambda *a, **k: None),
            mock.patch("_book_pipeline_v2.compose_book_v2", self._mock_compose),
            mock.patch("build_book_pdf.build_book", self._mock_build_book),
            mock.patch("validate_book_ready.validate_book", self._mock_validate),
            mock.patch("_pipeline_flags.book_visuals", lambda _bd: "manual_only"),
        ):
            return book_driver._drive_book_branch(self.book_dir)

    # ── phase advancement ────────────────────────────────────────────────────

    def test_the_lane_advances_design_compose_render(self):
        rc = self._drive()
        self.assertEqual(rc, 0, "the book lane is non-blocking and should return 0")
        state = _progress.read_state(self.book_dir)
        for phase in ("0book-design", "0book-compose", "0book-render"):
            self.assertEqual(
                state["phases"][phase]["status"],
                "completed",
                f"{phase} did not complete (status={state['phases'][phase].get('status')!r})",
            )

    def test_manual_visuals_skip_their_phases_with_a_recorded_reason(self):
        self._drive()
        state = _progress.read_state(self.book_dir)
        for phase in ("0book-illustrate", "0book-slide-import"):
            block = state["phases"][phase]
            self.assertEqual(block["status"], "skipped")
            self.assertIn("reason", block, f"{phase} was skipped without recording why")

    def test_the_artifacts_reach_disk(self):
        self._drive()
        for rel in ("book/book-toc.json", "book/book.md", "book/book.pdf"):
            self.assertTrue((self.book_dir / rel).exists(), f"{rel} was never written")

    # ── the observability layer (added 2026-08-08) ───────────────────────────

    def test_each_completed_phase_gets_a_review_report(self):
        self._drive()
        reviews = self.book_dir / "_system" / "phase-reviews"
        self.assertTrue(reviews.is_dir(), "no phase-reviews directory was created")
        for phase in ("0book-design", "0book-compose", "0book-render"):
            path = reviews / f"{phase}.json"
            self.assertTrue(path.exists(), f"no review report for {phase}")
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["phase"], phase)
            self.assertIn(report["verdict"], {"PHASE-SOUND", "PHASE-CONCERNS", "PHASE-BROKEN"})

    def test_the_review_summary_reaches_the_state_file(self):
        self._drive()
        state = _progress.read_state(self.book_dir)
        block = state["phases"]["0book-compose"]
        self.assertIn("review", block, "the compose phase completed without a review summary in state")
        self.assertIn("verdict", block["review"])
        self.assertIn("total", block["review"])

    def test_the_compose_review_rechecks_the_earlier_phases(self):
        self._drive()
        report = json.loads(
            (self.book_dir / "_system" / "phase-reviews" / "0book-compose.json").read_text(encoding="utf-8")
        )
        names = " ".join(g["name"] for g in report["gates"])
        for earlier in ("from 0a", "from 0b"):
            self.assertIn(earlier, names, f"the compose review did not re-verify {earlier}")

    def test_a_broken_earlier_artifact_is_reported_at_the_later_checkpoint(self):
        # The cross-phase request, end to end: 0a and 0b already completed, their
        # output is then destroyed, and the compose checkpoint must name it.
        (self.book_dir / "_system" / "source" / "text" / "refined-english.md").unlink()
        self._drive()
        report = json.loads(
            (self.book_dir / "_system" / "phase-reviews" / "0book-compose.json").read_text(encoding="utf-8")
        )
        failed = [g for g in report["gates"] if g["passed"] is False]
        self.assertTrue(
            any("0b" in g["name"] for g in failed),
            f"the destroyed 0b artifact was not reported; failures were {[g['name'] for g in failed]}",
        )
        self.assertEqual(report["verdict"], "PHASE-CONCERNS")

    def test_the_step_ledger_is_empty_here_because_compose_is_mocked(self):
        # Says out loud what this test does NOT cover. `compose_book_v2` is replaced
        # by a stub, so `_book_apparatus` never runs and none of its twenty-five
        # steps record. That is correct for a test about phase ADVANCEMENT, but it
        # would be easy to read the passing reviews above as proof the step ledger
        # works end to end. It is not: that is
        # `tests/test_apparatus_step_ledger_integration.py`, which runs the real
        # apparatus sequence. If this assertion ever starts failing, the lane has
        # gained a real step-recording path and this file should assert on it
        # properly rather than have the expectation flipped.
        self._drive()
        rows = read_steps(self.book_dir, phase="0book-compose")
        self.assertEqual(
            last_by_step(rows),
            {},
            "the book lane recorded steps that this test does not assert on — extend "
            "it rather than leaving the new path uncovered",
        )

    def test_the_review_never_turns_a_good_phase_into_a_failed_one(self):
        # A review is an observer. Even a crashing gate must leave the phase completed.
        import _phase_review as pr

        with mock.patch.dict(pr.OWN_GATES, {"0book-compose": [("PX", "explodes", lambda _bd: 1 / 0)]}):
            rc = self._drive()
        self.assertEqual(rc, 0)
        state = _progress.read_state(self.book_dir)
        self.assertEqual(state["phases"]["0book-compose"]["status"], "completed")

    def test_a_failing_lane_phase_is_recorded_rather_than_raised(self):
        # The lane must stay non-blocking: the podcast ships even if the book breaks.
        from _authoring import AuthoringError

        def _boom(book_dir, log=print, **_kw):
            raise AuthoringError(phase="0book-compose", message="mocked compose failure", manual_fallback="n/a")

        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout_buf),
            redirect_stderr(stderr_buf),
            mock.patch.object(book_driver, "author_phase_book_design", self._mock_design),
            mock.patch.object(book_driver, "phase_git_commit", lambda *a, **k: None),
            mock.patch("_book_pipeline_v2.compose_book_v2", _boom),
        ):
            rc = book_driver._drive_book_branch(self.book_dir)

        self.assertEqual(rc, 0, "a book-lane failure must not abort the run")
        state = _progress.read_state(self.book_dir)
        self.assertEqual(state["phases"]["0book-compose"]["status"], "failed")
        self.assertIn("mocked compose failure", json.dumps(state.get("last_error")))


if __name__ == "__main__":
    unittest.main()
