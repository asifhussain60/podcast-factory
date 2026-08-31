#!/usr/bin/env python3
"""A chapter begins with a capital letter — and the rule stops there.

The risk in a pass like this is not that it fails to capitalize. It is that it
capitalizes something it should not have touched: a word inside a code fence, a
list item, an Arabic word with no case, or — worst — that it quietly tidies away
a chapter that lost text at its boundary. Most of what follows pins the things it
must LEAVE ALONE.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _chapter_opening as co  # noqa: E402


def book(*chapters: str) -> str:
    return "# A Book\n\n" + "\n\n".join(chapters) + "\n"


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


def test_a_lowercase_opening_is_capitalized() -> None:
    src = book("## Love of the World\n\nand know that the love of the world is blameworthy.")
    assert "\nAnd know that" in co.capitalize_openings(src)


def test_the_live_case_from_the_library() -> None:
    # Exactly what Asif saw on the reader page on 2026-08-31.
    src = book("## Love of the World\n\nand know that the love of the world that is blameworthy is love")
    out = co.capitalize_openings(src)
    assert out.count("And know") == 1
    assert "and know" not in out


def test_only_the_first_paragraph_is_touched() -> None:
    src = book("## C\n\nfirst paragraph here.\n\nand this second one keeps its lowercase.")
    out = co.capitalize_openings(src)
    assert "First paragraph" in out
    assert "and this second one" in out


def test_every_chapter_gets_its_own_opening_fixed() -> None:
    src = book("## One\n\nalpha goes here.", "## Two\n\nbeta goes here.")
    out = co.capitalize_openings(src)
    assert "Alpha goes here" in out and "Beta goes here" in out


def test_running_it_twice_changes_nothing_the_first_run_did_not() -> None:
    src = book("## C\n\nand know that.")
    once = co.capitalize_openings(src)
    assert co.capitalize_openings(once) == once


def test_a_book_with_no_chapters_is_returned_unchanged() -> None:
    src = "# Just a title\n\nand some prose.\n"
    assert co.capitalize_openings(src) == src


# ---------------------------------------------------------------------------
# What it must not touch
# ---------------------------------------------------------------------------


def test_an_already_capital_opening_is_left_alone() -> None:
    src = book("## C\n\nWe ended on hasad last time.")
    assert co.capitalize_openings(src) == src


def test_arabic_script_is_left_exactly_as_it_is() -> None:
    src = book("## C\n\nحَسَدٌ is the disease under discussion.")
    assert co.capitalize_openings(src) == src


def test_a_heading_immediately_followed_by_a_subheading_is_left_alone() -> None:
    src = book("## C\n\n### a subheading\n\nand the prose.")
    out = co.capitalize_openings(src)
    assert "### a subheading" in out
    assert "And the prose" in out


def test_a_bullet_is_not_prose_and_is_skipped() -> None:
    src = book("## C\n\n- a bullet leads\n\nand then prose.")
    out = co.capitalize_openings(src)
    assert "- a bullet leads" in out
    assert "And then prose" in out


def test_a_blockquote_is_skipped() -> None:
    src = book("## C\n\n> a quoted line\n\nand then prose.")
    out = co.capitalize_openings(src)
    assert "> a quoted line" in out
    assert "And then prose" in out


def test_a_code_fence_is_never_edited() -> None:
    src = book("## C\n\n```\nand this is code\n```\n\nand this is prose.")
    out = co.capitalize_openings(src)
    assert "and this is code" in out
    assert "And this is prose" in out


def test_emphasis_markers_survive_and_the_letter_inside_is_raised() -> None:
    src = book("## C\n\n*and* know that.")
    assert "*And* know" in co.capitalize_openings(src)


def test_an_opening_quotation_keeps_its_quote_mark() -> None:
    src = book('## C\n\n"and know," he said.')
    assert '"And know,"' in co.capitalize_openings(src)


def test_a_digit_opening_is_left_alone() -> None:
    src = book("## C\n\n7 disciplines are named here.")
    assert co.capitalize_openings(src) == src


# ---------------------------------------------------------------------------
# The fragment — reported, never disguised
# ---------------------------------------------------------------------------


def test_a_fragment_opening_is_reported() -> None:
    # kitab-al-riyad chapter 6: text was lost at the chapter boundary.
    src = book("## 6. Parts or Traces?\n\ntelling, and short of it. It is now established that")
    found = co.fragment_openings(src)
    assert len(found) == 1
    assert found[0]["chapter"] == "6. Parts or Traces?"


def test_a_fragment_is_still_capitalized_because_the_rule_is_absolute() -> None:
    src = book("## C\n\ntelling, and short of it.")
    assert "Telling, and short of it." in co.capitalize_openings(src)


def test_an_ordinary_opening_is_not_called_a_fragment() -> None:
    src = book("## C\n\nand know that the love of the world is blameworthy.")
    assert co.fragment_openings(src) == []


def test_openings_reports_every_chapter_with_its_verdict() -> None:
    src = book("## One\n\nand know that.", "## Two\n\nWe ended on hasad.")
    rows = co.openings(src)
    assert [r["lowercase"] for r in rows] == [True, False]


def test_the_fragment_signal_is_read_before_the_capital_is_applied() -> None:
    """The bug this pins: checking after capitalizing finds nothing, always.

    `_FRAGMENT` keys on a LOWERCASE word before a comma, because that is what
    separates a lost sentence-tail from somebody opening with "However,". Run it
    on the capitalized text and the signal it looks for has just been erased.
    """
    src = book("## 6. Parts or Traces?\n\ntelling, and short of it. It is now established")
    assert co.fragment_openings(src), "the fragment must be visible before the fix"
    assert not co.fragment_openings(co.capitalize_openings(src)), (
        "after capitalizing the signal is gone — callers must read `before`"
    )


def test_a_capitalized_opening_before_a_comma_is_not_a_fragment() -> None:
    # "However," is a person starting a sentence, not a chapter that lost its head.
    src = book("## C\n\nHowever, the text turns to the heart.")
    assert co.fragment_openings(src) == []


def test_both_callers_read_the_pre_capitalization_text() -> None:
    """A grep, because the ordering is invisible at the call site otherwise."""
    root = Path(__file__).resolve().parents[1]
    # The step body lives with the rule (it moved out of `_book_apparatus` in the
    # 2026-08-31 split), so this follows it rather than pinning a stale location.
    module = (root / "_chapter_opening.py").read_text(encoding="utf-8")
    assert "fragment_openings(before)" in module
    assert "fragment_openings(after)" not in module
    script = (root / "normalize_chapter_openings.py").read_text(encoding="utf-8")
    assert "openings(before)" in script
