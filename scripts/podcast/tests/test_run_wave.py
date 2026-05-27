#!/usr/bin/env python3
"""Tests for scripts/podcast/run_wave.py (P1.4 wave kickoff harness).

Uses stdlib unittest only — pytest is not yet a project dependency (P8.1).
Covers the P1.4 acceptance rows listed in _workspace/plan/operations/per-book-ship-checklist.md.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

# Make scripts/podcast/ importable
SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import run_wave  # noqa: E402


# Minimal per-book-ship-checklist.md fixture covering W1..W5.
SAMPLE_ACC = """\
# Acceptance Criteria — Master Checklist

Companion to: foo.

## Wave 1 — Foundation & Guardrails

### P1 — Boundary
- [ ] **P1.1** ✅ first bullet
- [ ] **P1.1** ✅ second bullet
- [x] **P3.1** ✅ doc cleanup shipped
- [x] **P3.2** ✅ doc cleanup shipped

### P5 — Perm-mode fix
- [x] **P5.1** ✅ SHIPPED

## Wave 2 — Observability + Polish

### P7 — Heartbeat
- [ ] **P7.1** ✅ daemon thread

## Wave 3 — Corpus Validation

### P9 — Corpus
- [ ] **P9.1** 📊 Ayyuhal Walad

## Wave 4 — Control Plane

### P11 — Multi-Mac decision (doc-only)
- [ ] **P11.1** ✅ docs/podcast/multi-mac-decision.md exists

## Wave 5 — Deferred + Self-Learning

- [ ] **P17** 🟡 PDF pre-splitting
- [ ] **P17.1** 🟡 Source-adapter registry
"""

# Acceptance file where every W1 row is checked — for testing the "wave DONE" path.
ALL_W1_DONE = """\
# Acceptance Criteria

## Wave 1 — Foundation
- [x] **P1.1** ✅ bullet
- [x] **P5.1** ✅ bullet

