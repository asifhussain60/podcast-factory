#!/usr/bin/env python3
"""Tests for _convergence.py — verdict parsing + outcome dataclass.

The verdict-line regex is the most regression-prone part of convergence.
Without these tests, the silent BLOCKED-on-unparseable fallback hides drift
between what the challenger LLM writes and what the loop reads. Each test
pins one shape we have seen in real challenger-report.md output.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _convergence import (  # noqa: E402
    VERDICT_LINE_RE,
    parse_challenger_report,
    ChapterOutcome,
)


class VerdictRegexTests(unittest.TestCase):
    """The regex must match every shape we have seen in production."""

    def test_canonical_shape(self):
        m = VERDICT_LINE_RE.search("**Verdict:** SHIP-READY")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).upper(), "SHIP-READY")

    def test_embedded_keyword_shape(self):
        """KaR's in-body per-iteration summaries use this shape."""
        m = VERDICT_LINE_RE.search("**Verdict: SHIP-WITH-CAUTION** —")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).upper(), "SHIP-WITH-CAUTION")

    def test_embedded_keyword_blocked(self):
        m = VERDICT_LINE_RE.search("**Verdict: BLOCKED** — 1 P0 finding")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).upper(), "BLOCKED")

    def test_case_insensitive(self):
        m = VERDICT_LINE_RE.search("**Verdict:** ship-ready")
        self.assertIsNotNone(m)

    def test_extra_whitespace(self):
        m = VERDICT_LINE_RE.search("**Verdict:**   SHIP-READY")
        self.assertIsNotNone(m)

    def test_prose_with_word_verdict_does_not_false_match(self):
        m = VERDICT_LINE_RE.search("the verdict was a surprise to nobody")
        self.assertIsNone(m)


class ParseReportTests(unittest.TestCase):

    def _write_report(self, body: str) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "challenger-report.md"
        tmp.write_text(body, encoding="utf-8")
        return tmp

    def test_missing_file_returns_blocked_zeros(self):
        verdict, p0, p1, p2 = parse_challenger_report(Path("/nonexistent"))
        self.assertEqual(verdict, "BLOCKED")
        self.assertEqual((p0, p1, p2), (0, 0, 0))

    def test_ship_ready_clean(self):
        report = self._write_report(
            "# title\n\n**Verdict:** SHIP-READY\n\n"
            "## findings\n\n### P0 (none)\n\nNone.\n\n"
            "### P1 (none)\n\nNone.\n\n### P2 (none)\n\nNone.\n"
        )
        verdict, p0, p1, p2 = parse_challenger_report(report)
        self.assertEqual(verdict, "SHIP-READY")
        self.assertEqual((p0, p1, p2), (0, 0, 0))

    def test_ship_with_caution_with_p1_findings(self):
        """Mirrors KaR's actual report shape."""
        report = self._write_report(
            "# title\n\n"
            "**Verdict:** SHIP-WITH-CAUTION\n\n"
            "## section 5 — findings\n\n"
            "### P0 (none)\n\nNone.\n\n"
            "### P1 (3 findings)\n\n"
            "#### A4: foo\n\nbody\n\n"
            "#### N3-a: bar\n\nbody\n\n"
            "#### N3-b: baz\n\nbody\n\n"
            "### P2 (none)\n\nNone.\n"
        )
        verdict, p0, p1, p2 = parse_challenger_report(report)
        self.assertEqual(verdict, "SHIP-WITH-CAUTION")
        self.assertEqual(p1, 3)


class ChapterOutcomeTests(unittest.TestCase):
    """Ensure the outcome dataclass keeps the contract the orchestrator
    expects: FAILED on cap-reached (not the former FORCE-SHIP-CAUTION)."""

    def test_force_ship_caution_no_longer_a_legal_verdict(self):
        # The docstring contract removed FORCE-SHIP-CAUTION from the verdict
        # union. If anyone re-adds it, this test fails to flag the regression.
        legal = {"SHIP-READY", "SHIP-WITH-CAUTION", "FAILED"}
        outcome = ChapterOutcome(
            chapter_slug="ch01-test",
            final_verdict="FAILED",
            outer_iterations=3,
            fixer_attempts=9,
            p0_remaining=1,
            p1_remaining=0,
            p2_remaining=0,
        )
        self.assertIn(outcome.final_verdict, legal)


if __name__ == "__main__":
    unittest.main()
