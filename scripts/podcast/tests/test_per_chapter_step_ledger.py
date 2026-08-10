#!/usr/bin/env python3
"""The per-chapter lane records one step per stage, with a duration each.

The chapter loop is the pipeline's longest phase — a measured median of 37 minutes
per chapter across 20 chapters — and until 2026-08-08 it recorded only that total.
So "where do the 37 minutes go" had no answer on disk, and the plan to answer it by
reading `duration_ms` after the next real book run could not have worked: no stage
inside a chapter wrote a step-ledger line at all.

These tests pin the five stages and, more importantly, the two properties that make
the records worth reading:

  * a stage that FAILS BY RETURNING — which is how this whole lane reports failure,
    each stage handing back a FAILED outcome object rather than raising — records
    `failed`, not `ok`. A ledger that calls a failed stage successful is worse than
    no ledger, and the plain `step()` context manager cannot see a return.
  * the chapter slug is on every record, because under `PER_CHAPTER_MAX_WORKERS`
    several chapters write to the same ledger at once and a duration nobody can
    attribute to a chapter measures nothing.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import phases.per_chapter as per_chapter  # noqa: E402
from _convergence import ChapterOutcome  # noqa: E402
from _step_ledger import last_by_step, read_steps, record_step  # noqa: E402

STAGES = ("extract", "framing", "lint", "build", "augment", "converge")


def _outcome(verdict: str = "SHIP-READY", notes: list[str] | None = None) -> ChapterOutcome:
    return ChapterOutcome(
        chapter_slug="a-chapter",
        final_verdict=verdict,
        outer_iterations=1,
        fixer_attempts=0,
        p0_remaining=0,
        p1_remaining=0,
        p2_remaining=0,
        notes=notes or [],
    )


class PerChapterStepLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "a-book"
        (self.book_dir / "chapters").mkdir(parents=True)
        (self.book_dir / "episodes").mkdir(parents=True)
        (self.book_dir / "_system" / "episode-drafts" / "EP01-a-chapter").mkdir(parents=True)
        (self.book_dir / "chapters" / "ch01-a-chapter.txt").write_text("Chapter text.\n", encoding="utf-8")
        (self.book_dir / "episodes" / "EP01-a-chapter.txt").write_text("Episode text.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_pass(
        self,
        *,
        run_rc: dict[str, int] | None = None,
        framing_raises: Exception | None = None,
        outcome: ChapterOutcome | None = None,
    ):
        """Drive per_chapter_pass with every subprocess and model call replaced."""
        rcs = run_rc or {}

        def _fake_run(argv, *a, **k):
            script = Path(str(argv[1])).name if len(argv) > 1 else ""
            return rcs.get(script, 0), "", "stderr detail"

        def _fake_framing(*a, **k):
            if framing_raises is not None:
                raise framing_raises

        with (
            mock.patch.object(per_chapter, "_run", _fake_run),
            mock.patch.object(per_chapter, "author_framing", _fake_framing),
            mock.patch.object(per_chapter, "_resolve_episode_id", lambda *a, **k: "EP01-a-chapter"),
            mock.patch.object(per_chapter, "converge_chapter", lambda *a, **k: outcome or _outcome()),
            mock.patch.object(per_chapter, "_info", lambda *_a, **_k: None),
        ):
            return per_chapter.per_chapter_pass(self.book_dir, "a-chapter")

    def _rows(self) -> dict[str, dict]:
        """{stage: its final record} for this single-chapter fixture.

        `last_by_step` keys per CHAPTER (`build[a-chapter]`) since 2026-08-09, so one
        chapter's success can no longer overwrite another's failure. This fixture drives
        exactly one chapter, so the discriminator is stripped back off here and every
        assertion below stays about the stages themselves. The per-chapter keying is
        pinned by `ChaptersDoNotCollapseTests` at the bottom of this file.
        """
        rows = last_by_step(read_steps(self.book_dir, phase=per_chapter.PHASE))
        return {key.split("[", 1)[0]: row for key, row in rows.items()}

    # ── the records exist, and carry what makes them useful ──────────────────

    def test_a_clean_chapter_records_every_stage(self) -> None:
        self._run_pass()
        self.assertEqual(sorted(self._rows()), sorted(STAGES))

    def test_every_record_carries_a_duration(self) -> None:
        self._run_pass()
        for name, row in self._rows().items():
            self.assertIn("duration_ms", row, f"{name} recorded no duration — the whole point of the record")
            self.assertGreaterEqual(row["duration_ms"], 0, name)

    def test_every_record_names_its_chapter(self) -> None:
        # Under workers, several chapters append to one ledger concurrently.
        self._run_pass()
        for name, row in self._rows().items():
            self.assertEqual(row.get("evidence", {}).get("chapter"), "a-chapter", f"{name} is unattributable")

    def test_the_convergence_record_carries_the_verdict_and_iteration_count(self) -> None:
        self._run_pass()
        ev = self._rows()["converge"]["evidence"]
        self.assertEqual(ev["verdict"], "SHIP-READY")
        self.assertEqual(ev["outer_iterations"], 1)

    # ── failure by RETURN, the property the context manager cannot see ───────

    def test_a_failed_extract_records_failed_and_stops_the_lane(self) -> None:
        out = self._run_pass(run_rc={"extract_chapter.py": 2})
        self.assertEqual(out.final_verdict, "FAILED")
        rows = self._rows()
        self.assertEqual(rows["extract"]["outcome"], "failed")
        self.assertIn("rc=2", rows["extract"]["error"])
        for later in ("framing", "lint", "build", "converge"):
            self.assertNotIn(later, rows, f"{later} recorded a step after extract failed")

    def test_a_failed_build_records_failed(self) -> None:
        out = self._run_pass(run_rc={"build_episode_txt.py": 3})
        self.assertEqual(out.final_verdict, "FAILED")
        self.assertEqual(self._rows()["build"]["outcome"], "failed")

    def test_a_structural_lint_failure_records_failed(self) -> None:
        out = self._run_pass(run_rc={"pipeline_lint.py": 1})
        self.assertEqual(out.final_verdict, "FAILED")
        self.assertEqual(self._rows()["lint"]["outcome"], "failed")

    def test_a_lint_that_could_not_run_is_not_recorded_as_a_pass(self) -> None:
        """Exit 1 is the gate speaking; anything else non-zero is it never having run.

        `pipeline_lint.main` returns 2 for a missing book-dir and argparse exits 2 for a
        bad `--episode`. Only exit 1 was handled, so a validator that never started fell
        through, the step recorded `ok`, and the chapter proceeded as though its framing
        had been checked — the exact silent-failure shape this ledger exists to expose.
        """
        out = self._run_pass(run_rc={"pipeline_lint.py": 2})
        self.assertEqual(self._rows()["lint"]["outcome"], "failed", "a gate that could not run reported a pass")
        self.assertEqual(out.final_verdict, "FAILED")
        self.assertTrue(
            any("could not run" in n for n in out.notes),
            f"the reason must say the gate did not run, got {out.notes!r}",
        )

    def test_a_lint_that_could_not_run_is_distinguished_from_a_real_mismatch(self) -> None:
        # Both fail the chapter, but a human triaging them does completely different
        # things: one is a framing to fix, the other is a broken invocation.
        could_not_run = self._run_pass(run_rc={"pipeline_lint.py": 2})
        self.setUp()
        mismatch = self._run_pass(run_rc={"pipeline_lint.py": 1})
        self.assertNotIn("could not run", " ".join(mismatch.notes))
        self.assertIn("could not run", " ".join(could_not_run.notes))

    def test_framing_that_raises_records_failed_with_its_message(self) -> None:
        from _authoring import AuthoringError

        out = self._run_pass(framing_raises=AuthoringError(phase="framing", message="model refused"))
        self.assertEqual(out.final_verdict, "FAILED")
        row = self._rows()["framing"]
        self.assertEqual(row["outcome"], "failed")
        self.assertIn("model refused", row["error"])

    def test_a_failed_convergence_records_failed_rather_than_ok(self) -> None:
        # The expensive one. A chapter that burned fifteen passes and lost must not
        # sit in the ledger looking like a chapter that succeeded in the same time.
        out = self._run_pass(outcome=_outcome("FAILED", notes=["unresolved P0: fabricated citation"]))
        self.assertEqual(out.final_verdict, "FAILED")
        row = self._rows()["converge"]
        self.assertEqual(row["outcome"], "failed")
        self.assertIn("fabricated citation", row["error"])

    # ── outcomes that are neither ok nor failed ──────────────────────────────

    def test_a_framing_cache_hit_is_recorded_as_noop_not_ok(self) -> None:
        # The distinction is the point: a cache hit and an LLM re-authoring take
        # wildly different time, and reading them both as "ok" hides which happened.
        draft = self.book_dir / "_system" / "episode-drafts" / "EP01-a-chapter"
        (draft / "00-framing.md").write_text("authored framing\n", encoding="utf-8")
        (draft / per_chapter._FRAMING_SIG_NAME).write_text(
            per_chapter._chapter_sig(self.book_dir / "chapters" / "ch01-a-chapter.txt"), encoding="utf-8"
        )
        self._run_pass()
        self.assertEqual(self._rows()["framing"]["outcome"], "noop")

    def test_an_unchanged_augment_is_recorded_as_noop(self) -> None:
        with mock.patch.dict(
            sys.modules,
            {"intelligence.augmenter": mock.MagicMock(augment_episode_text=lambda text, *a, **k: text)},
        ):
            self._run_pass()
        self.assertEqual(self._rows()["augment"]["outcome"], "noop")

    def test_an_unwritable_ledger_never_costs_the_chapter_its_result(self) -> None:
        # The records are an observer. Break the WRITE, not `record_step` itself:
        # `record_step` already swallows everything internally, so patching it with a
        # raising mock would have tested the mock and reported the guard as absent.
        blocked = self.book_dir / "_system" / "not-a-directory"
        blocked.write_text("", encoding="utf-8")
        with mock.patch("_step_ledger.ledger_path", lambda _bd: blocked / "step-ledger.jsonl"):
            out = self._run_pass()
        self.assertEqual(out.final_verdict, "SHIP-READY")
        self.assertEqual(self._rows(), {}, "nothing should have been recorded")


class ChaptersDoNotCollapseTests(unittest.TestCase):
    """One chapter's success must never overwrite another chapter's failure.

    Every chapter records the same six stage names under one phase, with the chapter
    only in the evidence. `last_by_step` keyed on the NAME alone until 2026-08-09, so a
    twenty-chapter book collapsed to six records — the LAST chapter's. Chapter three
    failing at `build` was overwritten by chapter twenty succeeding at it, and the review
    gate that reads this summary called the phase healthy.

    Those rows are different CHAPTERS, not retries of one step. Retry semantics are still
    correct and are pinned separately below.
    """

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "a-book"
        (self.book_dir / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _record(self, step_name: str, chapter: str, outcome: str) -> None:
        record_step(
            self.book_dir,
            phase=per_chapter.PHASE,
            step=step_name,
            outcome=outcome,
            evidence={"chapter": chapter},
        )

    def test_a_failed_chapter_survives_a_later_chapters_success(self) -> None:
        self._record("build", "ch03", "failed")
        for n in range(4, 21):
            self._record("build", f"ch{n:02d}", "ok")
        rows = last_by_step(read_steps(self.book_dir, phase=per_chapter.PHASE))
        self.assertEqual(len(rows), 18, "each chapter must keep its own record")
        self.assertEqual(rows["build[ch03]"]["outcome"], "failed", "chapter three's failure was overwritten")

    def test_every_chapter_keeps_every_stage(self) -> None:
        for chapter in ("ch01", "ch02", "ch03"):
            for stage in STAGES:
                self._record(stage, chapter, "ok")
        rows = last_by_step(read_steps(self.book_dir, phase=per_chapter.PHASE))
        self.assertEqual(len(rows), 3 * len(STAGES))

    def test_a_retry_of_the_same_chapter_still_reports_its_final_outcome(self) -> None:
        # The property the original keying was built for, and which must not be lost:
        # a stage that failed and was retried WITHIN one chapter reports the retry.
        self._record("build", "ch01", "failed")
        self._record("build", "ch01", "ok")
        rows = last_by_step(read_steps(self.book_dir, phase=per_chapter.PHASE))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows["build[ch01]"]["outcome"], "ok")

    def test_a_phase_whose_steps_name_no_chapter_keeps_the_bare_step_name(self) -> None:
        # Every other phase records one instance per step and reads its keys by bare
        # name — `_phase_review` looks up apparatus steps and `win-*` windows that way.
        record_step(self.book_dir, phase="0book-compose", step="inline-arabic", outcome="ok")
        rows = last_by_step(read_steps(self.book_dir, phase="0book-compose"))
        self.assertEqual(list(rows), ["inline-arabic"])


if __name__ == "__main__":
    unittest.main()
