"""Mirroring the English paragraphing onto the Arabic's.

Asif, 2026-07-30: the source prints `قال الغلام: …` as one paragraph and the
edition printed "The boy said:" on a line of its own. A translation edition does
not get to choose its own paragraphing, so consecutive English paragraphs from one
Arabic paragraph are merged back into one.

Most of what follows guards the ways a merge could quietly damage the text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_mirror import (  # noqa: E402
    inside_quotation,
    is_arabic_block,
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


def test_a_lone_speech_tag_adopts_the_source_of_the_speech_it_opens() -> None:
    """`قال الغلام:` opens an Arabic paragraph; it is never one on its own.

    The aligner sometimes pairs the English tag with a span straddling two source
    paragraphs while the speech is pinned to one, and two signatures never group.
    """
    tag, speech = "The boy said:", '"You have dealt fairly with me."'
    out = mirror_chapter(
        f"{tag}\n\n{speech}\n",
        [pair(tag, 33, 34), pair(speech, 34)],
    )
    assert out is not None
    text, pairs = out
    assert text.strip() == f"{tag} {speech}"
    assert pairs[0]["source_paras"] == [34]


def test_a_tag_above_a_displayed_verse_stays_where_it_is() -> None:
    """It introduces a BLOCK quotation, which is exactly where a tag belongs."""
    tag = "The boy said:"
    body = f'{tag}\n\n> لا حول ولا قوة إلا بالله\n\n"There is no might except by God."\n'
    rendering = '"There is no might except by God."'
    out = mirror_chapter(body, [pair(tag, 170), pair(rendering, 170)])
    assert out is not None
    text, pairs = out
    assert text.index(tag) < text.index(">") < text.index(rendering)
    assert len(pairs) == 2


def test_an_arabic_quotation_is_never_absorbed_into_the_english() -> None:
    """The regression Asif caught in the printed PDF (2026-07-30).

    The first mirror pass called any block without a `>`/`#`/`<` prose, so all 39 of
    this book's standalone Arabic quotations were merged into the English on either
    side and the script ran on inside a Latin paragraph, wrapping mid-sentence.
    """
    english = "So the first of creation was a will, then a command, then a saying."
    arabic = "فَابْتَدَأَ خَلْقَ مَا خَلَقَ مِنْ نُورٍ تَفَرَّعَ مِنْهُ ثَلَاثُ كَلِمَاتٍ."
    after = "He began the creation of what He created out of a light."
    out = mirror_chapter(
        f"{english}\n\n{arabic}\n\n{after}\n",
        [pair(english, 12), pair(arabic, 12), pair(after, 12)],
    )
    assert out is not None
    text, pairs = out
    # Three blocks in, three blocks out — all one source paragraph, none merged.
    assert len(raw_blocks(text)) == 3
    assert len(pairs) == 3
    assert arabic in text.split("\n\n")[1]


def test_english_carrying_a_glossary_term_still_merges() -> None:
    """A term woven into a sentence is English, and must not stop a run."""
    a = "The bab (بَاب) is the gate through which the teaching passes to the seeker."
    b = "It is named so because nothing reaches the disciple except through it."
    out = mirror_chapter(f"{a}\n\n{b}\n", [pair(a, 5), pair(b, 5)])
    assert out is not None
    text, pairs = out
    assert len(pairs) == 1
    assert len(raw_blocks(text)) == 1


def test_is_arabic_block_separates_a_quotation_from_a_glossed_sentence() -> None:
    assert is_arabic_block("فَابْتَدَأَ خَلْقَ مَا خَلَقَ مِنْ نُورٍ تَفَرَّعَ مِنْهُ ثَلَاثُ كَلِمَاتٍ.")
    assert not is_arabic_block("The bab (بَاب) is the gate through which teaching passes.")
    assert not is_arabic_block("Plain English with no Arabic in it at all.")


def test_is_arabic_block_matches_the_shared_fixtures() -> None:
    """The Python third of a three-way mirror.

    The same question is answered by ``isArabicOnlyParagraph`` in
    ``plan-dashboard/scripts/lib/book-html.mjs`` (the PDF and the Composer's Read
    view) and again in ``src/lib/reader/markdown.ts`` (the reader, which is
    client-bundled and cannot import the Node-only module). All three read THIS
    fixture file, because drift between them is silent: one surface centers a
    paragraph as a display quotation while another sets it as running prose, and
    on this side the paragraph merge absorbs a quotation into the English beside
    it instead of leaving it standing alone.
    """
    fixtures = json.loads(
        (REPO / "plan-dashboard" / "scripts" / "lib" / "arabic-block.fixtures.json").read_text(encoding="utf-8")
    )
    cases = fixtures["cases"]
    assert cases, "fixture file is empty"
    # Guard the guard: an all-true fixture set passes against a constant function.
    assert any(c["out"] for c in cases) and any(not c["out"] for c in cases)
    for case in cases:
        assert is_arabic_block(case["in"]) is case["out"], case["why"]