## Wave 2 — Observability
- [ ] **P7.1** ✅ bullet
"""


class ParseWaveRowsTests(unittest.TestCase):
    def test_parse_wave_rows_splits_by_wave_heading(self):
        rows = run_wave.parse_wave_rows(SAMPLE_ACC)
        self.assertEqual(set(rows.keys()), {1, 2, 3, 4, 5})

    def test_parse_wave_rows_counts_match_sample(self):
        rows = run_wave.parse_wave_rows(SAMPLE_ACC)
        self.assertEqual(len(rows[1]), 5)  # 2×P1.1 + P3.1 + P3.2 + P5.1
        self.assertEqual(len(rows[2]), 1)
        self.assertEqual(len(rows[3]), 1)
        self.assertEqual(len(rows[4]), 1)
        self.assertEqual(len(rows[5]), 2)

    def test_parse_wave_rows_captures_check_status(self):
        rows = run_wave.parse_wave_rows(SAMPLE_ACC)
        w1_status = [s for s, _ in rows[1]]
        # 2 unchecked P1.1 + 2 checked P3 + 1 checked P5.1 = [ , , x, x, x]
        self.assertEqual(w1_status.count("x"), 3)
        self.assertEqual(w1_status.count(" "), 2)

    def test_parse_wave_rows_returns_empty_for_no_headings(self):
        self.assertEqual(run_wave.parse_wave_rows("no headings here"), {})

    def test_parse_wave_rows_handles_subnumbered_ids(self):
        text = "## Wave 5\n- [ ] **P17.1** registry"
        rows = run_wave.parse_wave_rows(text)
        self.assertEqual(rows[5], [(" ", "P17.1")])


class WaveStatusTests(unittest.TestCase):
    def test_wave_status_partial(self):
        checked, total = run_wave.wave_status(SAMPLE_ACC, 1)
        self.assertEqual(checked, 3)
        self.assertEqual(total, 5)

    def test_wave_status_zero_when_no_rows(self):
        checked, total = run_wave.wave_status("", 1)
        self.assertEqual((checked, total), (0, 0))

    def test_is_wave_done_partial_false(self):
        self.assertFalse(run_wave.is_wave_done(SAMPLE_ACC, 1))

    def test_is_wave_done_all_checked_true(self):
        self.assertTrue(run_wave.is_wave_done(ALL_W1_DONE, 1))

    def test_is_wave_done_empty_wave_false(self):
        """A wave with zero rows is NOT done (avoids vacuous truth)."""
        self.assertFalse(run_wave.is_wave_done("## Wave 9 — empty\n", 9))


class CostLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "kitab-foo"
        (self.book_dir / "_system").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _patch_books_dir(self):
        return mock.patch.object(run_wave, "BOOKS_DIR", Path(self.tmp.name))

    def test_book_cost_zero_when_no_ledger(self):
        with self._patch_books_dir():
            self.assertEqual(run_wave.book_cost_usd("kitab-foo"), 0.0)

    def test_book_cost_sums_rows(self):
        ledger = self.book_dir / "_system" / "cost-ledger.jsonl"
        ledger.write_text(
            "\n".join(
                json.dumps({"ts": "x", "cost_usd": v}) for v in [1.5, 2.75, 0.25]
            )
        )
        with self._patch_books_dir():
            self.assertAlmostEqual(run_wave.book_cost_usd("kitab-foo"), 4.5)

    def test_book_cost_tolerates_malformed_rows(self):
        ledger = self.book_dir / "_system" / "cost-ledger.jsonl"
        ledger.write_text("not json\n" + json.dumps({"cost_usd": 3.0}) + "\nalso not json")
        with self._patch_books_dir():
            self.assertEqual(run_wave.book_cost_usd("kitab-foo"), 3.0)

    def test_book_cost_handles_missing_cost_field(self):
        ledger = self.book_dir / "_system" / "cost-ledger.jsonl"
        ledger.write_text(json.dumps({"ts": "x"}))
        with self._patch_books_dir():
            self.assertEqual(run_wave.book_cost_usd("kitab-foo"), 0.0)


class CheckCommandTests(unittest.TestCase):
    """`--check` is report-only; always exits 0."""

    def _run(self, text: str, wave: int) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = run_wave.cmd_check(text, wave)
        return rc, buf.getvalue()

    def test_check_pending_wave(self):
        rc, out = self._run(SAMPLE_ACC, 1)
        self.assertEqual(rc, run_wave.EXIT_DONE)
        self.assertIn("Wave 1 (Foundation & Guardrails)", out)
        self.assertIn("3/5 acceptance rows checked", out)
        self.assertIn("PENDING", out)
        self.assertIn("P1.1: 2/2 bullets unchecked", out)

    def test_check_done_wave(self):
        rc, out = self._run(ALL_W1_DONE, 1)
        self.assertEqual(rc, run_wave.EXIT_DONE)
        self.assertIn("DONE", out)
        self.assertNotIn("Unchecked task ids", out)


class MainArgvTests(unittest.TestCase):
    """End-to-end exercises of main() via argv injection. Uses tmp acceptance file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.acc_file = self.tmp_path / "per-book-ship-checklist.md"
        self.books_dir = self.tmp_path / "books"
        self.books_dir.mkdir()
        self._patches = [
            mock.patch.object(run_wave, "ACCEPTANCE_FILE", self.acc_file),
            mock.patch.object(run_wave, "BOOKS_DIR", self.books_dir),
            mock.patch.object(run_wave, "p9_invariant_green", lambda: True),
            mock.patch.object(run_wave, "_ensure_wave_branch", lambda wave_n: None),
            mock.patch.object(
                run_wave,
                "_merge_wave_to_develop_and_return",
                lambda wave_n: run_wave.EXIT_DONE,
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        self.tmp.cleanup()

    def _write_acc(self, text: str) -> None:
        self.acc_file.write_text(text)

    def _run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = run_wave.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_missing_acceptance_file_returns_error(self):
        rc, _, err = self._run_main("1")
        self.assertEqual(rc, run_wave.EXIT_ERROR)
        self.assertIn("acceptance file missing", err)

    def test_done_wave_idempotent_exits_zero(self):
        self._write_acc(ALL_W1_DONE)
        rc, out, _ = self._run_main("1")
        self.assertEqual(rc, run_wave.EXIT_DONE)
        self.assertIn("already DONE", out)

    def test_pending_wave_halts_at_review_gate(self):
        self._write_acc(SAMPLE_ACC)
        rc, out, _ = self._run_main("1")
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        # New phase-registry dispatcher emits one of these halt signatures:
        #   • "phase registry is empty" — wave registry has no runners wired
        #   • "halted at a phase requiring human review" — a runner returned halted
        #   • "executed N phase(s); X/Y wave rows checked" — partial progress
        # Whichever path runs, exit code is HALTED_REVIEW (asserted above).
        self.assertTrue(
            any(
                marker in out
                for marker in (
                    "phase registry is empty",
                    "halted at a phase requiring",
                    "wave rows checked",
                )
            ),
            f"Expected a halt-shape signature in output, got:\n{out}",
        )

    def test_check_flag_reports_without_dispatching(self):
        self._write_acc(SAMPLE_ACC)
        rc, out, _ = self._run_main("--check", "1")
        self.assertEqual(rc, run_wave.EXIT_DONE)
        self.assertIn("--check", out)
        # Dispatcher's status block should NOT appear under --check
        self.assertNotIn("W1 dispatch", out)

    def test_w3_requires_book_flag(self):
        self._write_acc(SAMPLE_ACC)
        rc, _, err = self._run_main("3")
        self.assertEqual(rc, run_wave.EXIT_ERROR)
        self.assertIn("Wave 3 requires --book", err)

    def test_w3_refuses_when_cost_over_cap(self):
        self._write_acc(SAMPLE_ACC)
        # Seed a $75 ledger for the book.
        book = self.books_dir / "kitab-pricey"
        (book / "_system").mkdir(parents=True)
        (book / "_system" / "cost-ledger.jsonl").write_text(
            json.dumps({"cost_usd": 30.0}) + "\n" + json.dumps({"cost_usd": 45.0})
        )
        rc, _, err = self._run_main("3", "--book", "kitab-pricey")
        self.assertEqual(rc, run_wave.EXIT_ERROR)
        self.assertIn("exceeding hard cap", err)
        self.assertIn("$75.00", err)

    def test_w3_allows_when_cost_under_cap(self):
        self._write_acc(SAMPLE_ACC)
        book = self.books_dir / "kitab-cheap"
        (book / "_system").mkdir(parents=True)
        (book / "_system" / "cost-ledger.jsonl").write_text(
            json.dumps({"cost_usd": 5.0})
        )
        rc, out, _ = self._run_main("3", "--book", "kitab-cheap")
        # Cost gate PASSES (under cap). The dispatcher proceeds to iterate the
        # W3 registry; since REGISTRY[3] is empty, "phase registry is empty"
        # marker appears and exit is HALTED_REVIEW.
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        # Either the registry-empty path OR a halt-signature path is fine — both
        # mean "the cost guard didn't block; the dispatcher proceeded."
        self.assertTrue(
            "phase registry is empty" in out or "iterating" in out,
            f"Expected dispatcher-proceeded signature, got:\n{out}",
        )

    def test_w3_allows_when_ledger_missing(self):
        self._write_acc(SAMPLE_ACC)
        # No ledger file → cost == 0 → allow.
        rc, _, _ = self._run_main("3", "--book", "kitab-new")
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)

    def test_w3_cost_cap_override(self):
        """`--cost-cap-hard 100` should allow a $75 spend that the default would block."""
        self._write_acc(SAMPLE_ACC)
        book = self.books_dir / "kitab-overrun"
        (book / "_system").mkdir(parents=True)
        (book / "_system" / "cost-ledger.jsonl").write_text(
            json.dumps({"cost_usd": 75.0})
        )
        rc, _, _ = self._run_main(
            "3", "--book", "kitab-overrun", "--cost-cap-hard", "100"
        )
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)

    def test_w5_requires_phase_flag(self):
        self._write_acc(SAMPLE_ACC)
        rc, _, err = self._run_main("5")
        self.assertEqual(rc, run_wave.EXIT_ERROR)
        self.assertIn("Wave 5 requires --phase", err)

    def test_w5_with_phase_dispatches(self):
        acc = textwrap.dedent(
            """\
            # Acceptance Criteria

            ## Wave 1
            - [x] **P1.1** done

            ## Wave 2
            - [x] **P2.1** done

            ## Wave 3
            - [x] **P3.1** done

            ## Wave 4
            - [x] **P4.1** done

            ## Wave 5
            - [ ] **P5.1** pending
            """
        )
        self._write_acc(acc)
        rc, out, _ = self._run_main("5", "--phase", "P17.1")
        # W5 phase-flag check passes; dispatcher proceeds to iterate REGISTRY[5].
        # Since REGISTRY[5] is empty, "phase registry is empty" appears.
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        self.assertIn("phase registry is empty", out)

    def test_invalid_wave_number_rejected(self):
        with self.assertRaises(SystemExit):
            self._run_main("6")

    def test_wave_2_dispatch_halts(self):
        acc = textwrap.dedent(
            """\
            # Acceptance Criteria

            ## Wave 1
            - [x] **P1.1** done

            ## Wave 2
            - [ ] **P2.1** pending
            """
        )
        self._write_acc(acc)
        rc, out, _ = self._run_main("2")
        # W2 registry currently empty → "phase registry is empty" + halt.
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        self.assertTrue(
            "phase registry is empty" in out or "W2" in out,
            f"Expected W2 halt signature, got:\n{out}",
        )

    def test_wave_4_dispatch_halts(self):
        self._write_acc(SAMPLE_ACC)
        rc, out, _ = self._run_main("4")
        # W4 currently iterates 1 phase (P11.1); halt is from "remaining rows"
        # OR from registry-empty if P11.1 module isn't shipped. Either is a
        # valid halt for this test's purpose.
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        self.assertTrue(
            "phase registry is empty" in out
            or "wave rows checked" in out
            or "iterating" in out,
            f"Expected W4 halt signature, got:\n{out}",
        )

    def test_collective_quality_gate_triggers_mandatory_alignment(self):
        self._write_acc(SAMPLE_ACC)
        rc, out, _ = self._run_main("2")
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        self.assertIn("mandatory alignment inserted", out)

    def test_collective_quality_passes_when_prior_waves_done(self):
        acc = textwrap.dedent(
            """\
            # Acceptance Criteria

            ## Wave 1
            - [x] **P1.1** done

            ## Wave 2
            - [ ] **P2.1** pending
            """
        )
        self._write_acc(acc)
        rc, out, _ = self._run_main("2")
        # W2 still halts because it's not complete, but no mandatory alignment line
        # should appear since W1 is already complete.
        self.assertEqual(rc, run_wave.EXIT_HALTED_REVIEW)
        self.assertNotIn("mandatory alignment inserted", out)


class P9InvariantTests(unittest.TestCase):
    def test_returns_true_when_challenger_test_missing(self):
        with mock.patch.object(run_wave, "CHALLENGER_TEST", Path("/nonexistent")):
            self.assertTrue(run_wave.p9_invariant_green())

    def test_returns_true_on_subprocess_exit_0(self):
        with mock.patch.object(run_wave, "CHALLENGER_TEST", Path("/dev/null")), \
             mock.patch.object(Path, "exists", lambda self: True), \
             mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.MagicMock(returncode=0)
            self.assertTrue(run_wave.p9_invariant_green())

    def test_returns_false_on_subprocess_non_zero(self):
        with mock.patch.object(run_wave, "CHALLENGER_TEST", Path("/dev/null")), \
             mock.patch.object(Path, "exists", lambda self: True), \
             mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.MagicMock(returncode=1)
            self.assertFalse(run_wave.p9_invariant_green())


if __name__ == "__main__":
    unittest.main()
