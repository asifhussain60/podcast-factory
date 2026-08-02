"""Tests for _book_quran — canonical Arabic for cited Qur'anic verses.

The properties worth pinning are the ones whose failure is silent and expensive:
a citation shape that stops matching, an extent claimed on too little evidence, a
second run doubling the Arabic, and — above all — a wrong verse reaching the page
because one signal was trusted on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_citations import CITE_RE  # noqa: E402
from _book_quran import _block_start, inject_text  # noqa: E402
from _book_quran_extent import (  # noqa: E402
    _align,
    _arabic_ratio,
    ornate_spans,
    valid_reference,
)


# ── Citation parsing ──────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text,expected",
    [
        ('... of what We reminded them of." (5:13)', [("5", "13", None)]),
        ('"..." (Quran 21:98)', [("21", "98", None)]),
        ('"..." (Quran, 35: 45)', [("35", "45", None)]),
        ('"..." (Qur\'an 2:255)', [("2", "255", None)]),
        ('"..." (Q 53:39)', [("53", "39", None)]),
        ('"..." (Quran 14:24-26)', [("14", "24", "26")]),
        ('"..." (Quran 16:68–69)', [("16", "68", "69")]),  # en dash
    ],
)
def test_citation_shapes_this_corpus_uses(text, expected):
    assert [m.groups() for m in CITE_RE.finditer(text)] == expected


@pytest.mark.parametrize(
    "text",
    [
        "Q1.20 revenue was flat",  # fiscal quarter
        "a 3:2 ratio of oil to vinegar",  # bare ratio, no parens
        "the meeting ran 12:30 to 13:45",
        "pages 12:14 of the manuscript",
    ],
)
def test_non_citations_are_refused(text):
    """The whole risk of accepting a bare `(N:M)` is what else looks like one."""
    assert not CITE_RE.search(text)


def test_reference_range_validation():
    assert valid_reference(2, 282)
    assert valid_reference(114, 6)
    assert not valid_reference(2, 287)  # al-Baqara has 286
    assert not valid_reference(115, 1)
    assert not valid_reference(0, 1)


# ── The scan ──────────────────────────────────────────────────────────────────
def test_ornate_spans_survive_an_unbalanced_bracket():
    """This book's scan has 45 opens against 44 closes; a naive split loses the lot."""
    text = "prose ﴿ الْحَمْدُ لِلَّهِ ﴾ more ﴿ رَبِّ الْعَلَمِينَ ﴾ tail ﴿ never closed"
    spans = ornate_spans(text)
    assert spans == ["الْحَمْدُ لِلَّهِ", "رَبِّ الْعَلَمِينَ"]


def test_arabic_ratio_separates_a_verse_from_an_inline_honorific():
    """The idempotency guard turns on this distinction."""
    verse = "إِنَّمَا ٱلنَّسِىٓءُ زِيَادَةٌۭ فِى ٱلْكُفْرِ"
    prose = "Many works composed by the elders affirm the imams (عَلَيْهِمُ السَّلَامُ) plainly."
    assert _arabic_ratio(verse) >= 0.6
    assert _arabic_ratio(prose) < 0.6


# ── Alignment ─────────────────────────────────────────────────────────────────
def test_align_prefers_the_occurrence_its_neighbours_agree_with():
    """A repeated word must not drag the window back to its first occurrence.

    This is the Q 2:282 failure in miniature: `wa` appears early and again inside
    the quoted clause, and resolving it in isolation stretched a 12-word extent
    into a claimed 98-word one.
    """
    ayah = ["wa", "alif", "ba", "jim", "dal", "ha", "wa", "zay", "ha"]
    quoted = ["jim", "dal", "ha", "wa", "zay"]
    lo, hi, n, precision = _align(quoted, ayah)
    assert (lo, hi) == (3, 8)
    assert n == 5
    assert precision == 1.0


def test_align_breaks_the_chain_at_a_large_jump():
    """One coincidence far from the quotation must not set the extent's start.

    Tokens are deliberately dissimilar words rather than `w1..w29`: a numbered
    series fuzzy-matches itself (`w20` against `w2` scores 0.8) and would test the
    similarity function instead of the segmentation.
    """
    filler = [
        "alpha",
        "bravo",
        "cobalt",
        "dinghy",
        "ember",
        "fjord",
        "gasket",
        "hubcap",
        "ingot",
        "jonquil",
        "kelpie",
        "lentil",
        "mizzen",
        "nutmeg",
        "oxbow",
        "pylon",
        "quartz",
        "rhubarb",
        "sextant",
        "tundra",
        "umlaut",
        "vellum",
        "wicket",
        "xenon",
        "yarrow",
        "zephyr",
    ]
    ayah = ["stray"] + filler
    quoted = ["stray", "umlaut", "vellum", "wicket", "xenon"]
    lo, hi, n, _ = _align(quoted, ayah)
    assert lo == ayah.index("umlaut")  # not 0 — the lone `stray` is its own segment
    assert (hi, n) == (ayah.index("xenon") + 1, 4)


