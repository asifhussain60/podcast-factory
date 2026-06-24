"""Regression tests for wisdom/saying reference-tail noise."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _rules import R_NOISE_APPARATUS_PATTERNS, strip_noise_reference_attributions  # noqa: E402


class ReferenceAttributionNoiseTests(unittest.TestCase):
    def test_exact_nahj_hikam_tail_is_stripped_from_blockquote(self):
        text = (
            "> These hearts are vessels, and the best of them is the one that retains "
            "[its contents] most. — Ali ibn Abi Talib, the Father of Imams, in "
            "*Nahj al-Balagha* (compiled by al-Sharif al-Radi), Hikam (Saying) 147.\n"
        )

        cleaned, count = strip_noise_reference_attributions(text)

        self.assertEqual(count, 1)
        self.assertEqual(
            cleaned,
            "> These hearts are vessels, and the best of them is the one that retains "
            "[its contents] most. — Ali ibn Abi Talib, the Father of Imams.\n",
        )

    def test_translator_tail_is_stripped_but_speaker_remains(self):
        text = (
            "> Knowledge is better than wealth. — Ali ibn Abi Talib, the Father of Imams, "
            "*Nahj al-Balagha* (compiled by al-Sharif al-Radi), Saying 147, "
            "trans. Sayyid Ali Reza.\n"
        )

        cleaned, count = strip_noise_reference_attributions(text)

        self.assertEqual(count, 1)
        self.assertEqual(
            cleaned,
            "> Knowledge is better than wealth. — Ali ibn Abi Talib, the Father of Imams.\n",
        )

    def test_short_nahj_sermon_tail_is_stripped(self):
        text = (
            "> The foremost in religion is the knowledge of Him. — Ali ibn Abi Talib, "
            "the Father of Imams, *Nahj al-Balagha*, Sermon 1, trans. Sayed Ali Reza.\n"
        )

        cleaned, count = strip_noise_reference_attributions(text)

        self.assertEqual(count, 1)
        self.assertEqual(
            cleaned,
            "> The foremost in religion is the knowledge of Him. — Ali ibn Abi Talib, "
            "the Father of Imams.\n",
        )

    def test_ghurar_maxims_tail_is_stripped(self):
        text = (
            "> Knowledge is the life of the hearts. — Ali ibn Abi Talib, the Father "
            "of Imams, *Ghurar al-Hikam wa Durar al-Kalim* (compiled by al-Amidi), "
            "among the maxims on knowledge.\n"
        )

        cleaned, count = strip_noise_reference_attributions(text)

        self.assertEqual(count, 1)
        self.assertEqual(
            cleaned,
            "> Knowledge is the life of the hearts. — Ali ibn Abi Talib, the Father "
            "of Imams.\n",
        )

    def test_plain_prose_is_not_changed(self):
        text = (
            "The chapter mentions Nahj al-Balagha while explaining the teaching, "
            "but it is not a blockquote citation tail.\n"
        )

        cleaned, count = strip_noise_reference_attributions(text)

        self.assertEqual(count, 0)
        self.assertEqual(cleaned, text)

    def test_noise_taxonomy_tracks_reference_tail(self):
        sample = "in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam (Saying) 147"
        matches = [
            label
            for pattern, label in R_NOISE_APPARATUS_PATTERNS
            if pattern.search(sample)
        ]

        self.assertIn("NZ-REFERENCE-TAIL", matches)


if __name__ == "__main__":
    unittest.main()
