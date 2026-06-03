"""
Tests for mint_section_depths.py (Wave N pipeline-side depth guessing fix).

Tests the keyword classifier in isolation (without touching the real DB).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mint_section_depths import _classify_section


class TestClassifySection(unittest.TestCase):
    def test_haqaiq_keyword_wins(self):
        self.assertEqual(_classify_section("The Haqaiq of Being", "discussion of haqaiq", None), "haqaiq")

    def test_mabda_maad_keyword_wins(self):
        self.assertEqual(_classify_section("Origin and Return", "explores the concept of mabda", None), "mabda_maad")

    def test_mamsool_keyword_wins(self):
        self.assertEqual(_classify_section("A Parable of the Soul", "this parable teaches", None), "mamsool")

    def test_taveel_keyword_wins(self):
        self.assertEqual(_classify_section("The Inner Meaning", "esoteric interpretation of the verse", None), "taveel")

    def test_advanced_keyword_wins(self):
        self.assertEqual(_classify_section("Legal Reasoning", "analysis of jurisprudence in the text", None), "advanced")

    def test_general_keyword_wins(self):
        self.assertEqual(_classify_section("Historical Background", "a history of the period", None), "general")

    def test_falls_back_to_book_level(self):
        result = _classify_section("An Untitled Section", "no matching keywords here", "taveel")
        self.assertEqual(result, "taveel")

    def test_falls_back_to_general_when_no_book_level(self):
        result = _classify_section("An Untitled Section", "no keywords at all", None)
        self.assertEqual(result, "general")

    def test_higher_priority_beats_lower(self):
        # 'haqaiq' and 'history' both appear — haqaiq is checked first
        result = _classify_section("Deep Concepts", "history of haqaiq realities", None)
        self.assertEqual(result, "haqaiq")

    def test_heading_contributes_to_classification(self):
        # keyword in heading, body is neutral
        result = _classify_section("Taveel of the Verse", "this section discusses the topic", None)
        self.assertEqual(result, "taveel")

    def test_body_contributes_to_classification(self):
        # keyword only in body
        result = _classify_section("The Soul's Journey", "the parable shows us the allegorical meaning", None)
        self.assertEqual(result, "mamsool")


if __name__ == "__main__":
    unittest.main()
