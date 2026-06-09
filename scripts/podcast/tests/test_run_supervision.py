"""Tests for the Phase E run-supervision & fast-fail system.

Covers:
  - preflight_chapter.smoke_check_chapter  ($0 deterministic gate)
  - cost_guard.cost_ceiling_check          (real-money $20/$50 ceiling)
  - chapter_driver circuit breaker         (halt-after-one on systemic failure)
  - supervise_run decision helpers         (terminal / systemic classification)
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_PODCAST = _REPO_ROOT / "scripts" / "podcast"
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))


def _make_book(tmp: Path, slugs: list[str], words: int = 600) -> Path:
    book = tmp / "book"
    (book / "chapters").mkdir(parents=True)
    (book / "chapter-contracts").mkdir(parents=True)
    (book / "_system").mkdir(parents=True)
    for i, s in enumerate(slugs, 1):
        (book / "chapters" / f"ch{i:02d}-{s}.txt").write_text("word " * words, encoding="utf-8")
        (book / "chapter-contracts" / f"{s}.yml").write_text(
            f"slug: {s}\nepisode_number: {i}\n", encoding="utf-8"
        )
    (book / "_system" / "orchestrator-state.json").write_text(
        json.dumps({
            "schema_version": 1, "book_slug": "book", "phase": "per-chapter",
            "phase_status": "running", "last_completed_phase": "0f",
            "last_error": None, "phases": {}, "status": "draft", "config": {},
        }), encoding="utf-8",
    )
    return book


class SmokeGateTests(unittest.TestCase):
    def test_valid_chapter_passes(self):
        from phases.preflight_chapter import smoke_check_chapter
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            ok, reason = smoke_check_chapter(book, "alpha")
            self.assertTrue(ok, reason)

    def test_missing_chapter_file(self):
        from phases.preflight_chapter import smoke_check_chapter
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            ok, reason = smoke_check_chapter(book, "ghost")
            self.assertFalse(ok)
            self.assertIn("chapter file missing", reason)

    def test_missing_contract(self):
        from phases.preflight_chapter import smoke_check_chapter
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            (book / "chapter-contracts" / "alpha.yml").unlink()
            ok, reason = smoke_check_chapter(book, "alpha")
            self.assertFalse(ok)
            self.assertIn("contract missing", reason)

    def test_word_band(self):
        from phases.preflight_chapter import smoke_check_chapter
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"], words=10)
            ok, reason = smoke_check_chapter(book, "alpha")
            self.assertFalse(ok)
            self.assertIn("word count", reason)


class CostCeilingTests(unittest.TestCase):
    def _book_with_ledger(self, tmp: Path, rows: list[dict], config: dict | None = None) -> Path:
        book = tmp / "book"
        (book / "_system").mkdir(parents=True)
        (book / "_system" / "orchestrator-state.json").write_text(
            json.dumps({"phase": "0e", "phase_status": "running", "phases": {},
                        "config": config or {}}), encoding="utf-8")
        led = book / "_system" / "cost-ledger.jsonl"
        led.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return book

    def test_under_soft_is_ok(self):
        from cost_guard import cost_ceiling_check
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book_with_ledger(Path(tmp), [
                {"ts": "t", "phase": "0e", "step": "x", "model": "g", "cost_usd": 5.0, "engine": "api"}])
            self.assertEqual(cost_ceiling_check(book)["action"], "ok")

    def test_soft_warns_hard_halts(self):
        from cost_guard import cost_ceiling_check
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book_with_ledger(Path(tmp), [
                {"ts": "t", "phase": "0e", "step": "x", "model": "g", "cost_usd": 25.0, "engine": "api"}])
            self.assertEqual(cost_ceiling_check(book)["action"], "warn")
            (book / "_system" / "cost-ledger.jsonl").write_text(
                json.dumps({"ts": "t", "phase": "0e", "step": "x", "model": "g",
                            "cost_usd": 55.0, "engine": "api"}) + "\n", encoding="utf-8")
            self.assertEqual(cost_ceiling_check(book)["action"], "halt")

    def test_max_engine_excluded(self):
        from cost_guard import cost_ceiling_check
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book_with_ledger(Path(tmp), [
                {"ts": "t", "phase": "per-chapter", "step": "framing", "model": "claude",
                 "cost_usd": 100.0, "engine": "max"}])
            self.assertEqual(cost_ceiling_check(book)["action"], "ok")


class CircuitBreakerTests(unittest.TestCase):
    """The loop must HALT (not grind) on a systemic failure."""

    def _drive(self, slugs, outcome_for):
        """Run _drive_per_chapter_and_after with per_chapter_pass + side phases mocked.

        outcome_for(slug) -> ChapterOutcome. Returns (rc, call_log, final_state).
        State is read INSIDE the tempdir context (the dir is removed on exit).
        """
        from phases import chapter_driver as cd
        from _convergence import ChapterOutcome  # noqa: F401

        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), slugs)
            calls: list[str] = []

            def _fake_pass(book_dir, slug):
                calls.append(slug)
                return outcome_for(slug)

            with (
                mock.patch.object(cd, "per_chapter_pass", side_effect=_fake_pass),
                mock.patch.object(cd, "phase_git_commit"),
                mock.patch.object(cd, "smoke_check_book", return_value=[]),
            ):
                rc = cd._drive_per_chapter_and_after(book)
            state = json.loads(
                (book / "_system" / "orchestrator-state.json").read_text(encoding="utf-8")
            )
            return rc, calls, state

    def _failed(self, slug, reason):
        from _convergence import ChapterOutcome
        return ChapterOutcome(chapter_slug=slug, final_verdict="FAILED",
                              outer_iterations=0, fixer_attempts=0,
                              p0_remaining=0, p1_remaining=0, p2_remaining=0,
                              notes=[reason])

    def test_first_chapter_deterministic_failure_halts_after_one(self):
        slugs = ["a-ch", "b-ch", "c-ch"]
        rc, calls, state = self._drive(
            slugs, lambda s: self._failed(s, "extract failed: not under canonical root"))
        # Only the FIRST chapter is attempted; the loop halts.
        self.assertEqual(calls, ["a-ch"])
        self.assertEqual(rc, 2)
        self.assertIn("CIRCUIT-BREAKER", (state.get("last_error") or {}).get("message", ""))

    def test_same_signature_across_chapters_halts(self):
        from _convergence import ChapterOutcome
        slugs = ["a-ch", "b-ch", "c-ch", "d-ch"]

        def outcome(s):
            if s == "a-ch":
                return ChapterOutcome(chapter_slug=s, final_verdict="SHIP-READY",
                                      outer_iterations=1, fixer_attempts=0,
                                      p0_remaining=0, p1_remaining=0, p2_remaining=0, notes=[])
            return self._failed(s, "P0: forbidden pairing of title and name")

        rc, calls, _state = self._drive(slugs, outcome)
        # a ships; b fails (1 sig); c fails same sig -> halt. d never attempted.
        self.assertEqual(calls, ["a-ch", "b-ch", "c-ch"])
        self.assertEqual(rc, 2)

    def test_distinct_content_failures_do_not_halt_early(self):
        # Different reasons, none first-chapter-deterministic (give them a SHIP first
        # so attempted!=1), should NOT trip the breaker — graceful-degrade continues.
        from _convergence import ChapterOutcome
        slugs = ["a-ch", "b-ch", "c-ch"]

        def outcome(s):
            if s == "a-ch":
                return ChapterOutcome(chapter_slug=s, final_verdict="SHIP-READY",
                                      outer_iterations=1, fixer_attempts=0,
                                      p0_remaining=0, p1_remaining=0, p2_remaining=0, notes=[])
            return self._failed(s, f"unique finding for {s}")

        rc, calls, _state = self._drive(slugs, outcome)
        # All attempted (no systemic halt); loop returns 2 at the end due to failures.
        self.assertEqual(calls, ["a-ch", "b-ch", "c-ch"])


class SuperviseHelperTests(unittest.TestCase):
    def test_terminal(self):
        import supervise_run as s
        self.assertTrue(s._terminal({"phase": "done", "phase_status": "x"}))
        self.assertTrue(s._terminal({"phase": "finalize", "phase_status": "halted"}))
        self.assertFalse(s._terminal({"phase": "per-chapter", "phase_status": "running"}))

    def test_systemic_classification(self):
        import supervise_run as s
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "book"
            (book / "_system").mkdir(parents=True)
            (book / "_system" / "orchestrator-state.json").write_text(
                json.dumps({"phase": "per-chapter", "phase_status": "running",
                            "phases": {}, "config": {}}), encoding="utf-8")
            self.assertIsNotNone(s._systemic_reason({"last_error": {"message": "CIRCUIT-BREAKER: x"}}, book))
            self.assertIsNotNone(s._systemic_reason(
                {"phase": "per-chapter", "phase_status": "failed", "last_error": None}, book))
            self.assertIsNone(s._systemic_reason(
                {"phase": "per-chapter", "phase_status": "running", "last_error": None}, book))


if __name__ == "__main__":
    unittest.main()
