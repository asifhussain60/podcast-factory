"""Mirroring the English paragraphing onto the Arabic's.

Asif, 2026-07-30: the source prints `قال الغلام: …` as one paragraph and the
edition printed "The boy said:" on a line of its own. A translation edition does
not get to choose its own paragraphing, so consecutive English paragraphs from one
Arabic paragraph are merged back into one.

Most of what follows guards the ways a merge could quietly damage the text.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_mirror import (  # noqa: E402
    inside_quotation,
    join_blocks,
    mirror_chapter,
    raw_blocks,
)
from _para_blocks import para_fingerprint  # noqa: E402


def pair(block: str, *src: int, confidence: str = "verified") -> dict:
    return {"fp": para_fingerprint(block), "source_paras": list(src), "confidence": confidence}


def test_a_speech_tag_joins_the_speech_it_introduces() -> None:
    tag = "The boy said:"
    speech = '"The thought that I may have no excuse frightens me."'
    body = f"{tag}\n\n{speech}\n"
    out = mirror_chapter(body, [pair(tag, 30), pair(speech, 30)])
    assert out is not None
    text, pairs = out
    assert text.strip() == f"{tag} {speech}"
    assert len(pairs) == 1
    assert pairs[0]["source_paras"] == [30]
    assert pairs[0]["fp"] == para_fingerprint(text.strip())


def test_a_continued_speech_loses_its_reopening_quote() -> None:
    """English reopens a quote each paragraph and closes only the last one.

    Merged naively that leaves an orphan quotation mark in mid-sentence.
    """
    a = '"God did not create people as scholars.'
    b = '"In the same way, deeper knowledge cannot be received first."'
    assert join_blocks([a, b]) == (
        '"God did not create people as scholars. In the same way, deeper knowledge cannot be received first."'
    )


def test_a_quote_that_opens_a_new_speech_is_kept() -> None:
    """Only a CONTINUATION mark is dropped — a fresh quotation keeps its own."""
    a = "The narrator continued."
    b = '"A new thing is said here."'
    assert join_blocks([a, b]) == 'The narrator continued. "A new thing is said here."'


def test_quotation_state_reads_both_quote_styles() -> None:
    assert inside_quotation('He said "one')
    assert not inside_quotation('He said "one"')
    assert inside_quotation("He said “one")
    assert not inside_quotation("He said “one”")


def test_paragraphs_from_different_sources_are_left_apart() -> None:
    a, b = "First paragraph here.", "Second paragraph here."
    out = mirror_chapter(f"{a}\n\n{b}\n", [pair(a, 4), pair(b, 5)])
    assert out is not None
    text, pairs = out
    assert text.strip() == f"{a}\n\n{b}"
    assert len(pairs) == 2


def test_a_blockquote_between_them_stops_the_run() -> None:
    """A verse between two paragraphs of one source must not be merged across."""
    a, b = "Before the verse.", "After the verse."
    body = f"{a}\n\n> a quoted verse\n\n{b}\n"
    out = mirror_chapter(body, [pair(a, 7), pair(b, 7)])
    assert out is not None
    text, pairs = out
    assert "> a quoted verse" in text
    assert text.index(a) < text.index("> a quoted verse") < text.index(b)
    assert len(pairs) == 2  # two runs, both pointing at ¶7


def test_a_stale_alignment_merges_nothing() -> None:
    """The alignment naming paragraphs this chapter no longer has is the one case
    where merging could join two unrelated passages. It refuses outright."""
    a, b = "First paragraph here.", "Second paragraph here."
    stale = [pair("something the chapter no longer says", 4), pair(b, 4)]
    assert mirror_chapter(f"{a}\n\n{b}\n", stale) is None


def test_a_length_disagreement_merges_nothing() -> None:
    a = "Only one paragraph."
    assert mirror_chapter(f"{a}\n", [pair(a, 1), pair("ghost", 2)]) is None


def test_bracketed_confidence_wins_over_verified_in_a_merge() -> None:
    """A merged paragraph is only as certain as its least certain part."""
    a, b = "Certain part here.", "Uncertain part here."
    out = mirror_chapter(f"{a}\n\n{b}\n", [pair(a, 9), pair(b, 9, confidence="bracketed")])
    assert out is not None
    _text, pairs = out
    assert pairs[0]["confidence"] == "bracketed"


def test_headings_and_figures_survive_untouched() -> None:
    a, b = "Opening paragraph.", "Closing paragraph."
    body = f"## A heading\n\n{a}\n\n{b}\n"
    out = mirror_chapter(body, [pair(a, 2), pair(b, 2)])
    assert out is not None
    text, _pairs = out
    assert text.startswith("## A heading")
    assert len(raw_blocks(text)) == 2  # the heading, and one merged paragraph
