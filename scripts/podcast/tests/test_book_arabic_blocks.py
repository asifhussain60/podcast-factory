"""One shape for every Arabic display quotation (Asif, 2026-08-05).

The cases are the shapes `ayyuhal-walad` actually held: a bracketed bare
paragraph, a blockquote whose rendering sat outside it, a verse with a trailing
citation, and — the one that must NOT change — a rendering the author continues
into his own commentary.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_arabic_blocks import normalize_arabic_blocks  # noqa: E402

VERSE = "مَنْ جَاوَزَ الْأَرْبَعِينَ وَلَمْ يَغْلِبْ خَيْرُهُ عَلَىٰ شَرِّهِ فَلْيَتَجَهَّزْ إِلَىٰ النَّارِ"
SHORT = "إِلَّا مَن تَابَ وَآمَنَ وَعَمِلَ صَلِحًۭا"


def test_a_bracketed_bare_paragraph_becomes_a_blockquote_without_its_brackets() -> None:
    body = f"He said:\n\n({VERSE})\n\nAnd then he went on."
    out, stats = normalize_arabic_blocks(body)
    assert out == f"He said:\n\n> {VERSE}\n\nAnd then he went on."
    assert stats["promoted"] == 1


def test_the_rendering_is_pulled_into_the_quotation() -> None:
    body = f'He said:\n\n> {VERSE}\n\n"Whoever passes forty years of age."\n\nAnd then.'
    out, stats = normalize_arabic_blocks(body)
    assert out == f'He said:\n\n> {VERSE}\n>\n> "Whoever passes forty years of age."\n\nAnd then.'
    assert stats["translations_joined"] == 1


def test_a_trailing_citation_is_part_of_the_rendering() -> None:
    body = f'\n\n> {VERSE}\n\n"And that man shall have nothing but that for which he strives." (Quran, an-Najm: 38)\n'
    out, stats = normalize_arabic_blocks(body)
    assert stats["translations_joined"] == 1
    assert '> "And that man shall have nothing but that for which he strives." (Quran, an-Najm: 38)' in out


def test_a_rendering_the_author_continues_is_left_outside() -> None:
    """THE ONE THAT MUST NOT MOVE. Pulling the commentary in would attribute the
    author's own sentence to scripture — fidelity, not formatting."""
    body = f'\n\n> {VERSE}\n\n"And in the hours before dawn they would seek forgiveness." (al-Dhariyat: 18) In this there is a sign.\n'
    out, stats = normalize_arabic_blocks(body)
    assert out == body
    assert stats["translations_joined"] == 0


def test_a_short_quranic_verse_is_a_display_quotation_too() -> None:
    """Exactly 20 Arabic letters — under `is_arabic_block`'s bar, which is why
    two verses stayed bare paragraphs and printed black."""
    body = f"He said:\n\n({SHORT})\n\nAnd then."
    out, stats = normalize_arabic_blocks(body)
    assert out == f"He said:\n\n> {SHORT}\n\nAnd then."
    assert stats["promoted"] == 1


def test_english_prose_that_merely_contains_arabic_is_not_promoted() -> None:
    body = "He named the Bayt al-Mamur (الْبَيْت) in passing, and moved on to other matters entirely."
    out, stats = normalize_arabic_blocks(body)
    assert out == body
    assert stats == {"promoted": 0, "translations_joined": 0}


def test_a_heading_or_html_line_is_never_touched() -> None:
    body = f"## 1. A Chapter\n\n<!-- editorial:begin -->\n\n> {VERSE}\n"
    out, _ = normalize_arabic_blocks(body)
    assert out.startswith("## 1. A Chapter\n\n<!-- editorial:begin -->")


def test_running_it_twice_changes_nothing_the_second_time() -> None:
    body = f'He said:\n\n({VERSE})\n\n"Whoever passes forty years of age."\n\nAnd then.'
    once, _ = normalize_arabic_blocks(body)
    twice, stats = normalize_arabic_blocks(once)
    assert once == twice
    assert stats == {"promoted": 0, "translations_joined": 0}


def test_a_quotation_with_no_rendering_after_it_is_left_alone() -> None:
    body = f"He said:\n\n> {VERSE}\n\nAnd the next thing he said was something else.\n"
    out, stats = normalize_arabic_blocks(body)
    assert out == body
    assert stats["translations_joined"] == 0