# ── Insertion ─────────────────────────────────────────────────────────────────
VERSE = "إِنَّمَا ٱلنَّسِىٓءُ زِيَادَةٌۭ فِى ٱلْكُفْرِ"
SPAN = "إِنَّمَا النَّسِىءُ زِيَادَةً فِى الْكُفْرِ"  # the same clause, OCR-damaged


def test_inserts_canonical_arabic_above_the_quotation():
    text = 'Then He said:\n\n"Forgetfulness is only an excess of disbelief." (9:37)\n'
    out, stats = inject_text(text, [SPAN])
    assert stats["inserted"] == 1
    lines = out.split("\n")
    i = next(i for i, l in enumerate(lines) if "(9:37)" in l)
    # `> arabic`, blank, then the quotation exactly as the author wrote it.
    assert lines[i - 2].startswith("> ")
    assert _arabic_ratio(lines[i - 2]) >= 0.6
    assert lines[i - 1] == ""
    assert lines[i] == '"Forgetfulness is only an excess of disbelief." (9:37)'


def test_letters_come_from_the_mushaf_not_the_scan():
    """The OCR chooses the extent; it must never supply a glyph.

    Asserted on ALEF WASLA (U+0671), which the Uthmani orthography uses and the
    scan's plain-alef spelling does not — a character-level discriminator rather
    than a whole-word literal, since two identical-looking Arabic words can differ
    in combining-mark order.
    """
    text = '"..." (9:37)\n'
    out, _ = inject_text(text, [SPAN])
    inserted = [l for l in out.split("\n") if l.startswith("> ")][0]
    assert SPAN not in inserted
    assert "ٱ" in inserted  # Uthmani alef wasla
    assert "ٱ" not in SPAN  # which the scan never had


def test_second_run_changes_nothing():
    text = '"..." (9:37)\n'
    once, _ = inject_text(text, [SPAN])
    twice, stats = inject_text(once, [SPAN])
    assert twice == once
    assert stats["inserted"] == 0
    assert stats["already"] == 1


def test_no_english_word_is_touched():
    import re

    text = 'He said:\n\n"Forgetfulness is only an excess of disbelief." (9:37)\n\nAnd so on.\n'
    out, _ = inject_text(text, [SPAN])
    words = lambda t: re.findall(r"[A-Za-z\']+", t)  # noqa: E731
    assert words(out) == words(text)


def test_a_verse_the_scan_lacks_is_reported_not_invented():
    """The rejected fallback: no extent means no Arabic, never a whole ayah."""
    text = '"..." (9:37)\n'
    out, stats = inject_text(text, [])  # empty scan
    assert out == text
    assert stats["inserted"] == 0
    assert [u["ref"] for u in stats["uncovered"]] == ["9:37"]


def test_arabic_goes_above_the_whole_blockquote_not_between_its_lines():
    """A citation on a continuation line must not split the quote it belongs to."""
    text = "> Forgetfulness is only an excess of disbelief\n> (9:37)\n"
    out, stats = inject_text(text, [SPAN])
    assert stats["inserted"] == 1
    lines = [l for l in out.split("\n") if l.strip()]
    assert _arabic_ratio(lines[0]) >= 0.6  # Arabic first
    assert lines[1].endswith("disbelief")  # then the quote, still intact
    assert lines[2] == "> (9:37)"  # and its citation still attached


def test_block_start_walks_only_blockquotes():
    lines = ["para", "", "> one", "> two", "> (9:37)", "", "para"]
    assert _block_start(lines, 4) == 2
    assert _block_start(lines, 0) == 0
    assert _block_start(lines, 6) == 6


# ── The two-signal rule for unlabelled passages ───────────────────────────────
def test_uncited_passage_is_written_only_on_agreement():
    """One signal proposes; it takes two to write.

    The finding carries `agreed`, and `inject_text` acts on the agreed list its
    caller hands it. What is pinned here is that an entry the reviewer did NOT
    agree cannot reach the page just by being present in the review.
    """
    text = "Some passage with no reference at all.\n"
    agreed = [{"proposed_ref": "9:37", "line": 1, "agreed": True, "english_similarity": 0.4}]
    out, stats = inject_text(text, [SPAN], uncited=agreed)
    assert stats["inserted"] == 1
    assert stats["inserted_detail"][0]["via"] == "uncited-agreed"

    # Same passage, same verse, but the scan never corroborated it: the caller
    # filters on `agreed`, so nothing is passed and nothing is written.
    out2, stats2 = inject_text(text, [SPAN], uncited=[])
    assert out2 == text
    assert stats2["inserted"] == 0


def test_a_cited_verse_wins_the_insertion_point_over_an_inference():
    text = '"..." (9:37)\n'
    guess = [{"proposed_ref": "2:255", "line": 1, "agreed": True}]
    out, stats = inject_text(text, [SPAN], uncited=guess)
    assert stats["inserted"] == 1
    assert stats["inserted_detail"][0]["via"] == "cited"
