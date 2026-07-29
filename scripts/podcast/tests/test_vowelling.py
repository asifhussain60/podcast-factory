"""test_vowelling.py — the Python half of the vowelling-gate mirror pair.

Runs the SHARED fixtures at plan-dashboard/scripts/lib/vowelling.fixtures.json,
which plan-dashboard/scripts/lib/vowelling.test.mjs runs too. A change to either
implementation that is not matched in the other fails here or there, rather than
letting the Composer's Diacritics button and the compose-time vowelling pass
admit different things into book.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _vowelling import (  # noqa: E402
    is_arabic_passage,
    is_vowelling_candidate,
    mark_count,
    mark_density,
    rejection_reason,
    skeleton,
)

FIXTURES = Path(__file__).resolve().parents[3] / "plan-dashboard" / "scripts" / "lib" / "vowelling.fixtures.json"


@pytest.fixture(scope="module")
def fx() -> dict:
    assert FIXTURES.exists(), f"shared fixtures missing: {FIXTURES}"
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_skeleton_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["skeleton"]:
        assert skeleton(case["in"]) == case["out"], case["in"]


def test_mark_count_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["markCount"]:
        assert mark_count(case["in"]) == case["out"], case["in"]


def test_is_candidate_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["isCandidate"]:
        assert is_vowelling_candidate(case["in"]) is case["out"], case.get("_why", case["in"])


def test_is_arabic_passage_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["isArabicPassage"]:
        assert is_arabic_passage(case["in"]) is case["out"], case.get("_why", case["in"])


def test_rejection_reason_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["rejection"]:
        got = rejection_reason(case["source"], case["candidate"])
        if "outStartsWith" in case:
            assert got is not None and got.startswith(case["outStartsWith"]), case.get("_why", got)
        else:
            assert got == case["out"], case.get("_why", case["source"])


# ── This half's own coverage ───────────────────────────────────────────────
# The gate's whole job is to bound a model to vocalisation, so the cases that
# matter are the substitutions a model actually makes when asked to vowel.


def test_uthmani_substitution_is_refused() -> None:
    """The mushaf spells the istirja' with a dagger alif where the book uses a
    plain one. A model reaching for the canonical spelling changes letters."""
    book = "إنا لله وإنا إليه راجعون"
    uthmani = "إِنَّا لِلَّهِ وَإِنَّآ إِلَيْهِ رَٰجِعُونَ"
    reason = rejection_reason(book, uthmani)
    assert reason is not None and reason.startswith("letters changed")


def test_whitespace_alone_never_makes_a_vowelling_inadmissible() -> None:
    bare = "إن أفضل الحسنات إحياء الأموات"
    spaced = "إِنَّ  أَفْضَلَ الْحَسَنَاتِ\n إِحْيَاءُ الْأَمْوَاتِ"
    assert rejection_reason(bare, spaced) is None


def test_tatweel_is_not_a_letter() -> None:
    assert skeleton("العـــلم") == skeleton("العلم")


def test_mark_density_separates_bare_from_vowelled() -> None:
    assert mark_density("إن أفضل الحسنات إحياء الأموات") < 0.05
    assert mark_density("لَيْسَ كَمِثْلِهِ شَيْءٌ") > 0.4
    # No Arabic letters at all: a density of zero, not a division by zero.
    assert mark_density("plain english") == 0.0
