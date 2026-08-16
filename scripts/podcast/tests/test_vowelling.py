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
    orphaned_marks,
    reflow_to_source_whitespace,
    reflow_words_to_source_whitespace,
    rejection_reason,
    skeleton,
    strip_orphaned_marks,
    transfer_marks,
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


def test_transfer_marks_matches_shared_fixtures(fx: dict) -> None:
    """The recovery, on the refusals that actually happened.

    Each case is a real entry from a book's recorded refusals, when a refusal was
    terminal and the passage stayed bare. A `None` is as load-bearing as a string:
    it is the gate still refusing where it must.
    """
    for case in fx["transfer"]:
        got = transfer_marks(case["source"], case["candidate"])
        assert got == case["out"], case.get("_why", case["source"])


def test_a_transferred_vowelling_always_passes_the_gate(fx: dict) -> None:
    """The guarantee is structural, not a second check that could disagree.

    Whatever comes back carries the SOURCE's letters, so its skeleton is
    source-identical by construction — `rejection_reason` can only refuse it for
    adding no marks, which a real vowelling never does.
    """
    from _vowelling import rejection_reason, skeleton

    for case in fx["transfer"]:
        got = transfer_marks(case["source"], case["candidate"])
        if got is None:
            continue
        assert skeleton(got) == skeleton(case["source"])
        assert rejection_reason(case["source"], got) is None


def test_reflow_words_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["reflowWords"]:
        got = reflow_words_to_source_whitespace(case["source"], case["candidate"])
        assert got == case["out"], case.get("_why", case["source"])


def test_an_orphan_mark_does_not_derail_the_reflow() -> None:
    """The defect that cost a 45-minute paid run on a real book.

    A scan can leave a combining mark with no letter under it. Consuming that
    orphan AS a letter put every later letter off by one; the walk ran off the end
    of the candidate and the repair gave up, handing back the model's collapsed
    single line. `rejection_reason` cannot see that — `skeleton` normalises
    whitespace before comparing — so the collapse was ADMITTED and the file
    silently lost lines.
    """
    source = "ْ توكل على الله\nإذا عزمت"
    collapsed = "ْ تَوَكَّلْ عَلَى اللهِ إِذَا عَزَمْتَ"
    out = reflow_to_source_whitespace(source, collapsed)
    assert out.count("\n") == source.count("\n"), "the orphan mark broke the alignment"
    assert skeleton(out) == skeleton(source)
    assert mark_count(out) == mark_count(collapsed), "the orphan mark itself must survive"
    # It lands after the adjacent space rather than before it — the source's marks
    # are skipped and the candidate's orphan is emitted when the walk next looks
    # for a letter. Harmless: a letterless mark moving across whitespace changes
    # nothing the gate, a reader, or a reader-of-lines can see.
    assert out.lstrip().startswith("ْ")


def test_a_mushaf_verse_keeps_the_line_break_the_book_printed() -> None:
    """The second half of the same failure.

    A Qur'anic run is replaced by canonical UTHMANI text, whose letters differ, so
    the character-level reflow correctly declines to align it — and the mushaf
    returns the verse's words joined by single spaces. A verse the book prints
    across two lines therefore came back as one, and the file lost a line.
    """
    source = "ليس كمثله\nشيء"
    canonical = "لَيْسَ كَمِثْلِهِۦ شَىْءٌۭ"
    assert reflow_to_source_whitespace(source, canonical) == canonical, "letters differ; must decline"
    out = reflow_words_to_source_whitespace(source, canonical)
    assert out.count("\n") == source.count("\n")
    assert out.split() == canonical.split(), "only the whitespace may move"
    # A word-count mismatch is handed back rather than reshaped to fit.
    assert reflow_words_to_source_whitespace(source, "لَيْسَ") == "لَيْسَ"


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


# ─── orphaned_marks / strip_orphaned_marks — the Kitab al-Riyad defect class ──
# `book/book.md` printed "Rahat al-Aqlِ," -- a kasra (U+0650) glued onto the
# Latin word "Aql" with no Arabic run anywhere near it on the page. Whatever
# pass produced it, `skeleton()` would have read that mark as vocalising the
# Latin "l" it happened to trail, which is not a vocalisation of anything.
# These prove the guard catches exactly this class and nothing else.


def test_orphaned_marks_catches_a_mark_glued_to_latin_text() -> None:
    """The exact defect: a kasra stranded on the transliterated word "Aql"."""
    corrupted = "known as Rahat al-Aqlِ, The Peace of the Intellect"
    found = orphaned_marks(corrupted)
    assert len(found) == 1
    assert found[0]["mark"] == "ِ"
    assert "Aql" in found[0]["context"]


def test_strip_orphaned_marks_removes_only_the_stray_mark() -> None:
    """Repair is surgical: the mark goes, every letter around it survives."""
    corrupted = "known as Rahat al-Aqlِ, The Peace of the Intellect"
    cleaned, records = strip_orphaned_marks(corrupted)
    assert cleaned == "known as Rahat al-Aql, The Peace of the Intellect"
    assert len(records) == 1


def test_rejection_reason_refuses_a_candidate_with_a_mark_off_an_arabic_letter() -> None:
    """The admissibility gate itself refuses this shape before it ever reaches
    `book.md` -- the defence-in-depth half of the fix, for whichever future
    caller hands `rejection_reason` a candidate like this directly."""
    reason = rejection_reason("راحة العقل", "Rahat al-Aqlِ")
    assert reason is not None
    assert reason.startswith("a vowel mark")


def test_orphaned_marks_leaves_ordinary_arabic_vowelling_untouched() -> None:
    """Normal Arabic-to-Arabic mark placement must keep working, INCLUDING the
    stacked-mark case (shadda then a vowel, both on one letter) that a naive
    "mark must directly follow a letter" check would misflag as orphaned."""
    fully_vowelled = "فَإِنَّهُ مَنْ عَمِلَ لِلَّهِ"  # إِنَّ stacks hamza+kasra, noon+shadda+fatha
    assert orphaned_marks(fully_vowelled) == []
    cleaned, records = strip_orphaned_marks(fully_vowelled)
    assert cleaned == fully_vowelled
    assert records == []
    assert rejection_reason("فإنه من عمل لله", fully_vowelled) is None


def test_orphaned_marks_empty_and_no_arabic_inputs() -> None:
    """Degenerate inputs never raise and never false-positive."""
    assert orphaned_marks("") == []
    assert orphaned_marks("plain English, no Arabic anywhere") == []
    assert strip_orphaned_marks("") == ("", [])
