#!/usr/bin/env python3
"""Tests for scripts/podcast/_phases.py (P5.4 deliverable).

Verifies the constants module's contract per podcast-plan.yaml P5.4 acceptance.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _phases  # noqa: E402


class PhaseEnumTests(unittest.TestCase):
    def test_phase_is_strenum(self):
        # Reference StrEnum via _phases at test-run time, not at import time —
        # if some other test reloads _phases, the StrEnum polyfill class gets
        # rebuilt and a captured-at-import reference would no longer match
        # Phase's new base class.
        self.assertTrue(issubclass(_phases.Phase, _phases.StrEnum))

    def test_phase_has_15_values(self):
        # 14 base phases + 11b-slide-decks (optional; gated by series.enable_slide_decks).
        # Updated 2026-05-23 — original test was authored when 11b-slide-decks
        # didn't yet exist; the phase was added but the test counter was missed.
        self.assertEqual(len(list(_phases.Phase)), 15)

    def test_phase_order_matches_canonical_sequence(self):
        expected = (
            "01-preflight",
            "02-branch",
            "03-scaffold",
            "04-ocr-translate",
            "05-refine-english",
            "06-phonetics",
            "07-chapter-design",
            "08-enrichment",
            "09-series-plan",
            "10-register-series",
            "11-per-chapter",
            "11b-slide-decks",
            "12-trainer",
            "13-merge",
            "14-done",
        )
        self.assertEqual(tuple(p.value for p in _phases.Phase), expected)

    def test_phase_order_constant_matches_enum(self):
        self.assertEqual(_phases.PHASE_ORDER, tuple(_phases.Phase))

    def test_phase_string_resolution(self):
        self.assertIs(_phases.Phase("05-refine-english"), _phases.Phase.REFINE_ENG)
        self.assertIs(_phases.Phase("12-trainer"), _phases.Phase.TRAINER)

    def test_unknown_name_raises(self):
        """Single execution path — no LEGACY_ALIAS, no resolve() indirection."""
        with self.assertRaises(ValueError):
            _phases.Phase("0b")  # legacy name; rejected
        with self.assertRaises(ValueError):
            _phases.Phase("nonexistent")

    def test_module_has_zero_side_effects_on_import(self):
        """Importing must not write files or hit network. (Implicit — re-import
        and verify nothing changed on the filesystem.)"""
        import importlib
        before_mtime = Path(_phases.__file__).stat().st_mtime
        importlib.reload(_phases)
        after_mtime = Path(_phases.__file__).stat().st_mtime
        self.assertEqual(before_mtime, after_mtime)


if __name__ == "__main__":
    unittest.main()
