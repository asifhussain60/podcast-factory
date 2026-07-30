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
    reflow_to_source_whitespace,
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


def test_reflow_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["reflow"]:
        got = reflow_to_source_whitespace(case["source"], case["candidate"])
        assert got == case["out"], case.get("_why", case["source"])


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


def test_a_digit_is_not_a_mark() -> None:
    """The regression that made unattended source vowelling unsafe.

    Arabic-Indic digits sit inside U+0653-U+0670, the span the mark class used to
    cover, so `skeleton` deleted them from BOTH sides of the comparison and a
    model that dropped every footnote and verse number while vowelling was
    admitted as "marks only". This is a real line from the Master-and-Disciple OCR.
    """
    line = "تأليف ١ سيدنا جعفر بن منصور ٢ اليمن٣"
    assert mark_count(line) == 0, "a bare line carries no marks, digits included"
    assert skeleton(line) == line, "digits belong to the skeleton"
    stripped = "تَأْلِيف سَيِّدنَا جَعْفَر بْن مَنْصُور اليَمَن"
    reason = rejection_reason(line, stripped)
    assert reason is not None and reason.startswith("letters changed")


def test_reflow_restores_line_structure_without_moving_marks() -> None:
    """`skeleton` collapses whitespace, so a collapsed multi-line run passes the
    gate. Reflow is what keeps the source's shape — 886 of 1,395 runs in one
    book's OCR span more than one line, and the bilingual build slices by line."""
    source = "قال العالم\nودموعه تنحدر\nعلى لحيته"
    collapsed = "قَالَ الْعَالِمُ وَدُمُوعُهُ تَنْحَدِرُ عَلَى لِحْيَتِهِ"
    out = reflow_to_source_whitespace(source, collapsed)
    assert out.count("\n") == source.count("\n")
    assert skeleton(out) == skeleton(source)
    assert mark_count(out) == mark_count(collapsed), "reflow must not drop a mark"
    assert rejection_reason(source, out) is None
    # Idempotent, and a non-aligning candidate is handed back for the gate to judge.
    assert reflow_to_source_whitespace(source, out) == out
    assert reflow_to_source_whitespace(source, "كلام آخر") == "كلام آخر"


def test_mark_density_separates_bare_from_vowelled() -> None:
    assert mark_density("إن أفضل الحسنات إحياء الأموات") < 0.05
    assert mark_density("لَيْسَ كَمِثْلِهِ شَيْءٌ") > 0.4
    # No Arabic letters at all: a density of zero, not a division by zero.
    assert mark_density("plain english") == 0.0


# ── Canonical scripture comes from the corpus, not from a model ────────────


def test_mushaf_vocalisation_returns_the_canonical_text() -> None:
    """A bare verse resolves to the mushaf's own vowelled words."""
    from _mushaf import mushaf_available, mushaf_vocalisation

    if not mushaf_available():  # pragma: no cover - mirror.db is tracked in git
        pytest.skip("canonical mushaf unavailable")
    source = "إنا لله وإنا إليه راجعون"
    got = mushaf_vocalisation(source)
    assert got is not None
    assert mark_count(got) > 5, "the canonical text is fully vowelled"
    # Uthmani, deliberately, and this is the one place in the repo where a
    # changed LETTER is right: the mushaf writes `رَجِعُونَ` without the alif that
    # modern spelling supplies, so the skeletons differ. Asserting that they do
    # pins the documented behaviour — the text inserted is the verse itself, not
    # a re-marking of the book's spelling of it.
    assert skeleton(got) != skeleton(source)


def test_mushaf_vocalisation_declines_a_span_that_does_not_align() -> None:
    """No fuzzy tail, no partial window: a near-miss returns nothing at all.

    The failure mode being refused is replacing a quotation with a DIFFERENT
    extent of the verse, which would silently change what the book quotes.
    """
    from _mushaf import mushaf_available, mushaf_vocalisation

    if not mushaf_available():  # pragma: no cover
        pytest.skip("canonical mushaf unavailable")
    assert mushaf_vocalisation("قال الشيخ لتلميذه في ذلك اليوم") is None
    assert mushaf_vocalisation("") is None
