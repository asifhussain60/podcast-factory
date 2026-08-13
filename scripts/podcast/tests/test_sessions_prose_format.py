#!/usr/bin/env python3
"""_sessions_prose_format.py — heading/citation normalization for a Sessions
chapter, never touching prose. Real cases pinned from surah-al-fateha's
"Quranic Friendship" chapter, the first place these defects were found."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _sessions_prose_format import (  # noqa: E402
    normalize_bare_citations,
    normalize_headings,
    normalize_sessions_prose,
)

# A real Qur'anic verse (Q81:22, At-Takwir) and a non-Qur'anic Arabic phrase,
# for the "never guess" boundary.
_REAL_VERSE = "وَمَا صَاحِبُكُم بِمَجْنُونٍۢ"
_NOT_QURANIC = "هذا الكلام ليس من القرآن الكريم على الإطلاق أبدا"


# ─── normalize_headings ─────────────────────────────────────────────────────


def test_heading_arabic_moves_into_parens() -> None:
    body = "### Trustworthy Friend ولیجۃ\n\nWALEEJA\n\nSome prose here.\n"
    new_body, changes = normalize_headings(body)
    assert "### Trustworthy Friend (ولیجۃ)" in new_body
    assert "WALEEJA" not in new_body
    assert "Some prose here." in new_body
    kinds = [c["kind"] for c in changes]
    assert kinds == ["heading-parenthesized", "transliteration-removed"]


def test_heading_with_no_translit_line_is_left_otherwise_untouched() -> None:
    body = "### Protective Friend ولی\n\nThe first of those friends is ولی.\n"
    new_body, changes = normalize_headings(body)
    assert "### Protective Friend (ولی)" in new_body
    assert "The first of those friends is ولی." in new_body
    assert len(changes) == 1  # only the heading, nothing to strip


def test_heading_with_no_arabic_is_untouched() -> None:
    body = "## The Stages Of Love\n\nSome prose.\n"
    new_body, changes = normalize_headings(body)
    assert new_body == body
    assert changes == []


def test_a_lowercase_word_after_a_heading_is_never_mistaken_for_translit() -> None:
    body = "### Confidant بِطانۃ\n\nAnother kind of friendship is بِطانۃ.\n"
    new_body, changes = normalize_headings(body)
    assert "Another kind of friendship is بِطانۃ." in new_body
    assert len(changes) == 1  # only the heading


# ─── normalize_bare_citations ───────────────────────────────────────────────


def test_bare_citation_above_an_already_carded_verse_is_dropped() -> None:
    body = f"Allah says:\n\n81:22\n\n> {_REAL_VERSE}\n>\n> And your companion is not a madman;\n\nMore prose.\n"
    new_body, changes = normalize_bare_citations(body)
    assert "81:22" not in new_body
    assert _REAL_VERSE in new_body
    assert changes == [{"kind": "citation-line-removed", "ref": "81:22", "reason": "already carded"}]


def test_bare_citation_above_a_bare_verse_gets_wrapped() -> None:
    body = (
        f"Allah says about them in the Quran\n\n26:99-101\n\n{_REAL_VERSE}\n\nSo they're saying it is not our fault.\n"
    )
    new_body, changes = normalize_bare_citations(body)
    assert "26:99-101" not in new_body
    assert f"> {_REAL_VERSE}" in new_body
    assert "So they're saying it is not our fault." in new_body  # commentary untouched, not swallowed
    assert changes == [{"kind": "citation-wrapped", "ref": "26:99-101", "arabic": _REAL_VERSE}]


def test_a_reference_over_non_quranic_arabic_is_left_completely_alone() -> None:
    body = f"He said:\n\n5:5\n\n{_NOT_QURANIC}\n\nMore prose.\n"
    new_body, changes = normalize_bare_citations(body)
    assert new_body == body
    assert changes == []


def test_a_reference_with_nothing_arabic_following_is_left_alone() -> None:
    body = "The score was\n\n5:5\n\nin the second half.\n"
    new_body, changes = normalize_bare_citations(body)
    assert new_body == body
    assert changes == []


def test_ordinary_prose_mentioning_arabic_inline_is_never_wrapped() -> None:
    """The false-positive guard: a normal sentence with an inline Arabic word
    must never be mistaken for a bare verse line just because a citation-like
    number sits somewhere nearby."""
    body = "See the chapter numbered\n\n2:257\n\nThis is why the name is صاحب, not a verse at all.\n"
    new_body, changes = normalize_bare_citations(body)
    assert new_body == body
    assert changes == []


def test_citation_normalization_is_idempotent() -> None:
    body = f"Allah says:\n\n81:22\n\n> {_REAL_VERSE}\n\nMore prose.\n"
    once, _ = normalize_bare_citations(body)
    twice, changes2 = normalize_bare_citations(once)
    assert once == twice
    assert changes2 == []


# ─── normalize_sessions_prose (combined) ────────────────────────────────────


def test_combined_pass_is_idempotent_on_a_real_chapter_shape() -> None:
    body = (
        "### Trustworthy Friend ولیجۃ\n\nWALEEJA\n\n"
        f"The next word the Quran uses is ولیجۃ. Allah says:\n\n81:22\n\n"
        f"> {_REAL_VERSE}\n>\n> And your companion is not a madman;\n\n"
        "More prose follows.\n"
    )
    once, changes = normalize_sessions_prose(body)
    twice, changes2 = normalize_sessions_prose(once)
    assert once == twice
    assert changes2 == []
    assert "### Trustworthy Friend (ولیجۃ)" in once
    assert "WALEEJA" not in once
    assert "81:22" not in once
