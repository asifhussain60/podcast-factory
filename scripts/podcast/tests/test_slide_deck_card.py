#!/usr/bin/env python3
"""Tests for the slide-deck generation card (_notebooklm_table sibling renderer).

The LOCKED episode upload table is untouched; these cover only the new card:
framing-driven discovery (letter suffixes included), expected-PDF drop paths,
and the rendered card shape.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _notebooklm_table as nt


def _book(framings: list[tuple[str, str]], decks: list[tuple[str, str]] = ()) -> Path:
    d = Path(tempfile.mkdtemp()) / "book"
    sd = d / "slide-decks"
    sd.mkdir(parents=True)
    for ch, slug in framings:
        (sd / f"{ch}-framing-{slug}.md").write_text("# F\nbody", encoding="utf-8")
    for ch, slug in decks:
        (sd / f"{ch}-deck-{slug}.txt").write_text("deck", encoding="utf-8")
    return d


class DiscoveryTests(unittest.TestCase):
    def test_framing_driven_with_letter_suffix(self) -> None:
        d = _book([("ch01", "intro"), ("ch14b", "appendix-arc")], decks=[("ch01", "intro")])
        found = nt.discover_slide_framings(d)
        self.assertEqual([(c, s) for c, s, _, _ in found], [("ch01", "intro"), ("ch14b", "appendix-arc")])
        # deck txt present only for ch01
        self.assertIsNotNone(found[0][3])
        self.assertIsNone(found[1][3])

    def test_no_slide_decks_dir(self) -> None:
        self.assertEqual(nt.discover_slide_framings(Path(tempfile.mkdtemp())), [])

    def test_expected_pdf_path(self) -> None:
        d = _book([("ch02", "x")])
        self.assertEqual(nt.expected_deck_pdf(d, "ch02", "x"), d / "slide-decks" / "ch02-x.pdf")


class CardRenderTests(unittest.TestCase):
    def test_empty_rows_render_nothing(self) -> None:
        self.assertEqual(nt.render_slide_deck_card_lines([]), [])

    def test_card_shape(self) -> None:
        rows = [
            nt.SlideDeckCardRow(
                ch="ch01",
                slug="intro",
                framing_href="content/X/b/slide-decks/ch01-framing-intro.md",
                deck_href="content/X/b/slide-decks/ch01-deck-intro.txt",
                expected_pdf="content/X/b/slide-decks/ch01-intro.pdf",
            )
        ]
        lines = nt.render_slide_deck_card_lines(rows)
        text = "\n".join(lines)
        self.assertIn("SLIDE DECK GENERATION", text)
        self.assertIn("| ch01 |", text)
        self.assertIn("[ch01-deck-intro.txt](content/X/b/slide-decks/ch01-deck-intro.txt)", text)
        self.assertIn("[ch01-framing-intro.md](content/X/b/slide-decks/ch01-framing-intro.md)", text)
        self.assertIn(nt.DEFAULT_SLIDE_FORMAT, text)
        self.assertIn("`content/X/b/slide-decks/ch01-intro.pdf`", text)
        self.assertIn(".SKIP", text)
        self.assertIn("--resume", text)

    def test_locked_episode_table_unchanged(self) -> None:
        # Guard: the locked 4-column episode table format must not drift.
        self.assertEqual(nt.COLUMNS, ("Chapters", "Episodes", "Deep dive or debate", "Length"))
        self.assertEqual(nt.DEFAULT_LENGTH, "Long")


if __name__ == "__main__":
    unittest.main()
