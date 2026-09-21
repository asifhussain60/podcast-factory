"""The text layer every corrections script shares: where a quote sits, and how to splice it."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _correction_text import (  # noqa: E402
    block_span,
    block_texts,
    locate_reader,
    locate_source,
    normalize_text,
    plain_text,
    prefix_before,
    read_chapters,
    split_blocks,
    substitute,
)
from correction_test_kit import make_book  # noqa: E402


def test_plain_text_strips_markup_a_reader_never_sees():
    md = "## not here\n**Bold** and *italic* with a [link](http://x) and `code`\n> quoted"
    assert plain_text(md) == "not here Bold and italic with a link and code quoted"


def test_blocks_are_numbered_by_blank_lines_like_the_narration_plan():
    body = "one\n\ntwo <!-- gone -->\n\n\nthree"
    assert split_blocks(body) == ["one", "two ", "three"]  # the comment goes, the space stays: same as chapter_blocks
    assert block_texts(body) == ["one", "two", "three"]


def test_locate_reader_counts_exact_occurrences_and_reports_block_offsets():
    body = "alpha beta gamma\n\ndelta beta epsilon"
    hits = locate_reader(body, "beta")
    assert [(h.block_index, h.start, h.end) for h in hits] == [(0, 6, 10), (1, 6, 10)]
    assert locate_reader(body, "delta beta")[0].block_index == 1
    assert locate_reader(body, "nothing") == []


def test_locate_reader_sees_through_wrapped_lines_and_formatting():
    body = "the neighbour\nwho is **near** and dear"
    assert len(locate_reader(body, "the neighbour who is near")) == 1


def test_locate_source_is_whitespace_flexible_but_not_formatting_flexible():
    body = "the neighbour\nwho is **near** and dear"
    assert locate_source(body, "the neighbour who is") != []
    assert locate_source(body, "who is near") == []  # spans the bold markers: cannot splice


def test_locate_source_never_matches_across_a_paragraph_break():
    assert locate_source("end of one.\n\nstart of two", "one. start") == []


def test_substitute_applies_last_position_first_so_offsets_stay_valid():
    text = "aaa bbb ccc"
    assert substitute(text, [(0, 3, "X"), (8, 11, "LONGER")]) == "X bbb LONGER"


def test_block_span_finds_the_paragraph():
    body = "first\n\nsecond one\n\nthird"
    s = body.index("second")
    assert body[slice(*block_span(body, s, s + 3))] == "second one"


def test_prefix_is_the_text_before_the_quote_capped_at_48():
    text = "x" * 100 + "QUOTE"
    assert prefix_before(text, 100) == "x" * 48
    assert prefix_before("abc QUOTE", 4) == "abc "


def test_read_chapters_uses_the_composer_key_and_printed_number(tmp_path):
    book = make_book(tmp_path)
    chs = read_chapters(book)
    assert [(c.key, c.number, c.heading) for c in chs] == [
        ("first chapter", 1, "1. First Chapter"),
        ("second chapter", 2, "2. Second Chapter"),
    ]
    assert normalize_text(" a \n b ") == "a b"
