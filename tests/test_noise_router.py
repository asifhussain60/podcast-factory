"""Tests for scripts/podcast/phases/noise_router.py (Wave I, I2)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast" / "phases"))

from noise_router import (
    _is_protected,
    _pass1_rule,
    ParagraphDecision,
)


class TestIsProtected(unittest.TestCase):
    """Protected content must never enter the noise-routing queue."""

    def test_arabic_script_is_protected(self):
        self.assertTrue(_is_protected("بسم الله الرحمن الرحيم"))

    def test_quran_citation_is_protected(self):
        self.assertTrue(_is_protected("[Quran 2:255] Ayat al-Kursi."))

    def test_hadith_citation_is_protected(self):
        self.assertTrue(_is_protected("[Hadith — Bukhari 1] The Prophet said…"))

    def test_plain_english_not_protected(self):
        self.assertFalse(_is_protected("The teacher explained the concept to his students."))

    def test_empty_string_not_protected(self):
        self.assertFalse(_is_protected(""))

    def test_mixed_arabic_english_is_protected(self):
        # Any Arabic Unicode makes the paragraph protected
        self.assertTrue(_is_protected("The term ta'wil (تأويل) refers to esoteric interpretation."))


class TestPass1RuleRouting(unittest.TestCase):
    """Pass 1 rule patterns must correctly identify structural noise."""

    def test_greeting_opener_deleted(self):
        decision = _pass1_rule("In the name of God, the Compassionate, the Merciful.")
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "delete")
        self.assertEqual(decision.routing_pass, "rule")

    def test_bismillah_deleted(self):
        decision = _pass1_rule("Bismillah ir-Rahman ir-Raheem, we begin today.")
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "delete")

    def test_lecture_greeting_deleted(self):
        decision = _pass1_rule("Dear brothers and sisters, welcome to today's session.")
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "delete")

    def test_substantive_paragraph_not_matched(self):
        text = ("The Imam explained that ta'wil is the science of uncovering hidden meaning "
                "within the text of scripture.")
        decision = _pass1_rule(text)
        self.assertIsNone(decision)

    def test_recap_reference_deleted(self):
        decision = _pass1_rule("As we discussed in the previous session, the concept builds on…")
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "delete")

    def test_confidence_high_for_rule_matches(self):
        decision = _pass1_rule("In the name of God, we begin.")
        self.assertIsNotNone(decision)
        self.assertGreater(decision.confidence, 0.85)


class TestNoiseRouterDataStructure(unittest.TestCase):
    """ParagraphDecision must carry all required fields."""

    def test_paragraph_decision_fields(self):
        d = ParagraphDecision(
            para_idx=3,
            text_preview="Some text here",
            action="keep",
            routing_pass="protected",
            reason="arabic-script",
            confidence=1.0,
        )
        self.assertEqual(d.para_idx, 3)
        self.assertEqual(d.action, "keep")
        self.assertEqual(d.routing_pass, "protected")
        self.assertEqual(d.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
