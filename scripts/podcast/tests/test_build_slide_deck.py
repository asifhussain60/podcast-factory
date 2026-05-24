#!/usr/bin/env python3
"""Smoke tests for build_slide_deck.py + _slide_convergence.py.

The slide-deck path is opt-in (gated by enable_slide_decks in series-plan.md)
and has shipped on zero books to date. These tests pin the deterministic
validators in build_slide_deck.py so enabling the slide path for a new book
(M&D) is a measured risk rather than an unknown.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import build_slide_deck as bsd   # noqa: E402
from _slide_convergence import _VERDICT_LINE_RE   # noqa: E402


class WordCountTests(unittest.TestCase):

    def test_word_count_basic(self):
        self.assertEqual(bsd.word_count("one two three"), 3)
        self.assertEqual(bsd.word_count(""), 0)
        self.assertEqual(bsd.word_count("   "), 0)


class DeterministicCheckerTests(unittest.TestCase):
    """Each check_* function in build_slide_deck.py mutates a `findings`
    list. We confirm they correctly flag the canonical violation cases."""

    def test_em_dash_flagged(self):
        findings: list[str] = []
        bsd.check_em_dashes("Hello — world.", "chapter", findings)
        self.assertTrue(any("em-dash" in f.lower() or "—" in f for f in findings))

    def test_em_dash_clean(self):
        findings: list[str] = []
        bsd.check_em_dashes("Hello, world.", "chapter", findings)
        self.assertEqual(findings, [])

    def test_html_comments_flagged(self):
        findings: list[str] = []
        bsd.check_html_comments("body <!-- TODO --> more", "chapter", findings)
        self.assertNotEqual(findings, [])

    def test_inline_phonetic_flagged(self):
        findings: list[str] = []
        bsd.check_inline_phonetics(
            "the seeker spoke of *Sharee-ah* (Sha-REE-ah) gently.",
            "chapter", findings,
        )
        # At minimum should flag the inline parenthetical
        self.assertNotEqual(findings, [])


class SlideVerdictRegexTests(unittest.TestCase):
    """Pin every verdict shape the slide-deck challenger LLM emits."""

    def test_classic_shape(self):
        m = _VERDICT_LINE_RE.search("**Verdict**: SHIP-READY")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).upper(), "SHIP-READY")

    def test_colon_inside_bold(self):
        m = _VERDICT_LINE_RE.search("**Verdict:** SHIP-READY")
        self.assertIsNotNone(m)

    def test_embedded_keyword(self):
        m = _VERDICT_LINE_RE.search("**Verdict: SHIP-READY** — clean.")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).upper(), "SHIP-READY")

    def test_bundle_status_alias(self):
        m = _VERDICT_LINE_RE.search("**Bundle status**: ship")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).lower(), "ship")

    def test_iterate_signals_blocked(self):
        m = _VERDICT_LINE_RE.search("**Verdict**: iterate")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).lower(), "iterate")


if __name__ == "__main__":
    unittest.main()
