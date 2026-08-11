#!/usr/bin/env python3
"""A quoted verse is recognised as scripture, or it is drawn as somebody's saying.

The reader decides which card a quotation gets by MATCHING the canonical mushaf exactly.
So anything attached to the run — even something invisible — decides whether the reader
sets it in the Uthmanic face under an `Al-Baqarah: 257` band, or as a generic quotation.

The KSESSIONS Quran widget attached two such things to every verse, and both were
invisible on the page:

  the ayah number   `۲۵۷` in Arabic-Indic digits, appended INSIDE the verse
  bidi marks        `&rlm;` / `&lrm;` wrapped around it so the Arabic would lay out
                    correctly inside the admin's own left-to-right page

Together they cost Surah Al-Fateha 67 of its 75 quotations and Love Of The Prophet 30 of
its 48. The defect is deliberately hard to see by reading — which is why the assertions
below are about the MATCH rather than about the text.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_defect_fixes import FIXES, clean_verse_lines  # noqa: E402
from _book_defects import DETECTORS, clean_verse_line, quote_line_noise  # noqa: E402

#: Qur'an 2:257 as the mushaf holds it.
VERSE = "ٱللَّهُ وَلِىُّ ٱلَّذِينَ آمَنُوا۟ يُخْرِجُهُم مِّنَ ٱلظُّلُمَتِ إِلَى ٱلنُّورِ"

#: And as the widget printed it: an RLM in front, the ayah number and an LRM behind.
AS_PRINTED = f"‏{VERSE} ‎۲۵۷"


def chapter(body: str) -> str:
    return f"# Book\n\n## A Chapter\n\n{body}\n"


# ---------------------------------------------------------------------------
# What comes off, and what must not
# ---------------------------------------------------------------------------


def test_the_widgets_debris_comes_off_and_the_verse_is_untouched() -> None:
    assert clean_verse_line(AS_PRINTED) == VERSE


@pytest.mark.parametrize(
    "line",
    [
        VERSE,  # nothing attached
        "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "قَالَ رَسُولُ ٱللَّهِ",  # a saying, not scripture — still left exactly as it is
    ],
)
def test_a_clean_line_is_returned_unchanged(line: str) -> None:
    assert clean_verse_line(line) == line


def test_a_digit_inside_the_verse_is_part_of_the_text() -> None:
    """Only a TRAILING numeral is the widget's. The pattern is anchored to the end
    because no mushaf verse ends in one, and a digit mid-run belongs to the reading."""
    mid = "ٱلْحَمْدُ ۳ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ"
    assert clean_verse_line(mid) == mid


def test_an_english_line_is_not_touched() -> None:
    """A trailing number on an English line is a citation somebody wrote."""
    md = chapter("> He read it aloud in 1998")
    assert quote_line_noise(md) == []
    assert clean_verse_lines(md)[1] == 0


# ---------------------------------------------------------------------------
# The detector and the repair, over a chapter
# ---------------------------------------------------------------------------


def test_a_quoted_verse_carrying_debris_is_found() -> None:
    md = chapter(f"> {AS_PRINTED}\n>\n> Allah is the protector of those who believe.")
    assert len(quote_line_noise(md)) == 1


def test_the_repair_leaves_the_quotation_marker_and_the_translation_alone() -> None:
    md = chapter(f"> {AS_PRINTED}\n>\n> Allah is the protector of those who believe.")
    out, fixed = clean_verse_lines(md)
    assert fixed == 1
    assert f"> {VERSE}" in out
    assert "> Allah is the protector of those who believe." in out
    assert quote_line_noise(out) == []


def test_the_repair_is_idempotent() -> None:
    md = chapter(f"> {AS_PRINTED}")
    once, _ = clean_verse_lines(md)
    assert clean_verse_lines(once)[1] == 0


def test_not_one_arabic_letter_changes() -> None:
    """The whole repair is deletion of things that carry no letter. A vowelling that
    changed a consonant would be refused elsewhere; so would this."""
    out, _ = clean_verse_lines(chapter(f"> {AS_PRINTED}"))
    letters = lambda s: [c for c in s if "ؠ" <= c <= "ي"]  # noqa: E731
    assert letters(out) == letters(chapter(f"> {AS_PRINTED}"))


def test_the_check_and_its_repair_are_both_registered() -> None:
    """A detector with no repair reports a defect nothing fixes; a repair with no
    detector never runs. Both halves or neither."""
    assert "quote-line-noise" in DETECTORS
    assert "quote-line-noise" in FIXES


# ---------------------------------------------------------------------------
# The end the whole thing exists for
# ---------------------------------------------------------------------------


def test_the_cleaned_verse_is_what_the_mushaf_holds() -> None:
    """The proof that the removal was the right removal: the canonical text recognises
    the cleaned line and does not recognise the printed one."""
    from _mushaf import is_quranic

    assert is_quranic(clean_verse_line(AS_PRINTED))
