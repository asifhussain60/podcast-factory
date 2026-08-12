#!/usr/bin/env python3
"""A devotional formula reaches the page in script, and an orphan `**` does not reach it.

Two defects found together in the Sessions books, both of them written by Asif into the
KSESSIONS admin years ago and both invisible to every gate until Surah Al-Fateha was
ingested:

  romanized-honorific   197 in Surah Al-Fateha, 81 in Love Of The Prophet. Reported as
                        `romanized-arabic`, whose answer is "nothing here applies a
                        repair", so 278 fixable instances read as unfixable.

  stray-emphasis        16 in Love Of The Prophet, on the live site. A `**` whose partner
                        is in a different paragraph of the same quotation.

Every case below is one of those, or the thing that must NOT be caught with them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_defect_fixes import (  # noqa: E402
    FIXES,
    balance_paragraph_emphasis,
    set_honorifics_in_script,
)
from _book_defects import romanized_arabic, stray_emphasis  # noqa: E402
from _book_honorific_defects import (  # noqa: E402
    ROMANIZED_HONORIFICS,
    honorific_script,
    romanized_honorific,
)

LIGATURE = "ﷺ"
ALLAH = "سُبْحَانَهُ وَتَعَالَى"


def chapter(body: str) -> str:
    return f"# Book\n\n## A Chapter\n\n{body}\n"


# ---------------------------------------------------------------------------
# The formula goes into script
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "want"),
    [
        ("Rasul Allah(Salallahu alayhi wa aalihee wa sallam) said", f"Rasul Allah {LIGATURE} said"),
        ("the prophet (Salallahu alayhi wa aalihee wa sallam).", f"the prophet {LIGATURE}."),
        ("The Prophet (SWS) taught", f"The Prophet {LIGATURE} taught"),
        ("Rasul Allah's (SWS) life", f"Rasul Allah's {LIGATURE} life"),
        ("Allah (Subhanahu wa Ta'ala) is", f"Allah {ALLAH} is"),
        ("Allah (Subhanhu Wa Ta'ala) is", f"Allah {ALLAH} is"),
    ],
)
def test_a_spelled_out_honorific_is_set_in_script(source: str, want: str) -> None:
    out, count = set_honorifics_in_script(source)
    assert out == want
    assert count == 1


def test_the_bracket_goes_with_the_romanization() -> None:
    """A honorific in script is not parenthetical in this library — `the Prophet ﷺ` is how
    every other book sets it."""
    out, _ = set_honorifics_in_script("the Prophet (SWS) said")
    assert "(" not in out and ")" not in out


def test_a_missing_space_before_the_bracket_does_not_fuse_the_glyph_to_the_name() -> None:
    """The transcripts write `Rasul Allah(Salallahu…)` as often as not."""
    out, _ = set_honorifics_in_script("Rasul Allah(SWS) said")
    assert out == f"Rasul Allah {LIGATURE} said"


def test_the_repair_is_idempotent() -> None:
    once, _ = set_honorifics_in_script("the Prophet (SWS) and Allah (Subhanahu wa Ta'ala)")
    twice, count = set_honorifics_in_script(once)
    assert count == 0
    assert twice == once


def test_allahs_honorific_carries_its_vowel_marks() -> None:
    """Arabic this repo WRITES carries its marks — the standing rule since 2026-07-29.
    The Prophet's is one ligature glyph and has none to carry."""
    assert any(mark in ALLAH for mark in "َُِّْ")
    assert honorific_script("Subhanahu wa Ta'ala") == ALLAH


# ---------------------------------------------------------------------------
# What must NOT be swept up with it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "the saying (Ana madinatul-ilm wa 'Ali babuha) is famous",  # a SAYING — never repaired
        "he read it (Surah al-Talaq, 65:1) aloud",  # a citation
        "the term (*ribh ma lam yudman*) means",  # an italic technical term
        "he saw it (finally) happen",  # ordinary English
    ],
)
def test_something_that_is_not_a_honorific_is_left_alone(text: str) -> None:
    out, count = set_honorifics_in_script(text)
    assert count == 0
    assert out == text


def test_a_saying_is_still_reported_as_needing_judgment() -> None:
    """The refusal that stands: a saying has a specific Arabic wording that is not on
    disk, and only a model recalling scripture could supply it."""
    # Its own script beside it, which is where a saying actually sits and is the
    # strongest evidence the detector has that the bracket is Arabic at all.
    md = chapter("أَنَا مَدِينَةُ الْعِلْمِ\n\nHe said it (Ana madinatul-ilm wa 'Ali babuha) plainly.")
    assert len(romanized_arabic(md)) == 1
    assert romanized_honorific(md) == []


def test_a_honorific_is_reported_once_by_the_check_that_can_repair_it() -> None:
    """Reported by both, it would be listed as needing judgment it does not need — which
    is exactly how 197 repairable instances came to read as unfixable."""
    md = chapter("Allah (Subhanahu wa Ta'ala) and the Prophet (SWS) both.")
    assert len(romanized_honorific(md)) == 2
    assert romanized_arabic(md) == []


def test_every_registered_form_is_recognised_and_repaired() -> None:
    """A pattern in the table with no repair behind it would report a defect nothing
    fixes — the exact shape this whole change removes."""
    for script in ROMANIZED_HONORIFICS.values():
        assert script.strip()
    assert "romanized-honorific" in FIXES


# ---------------------------------------------------------------------------
# The orphaned emphasis marker
# ---------------------------------------------------------------------------

# The live shape, verbatim in structure: an opener on the attribution line and a closer
# four paragraphs later. The BLOCK's count is even, which is why a block-level check saw
# nothing while sixteen asterisks printed.
LIVE_QUOTE = chapter(
    "> **Muhammad Ibn Abdullah — Accountability, Deeds\n"
    ">\n"
    "> حَاسِبُوا أَنْفُسَكُمْ\n"
    ">\n"
    "> Hold yourselves accountable before you are held accountable**"
)


def test_a_marker_whose_partner_is_in_another_paragraph_is_found() -> None:
    assert len(stray_emphasis(LIVE_QUOTE)) == 2


def test_the_block_level_count_is_even_which_is_why_the_paragraph_is_the_unit() -> None:
    assert LIVE_QUOTE.count("**") % 2 == 0


def test_the_opener_is_closed_in_its_own_paragraph_and_the_orphan_deleted() -> None:
    out, fixed = balance_paragraph_emphasis(LIVE_QUOTE)
    assert fixed == 2
    assert "> **Muhammad Ibn Abdullah — Accountability, Deeds**" in out
    assert out.rstrip().endswith("held accountable")
    assert stray_emphasis(out) == []


def test_not_one_word_changes() -> None:
    out, _ = balance_paragraph_emphasis(LIVE_QUOTE)
    assert out.replace("*", "").split() == LIVE_QUOTE.replace("*", "").split()


def test_balancing_is_idempotent() -> None:
    once, _ = balance_paragraph_emphasis(LIVE_QUOTE)
    assert balance_paragraph_emphasis(once)[1] == 0


def test_emphasis_that_pairs_inside_its_own_paragraph_is_left_alone() -> None:
    md = chapter("He called it **the summit** of the matter.\n\n> **Speaker**\n>\n> A saying.")
    assert stray_emphasis(md) == []
    assert balance_paragraph_emphasis(md)[1] == 0


def test_a_single_asterisk_is_not_an_emphasis_pair() -> None:
    """Italics are one asterisk and are not this check's business."""
    md = chapter("He read *Kitab al-Riyad* twice.")
    assert stray_emphasis(md) == []
