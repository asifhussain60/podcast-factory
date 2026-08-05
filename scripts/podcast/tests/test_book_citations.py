"""Tests for _book_citations — how a Qur'anic citation is written and read back.

The rename cases run from the SHARED fixture at
plan-dashboard/scripts/lib/surah-names.fixtures.json, which the site's own test
runs too, so the two surah-name tables cannot drift apart.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_citations import (  # noqa: E402
    SURAH_NAMES,
    find_citations,
    rename_citations,
    surah_name,
    surah_number,
)

FIXTURES = Path(__file__).resolve().parents[3] / "plan-dashboard" / "scripts" / "lib" / "surah-names.fixtures.json"
FIXTURE = json.loads(FIXTURES.read_text(encoding="utf-8"))


# ── The shared table ──────────────────────────────────────────────────────────
def test_names_match_the_shared_fixture():
    """The pin. A one-sided edit fails here rather than drifting silently."""
    assert list(SURAH_NAMES) == FIXTURE["names"]


def test_the_table_is_the_whole_quran():
    assert len(SURAH_NAMES) == 114
    assert surah_name(1) == "Al-Fatihah"
    assert surah_name(114) == "An-Nas"


def test_a_number_outside_the_quran_has_no_name():
    for n in (0, -1, 115, 999):
        assert surah_name(n) == ""


def test_names_are_plain_ascii():
    """The house rule. A macron or a dot here reaches the printed page."""
    for name in SURAH_NAMES:
        assert name.isascii(), name


def test_a_name_round_trips_to_its_number():
    for i, name in enumerate(SURAH_NAMES, start=1):
        assert surah_number(name) == i


def test_a_name_is_read_however_it_is_written():
    assert surah_number("al kahf") == 18
    assert surah_number("AlKahf") == 18
    assert surah_number("AL-KAHF") == 18
    assert surah_number("not a surah") == 0


# ── Renaming ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIXTURE["renames"], ids=lambda c: c["in"])
def test_rename_matches_the_shared_fixture(case):
    assert rename_citations(case["in"])[0] == case["out"]


def test_rename_is_idempotent():
    once, _ = rename_citations('"..." (2:24) and (Quran 14:24-26)')
    twice, stats = rename_citations(once)
    assert twice == once
    assert stats["renamed"] == 0
    assert stats["already_named"] == 2


def test_a_reference_outside_the_quran_is_left_as_written():
    out, stats = rename_citations("(200:1)")
    assert out == "(200:1)"
    assert stats["unnamed_reference"] == ["(200:1)"]


def test_a_bare_ratio_in_prose_is_never_a_citation():
    """The parenthesis is what makes it a citation — REQ of the numeric pattern."""
    for text in ("a ratio of 2:24", "at 9:30 in the morning", "pages 12:14"):
        assert rename_citations(text)[0] == text


# ── Reading both forms back ───────────────────────────────────────────────────
def test_the_named_form_is_read_back():
    """The idempotency contract that makes the rename safe: the Arabic-injection
    pass must still see a cited verse after the citation has been renamed."""
    (c,) = list(find_citations('"..." (Al-Baqarah: 24)'))
    assert (c.surah, c.ayah, c.last) == (2, 24, None)


def test_the_numeric_form_is_still_read_back():
    (c,) = list(find_citations('"..." (Quran 21:98)'))
    assert (c.surah, c.ayah, c.last) == (21, 98, None)


def test_a_named_range_is_read_back():
    (c,) = list(find_citations("(Ibrahim: 24-26)"))
    assert (c.surah, c.ayah, c.last) == (14, 24, 26)


def test_an_ordinary_parenthetical_is_not_a_citation():
    """`(see: 24)` looks exactly like the house form and is not scripture. The
    captured text has to BE one of the 114 names."""
    assert list(find_citations("(see: 24)")) == []
    assert list(find_citations("(note: 3-4)")) == []


def test_both_forms_come_back_in_document_order():
    refs = [(c.surah, c.ayah) for c in find_citations("(2:24) then (Al-Kahf: 65) then (Q 53:39)")]
    assert refs == [(2, 24), (18, 65), (53, 39)]
