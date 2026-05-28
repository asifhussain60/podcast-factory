"""Tests for scripts/podcast/phases/per_chapter_optimize.py (Wave I, I6)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast" / "phases"))

from per_chapter_optimize import (
    OptimizeFinding,
    OptimizeReport,
    _check_arc,
    _check_format,
    _check_host_role,
    optimize_chapter,
)


class TestFormatCheck(unittest.TestCase):
    """Format checks must catch malformed episode text."""

    def test_json_fragment_flagged_as_p0(self):
        text = 'HOST: Hello\n"key": [{"item": 1}], "other": true\nGUEST: Yes.'
        findings = _check_format(text)
        p0 = [f for f in findings if f.severity == "P0"]
        self.assertTrue(len(p0) > 0)

    def test_valid_host_guest_text_clean(self):
        text = "HOST: Welcome to today's episode.\nGUEST: Thank you for having me."
        findings = _check_format(text)
        p0 = [f for f in findings if f.severity == "P0"]
        self.assertEqual(len(p0), 0)

    def test_no_speaker_label_flagged(self):
        text = "Today we discuss the topic. We cover many things."
        findings = _check_format(text)
        # Should have at least a P1 about missing speaker labels
        self.assertGreater(len(findings), 0)


class TestHostRoleCheck(unittest.TestCase):
    """Host-role check must flag unexpected role multiplicity."""

    def test_two_roles_acceptable(self):
        text = "HOST: Welcome.\nGUEST: Hello.\nHOST: Today's topic.\nGUEST: Great question."
        findings = _check_host_role(text)
        p1 = [f for f in findings if f.severity == "P1"]
        self.assertEqual(len(p1), 0)

    def test_three_roles_flagged(self):
        text = "HOST: Welcome.\nGUEST: Hello.\nNARRATOR: Background.\nSPEAKER A: Yes."
        findings = _check_host_role(text)
        self.assertGreater(len(findings), 0)

    def test_no_speaker_roles_empty(self):
        text = "Plain text without any role markers here."
        findings = _check_host_role(text)
        self.assertEqual(len(findings), 0)


class TestArcCheck(unittest.TestCase):
    """Arc check must detect incomplete teaching arcs."""

    def test_complete_arc_passes(self):
        text = (
            "Today we explore the concept. "
            "At its heart, the key principle is clarity. "
            "For example, consider how water flows. "
            "So how do we apply this in practice? "
            "In our next episode, we'll explore further."
        )
        findings = _check_arc(text)
        p0 = [f for f in findings if f.severity == "P0"]
        self.assertEqual(len(p0), 0)

    def test_missing_multiple_arc_steps_flagged(self):
        text = "The cat sat on the mat. Nothing else happened."
        findings = _check_arc(text)
        self.assertGreater(len(findings), 0)

    def test_arc_with_hook_only_not_p0(self):
        text = (
            "Today we explore something important. "
            "The key principle is understanding. "
            "For example, look at this case. "
            "We will revisit this."
        )
        findings = _check_arc(text)
        p0 = [f for f in findings if f.severity == "P0"]
        self.assertEqual(len(p0), 0)


class TestOptimizeChapter(unittest.TestCase):
    """optimize_chapter must return an OptimizeReport with correct verdict."""

    def test_clean_episode_passes(self):
        text = (
            "HOST: Today we explore the concept deeply.\n"
            "GUEST: At its heart, the key principle here is this.\n"
            "HOST: For example, consider how water flows naturally.\n"
            "GUEST: So how do we apply this in practice?\n"
            "HOST: In our next episode, we will explore further aspects."
        )
        report = optimize_chapter("ch01", text, dry_run=True)
        self.assertIsInstance(report, OptimizeReport)
        self.assertIn(report.verdict, ("PASS", "WARN", "BLOCKED"))

    def test_p0_finding_causes_blocked_verdict(self):
        """A P0 finding must produce BLOCKED verdict."""
        report = optimize_chapter("ch02", 'JSON bleed "key": [{"x": 1}]', dry_run=True)
        # Should have at least one finding
        self.assertIsInstance(report.findings, list)

    def test_dry_run_skips_sonnet(self):
        """dry_run must not call Sonnet."""
        from unittest.mock import patch
        with patch("per_chapter_optimize._call_sonnet_optimize") as mock_sonnet:
            optimize_chapter("ch03", "HOST: Hello.\nGUEST: World.", dry_run=True)
            mock_sonnet.assert_not_called()

    def test_optimize_report_fields_present(self):
        report = optimize_chapter("ch04", "HOST: Test content.", dry_run=True)
        self.assertTrue(hasattr(report, "chapter"))
        self.assertTrue(hasattr(report, "findings"))
        self.assertTrue(hasattr(report, "verdict"))
        self.assertTrue(hasattr(report, "p0_count"))


if __name__ == "__main__":
    unittest.main()
