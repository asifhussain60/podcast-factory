"""test_align_paragraphs.py — the properties the Arabic reveal depends on.

The alignment decides which Arabic paragraph is shown above which English one, so
a defect here does not show LESS Arabic — it shows the WRONG Arabic, confidently.
The three properties that make it trustworthy are pinned below: the path never runs
backwards, a known anchor is honoured absolutely, and a paragraph with no evidence
of its own is carried rather than parked somewhere arbitrary.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _align_paragraphs import SELF_SUPPORT, align, bracket, is_monotonic  # noqa: E402
from _arabic_paragraphs import MERGED_INTO, join, parse_blocks  # noqa: E402

SOURCE = [
    "The scholar spoke about the limits of knowledge and the outward meaning.",
    "The boy asked about the gate and the covenant between them.",
    "They travelled through the desert toward the city at dawn.",
    "The father raged against religion and its adherents everywhere.",
]


def test_a_one_to_one_translation_aligns_in_order() -> None:
    composed = [
        "The scholar discussed the limits of knowledge, and the outward meaning.",
        "The boy enquired about the gate, and about the covenant between them.",
        "They journeyed across the desert towards the city as dawn broke.",
        "The father raged against religion and against its adherents.",
    ]
    out = align(SOURCE, composed)
    assert [a.source_index for a in out] == [0, 1, 2, 3]
    assert is_monotonic(out)


def test_one_source_paragraph_split_into_several_shares_it() -> None:
    """The case that broke the first attempt: articulation splits a block into
    short turns, and a turn like `The Master replied:` has nothing to match on."""
    composed = [
        "The scholar discussed the limits of knowledge.",
        "He replied:",
        "And he spoke of the outward meaning.",
        "The boy enquired about the gate and the covenant.",
    ]
    out = align(SOURCE, composed)
    assert is_monotonic(out)
    assert out[0].source_index == 0
    assert out[1].source_index == 0, "an evidence-free turn stays with its neighbour"
    assert out[3].source_index == 1


def test_the_path_never_runs_backwards() -> None:
    """Monotonicity is what makes a bracket meaningful. Without it a 'span between
    two confident neighbours' would not bound anything."""
    composed = [
        "desert city dawn journeyed",  # looks like source 2
        "scholar limits knowledge outward",  # looks like source 0 — must NOT go back
        "father raged religion adherents",
    ]
    out = align(SOURCE, composed)
    assert is_monotonic(out)


def test_an_anchor_is_absolute() -> None:
    """A shared quotation is knowledge, not evidence to be weighed: the path is
    forced through it even when the vocabulary argues elsewhere."""
    composed = [
        "scholar limits knowledge outward meaning",
        "scholar limits knowledge outward meaning",  # reads like source 0 …
    ]
    free = align(SOURCE, composed)
    assert free[1].source_index == 0
    forced = align(SOURCE, composed, anchors={1: 3})  # … but is known to be source 3
    assert forced[1].source_index == 3
    assert forced[1].anchored is True
    assert is_monotonic(forced)


def test_bracket_bounds_a_thin_paragraph_by_its_confident_neighbours() -> None:
    composed = [
        "The scholar discussed the limits of knowledge and outward meaning.",
        "He replied:",
        "The father raged against religion and its adherents everywhere.",
    ]
    out = align(SOURCE, composed)
    assert out[1].score < SELF_SUPPORT, "the middle turn has no evidence of its own"
    lo, hi = bracket(out, 1)
    assert lo <= out[1].source_index <= hi
    assert lo == out[0].source_index and hi == out[2].source_index


def test_empty_inputs_are_not_an_error() -> None:
    assert align([], ["x"]) == []
    assert align(["x"], []) == []
    assert is_monotonic([]) is True


# ── The Arabic side ────────────────────────────────────────────────────────


ARABIC = "\n".join(
    [
        "(١) اَلْفَقْرَةُ الْأُولَى هُنَا",
        "تَتِمَّةُ الْفَقْرَةِ الْأُولَى",
        "<!-- page 2 -->",
        "(٢) اَلْفَقْرَةُ الثَّانِيَة",
        "(٣) اَلْفَقْرَةُ الثَّالِثَة",
    ]
)


def test_arabic_blocks_run_from_marker_to_marker_and_drop_page_furniture() -> None:
    blocks = parse_blocks(ARABIC)
    assert sorted(blocks) == [1, 2, 3]
    assert "تَتِمَّة" in blocks[1].text, "a continuation line belongs to its paragraph"
    assert "page" not in blocks[1].text, "page markers are scan furniture, not text"


def test_a_footnote_digit_is_not_a_paragraph_marker() -> None:
    """Footnote references in this scan are bare digits welded to a letter. Only a
    parenthesised number at column 0 opens a paragraph; anything looser would shred
    the text at every footnote."""
    text = "(١) قَالَ الْعَالِمُ٢ لِلْغُلَامِ٣ كَلَامًا"
    blocks = parse_blocks(text)
    assert sorted(blocks) == [1]
    stripped = parse_blocks(text, strip_footnote_refs=True)
    assert "٢" not in stripped[1].text and "٣" not in stripped[1].text
    assert "قَالَ" in stripped[1].text, "stripping a reference must not touch the words"


def test_the_lost_paragraph_number_points_at_its_host_and_says_so() -> None:
    """¶511's marker was mangled by the OCR and its text sits inside 510. Asking
    for it returns 510 flagged `merged` — never a guessed split."""
    missing, host = next(iter(MERGED_INTO.items()))
    blocks = parse_blocks(f"({''.join(chr(0x660 + int(d)) for d in str(host))}) نَصٌّ طَوِيلٌ هُنَا")
    assert blocks[missing].merged is True
    assert blocks[missing].text == blocks[host].text
    assert join(blocks, [host, missing]) == blocks[host].text, "the block prints once, not twice"
