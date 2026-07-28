"""Fixture-pinned tests for the Buckwalter ↔ Arabic converter.

Ground truth lives in tests/fixtures/buckwalter.fixtures.json (see its _comment).
A failure here means the transliteration table drifted — which would corrupt the
skeleton join keys the morphology layer feeds the etymology veto and the
deterministic glossary fill.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import _buckwalter as bw  # noqa: E402

FIXTURES = REPO / "plan-dashboard" / "scripts" / "lib" / "buckwalter.fixtures.json"
assert FIXTURES.is_file(), f"shared fixture file missing: {FIXTURES}"
FIX = json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIX["bw2ar_cases"], ids=lambda c: c["name"])
def test_bw2ar_matches_the_shared_fixtures(case: dict) -> None:
    assert bw.bw2ar(case["bw"]) == case["ar"]


@pytest.mark.parametrize("case", FIX["bw2ar_cases"], ids=lambda c: c["name"])
def test_ar2bw_is_the_exact_inverse(case: dict) -> None:
    assert bw.ar2bw(case["ar"]) == case["bw"]


@pytest.mark.parametrize("case", FIX["bw2ar_cases"], ids=lambda c: c["name"])
def test_round_trip_is_lossless(case: dict) -> None:
    assert bw.ar2bw(bw.bw2ar(case["bw"])) == case["bw"]


@pytest.mark.parametrize("case", FIX["skeleton_cases"], ids=lambda c: c["name"])
def test_bw_skeleton_matches_the_shared_fixtures(case: dict) -> None:
    assert bw.bw_skeleton(case["bw"]) == case["skeleton"]


@pytest.mark.parametrize("bad", FIX["invalid_buckwalter"])
def test_strict_raises_on_non_buckwalter(bad: str) -> None:
    with pytest.raises(ValueError):
        bw.bw2ar(bad)


def test_non_strict_drops_unknown_characters() -> None:
    assert bw.bw2ar("rHm?", strict=False) == "رحم"


def test_table_is_bijective() -> None:
    assert len(bw._AR2BW) == len(bw._BW2AR)


def test_empty_and_none_are_safe() -> None:
    assert bw.bw2ar("") == ""
    assert bw.bw_skeleton("") == ""


@pytest.mark.parametrize("case", FIX["fold_cases"], ids=lambda c: c["name"])
def test_folds_match_the_shared_fixtures(case: dict) -> None:
    assert bw.latin_fold(case["latin"]) == case["latin_fold"]
    assert bw.arabic_fold(case["skeleton"]) == case["arabic_fold"]
    assert bw.folds_match(case["latin_fold"], case["arabic_fold"]) is case["match"]


@pytest.mark.parametrize("case", FIX["normalize_cases"], ids=lambda c: c["name"])
def test_normalize_arabic_matches_the_shared_fixtures(case: dict) -> None:
    from _arabic_coverage import normalize_arabic

    assert normalize_arabic(case["arabic"]) == case["skeleton"]


def test_folds_never_match_empty() -> None:
    assert not bw.folds_match("", "")
    assert not bw.folds_match("nfs", "")
    assert not bw.folds_match("", "nfs")
