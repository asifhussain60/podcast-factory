"""Introduce an honorific in full, then abbreviate it.

The rule: the FIRST occurrence in the book prints the full formula, every later
one prints the abbreviation. `the-master-and-the-disciple` shipped six `(ع)` with
no full form in front of any of them, so the first one taught the reader nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _honorifics import (  # noqa: E402
    HONORIFIC_ABBREVIATIONS,
    expand_first_honorific_use,
)

_FULL = "عليه السلام"


def test_the_first_use_is_spelled_out_and_the_rest_are_not() -> None:
    text = "So Joseph (ع) said, and Lot (ع) heard, and Moses (ع) answered."
    out, n = expand_first_honorific_use(text)
    assert n == 1
    assert out == f"So Joseph ({_FULL}) said, and Lot (ع) heard, and Moses (ع) answered."


def test_first_use_is_scoped_to_the_book_not_the_chapter() -> None:
    # A convention is introduced once, in the copy the reader holds. Per chapter it
    # would be spelled out nine times and stop being a convention.
    text = "## 1. One\n\nJoseph (ع) spoke.\n\n## 2. Two\n\nLot (ع) heard.\n"
    out, n = expand_first_honorific_use(text)
    assert n == 1
    assert out.count(_FULL) == 1 and out.count("(ع)") == 1


def test_a_full_form_already_present_counts_as_the_introduction() -> None:
    # A book that already spells one out is left exactly as it is.
    text = f"Adam ({_FULL}) first, then Joseph (ع)."
    out, n = expand_first_honorific_use(text)
    assert n == 0 and out == text


def test_the_pass_is_idempotent() -> None:
    text = "Joseph (ع) and Lot (ع) and Moses (ع)."
    once, _ = expand_first_honorific_use(text)
    twice, n = expand_first_honorific_use(once)
    assert twice == once and n == 0


def test_each_family_is_tracked_separately() -> None:
    # Singular and plural address different people, so seeing one teaches the
    # reader nothing about the other.
    text = "Fatima (س) and Joseph (ع)."
    out, n = expand_first_honorific_use(text)
    assert n == 2
    assert "عليها السلام" in out and _FULL in out


def test_ordinary_parentheses_are_left_alone() -> None:
    text = "The year (a lunar one) is completed in twelve months (see chapter 3)."
    out, n = expand_first_honorific_use(text)
    assert n == 0 and out == text


def test_a_plural_formula_does_not_introduce_the_singular_abbreviation() -> None:
    text = "Ishmael and Isaac (عليهم السلام), then Moses (ع)."
    out, n = expand_first_honorific_use(text)
    assert n == 1 and _FULL in out


def test_every_registered_expansion_round_trips() -> None:
    for abbrev, full in HONORIFIC_ABBREVIATIONS.items():
        out, n = expand_first_honorific_use(f"X ({abbrev}) then Y ({abbrev}).")
        assert n == 1, abbrev
        assert out == f"X ({full}) then Y ({abbrev})."
