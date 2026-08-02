"""A machine fence is recognised in BOTH the forms it occurs in on disk.

The pipeline writes ``<!-- editorial:begin -->``. The Composer's editor cannot
carry an HTML comment through a round-trip and serializes it back as a bare
``editorial:begin`` line. Every fence consumer in the pipeline used to match only
the comment form, which does not fail loudly — it silently reclassifies a
machine-authored aside as the book's own prose.

That is the-master-and-the-disciple chapter 3, July 2026: an articulation pass
could not see the span, rewrote the editorial note into the narrator's paragraph,
and the next ``0book-augment`` could not see it either, so it appended a second
copy instead of replacing the first. The chapter printed the same note twice.

The two regression tests at the bottom are that bug, in gate form.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_augment import _BLOCK_CLOSE, _BLOCK_OPEN, insert_blocks
from _book_fences import count_markers, find_spans, span_re, strip_spans
from _book_voice import _EDITORIAL_SPAN_RE

COMMENT = f"{_BLOCK_OPEN}\n> **Editorial note.** Body prose.\n{_BLOCK_CLOSE}"
BARE = "editorial:begin\n> **Editorial note.** Body prose.\neditorial:end"


def test_the_comment_form_the_pipeline_writes_is_matched() -> None:
    assert find_spans(COMMENT, "editorial") == [COMMENT]
    assert strip_spans(f"Prose.\n\n{COMMENT}\n\nMore.", "editorial") == "Prose.\n\n\n\nMore."


def test_the_bare_form_a_composer_round_trip_leaves_is_matched() -> None:
    """The regression's root cause: this used to return nothing at all."""
    assert find_spans(BARE, "editorial") == [BARE]
    assert "Body prose" not in strip_spans(BARE, "editorial")


def test_a_half_flattened_span_is_still_one_span() -> None:
    """An editor can flatten one marker and not the other — a real save shape."""
    mixed = f"{_BLOCK_OPEN}\n> aside\neditorial:end"
    assert find_spans(mixed, "editorial") == [mixed]


def test_a_marker_named_inside_a_sentence_is_prose() -> None:
    """The bare alternative is anchored to a whole line, exactly as `markerOf`
    in book-fences.ts matches only a trimmed full line. Otherwise a chapter that
    DISCUSSES the fence format would have its prose eaten."""
    prose = "The pipeline writes an editorial:begin marker before each aside.\n"
    assert find_spans(prose, "editorial") == []
    assert strip_spans(prose, "editorial") == prose
    assert count_markers(prose, "editorial", "begin") == 0


def test_a_quoted_marker_line_is_prose_too() -> None:
    """`> editorial:begin` is a blockquote of the marker, not the marker."""
    assert find_spans("> editorial:begin\n> x\n> editorial:end", "editorial") == []


def test_two_spans_of_one_kind_do_not_collapse_into_one() -> None:
    """Non-greedy between the markers — a greedy match would swallow the prose
    BETWEEN two asides and delete a paragraph of the book on strip."""
    doc = f"{COMMENT}\n\nkeep me\n\n{COMMENT}"
    assert len(find_spans(doc, "editorial")) == 2
    assert "keep me" in strip_spans(doc, "editorial")


def test_kinds_do_not_match_each_other() -> None:
    assert find_spans(COMMENT, "bridge") == []
    assert find_spans("<!-- bridge:begin -->\nx\n<!-- bridge:end -->", "editorial") == []


def test_leading_and_trailing_fragments_are_honoured() -> None:
    """Callers that consume surrounding blank lines keep doing so."""
    doc = f"A.\n\n{COMMENT}\n\nB."
    assert strip_spans(doc, "editorial", leading=r"\n*", trailing=r"\n*") == "A.B."


def test_markers_are_counted_in_either_form() -> None:
    assert count_markers(f"{COMMENT}\n{BARE}", "editorial", "begin") == 2
    assert count_markers(f"{COMMENT}\n{BARE}", "editorial", "end") == 2


def test_span_re_is_reusable_across_calls() -> None:
    """It is cached on (kind, leading, trailing); a cached compiled pattern must
    not carry match state between callers."""
    r = span_re("editorial")
    assert r is span_re("editorial")
    assert len(r.findall(COMMENT)) == 1
    assert len(r.findall(COMMENT)) == 1


# ─── The July 2026 duplicate, in gate form ──────────────────────────────────


def test_augment_replaces_a_bare_marked_prior_block_instead_of_stacking() -> None:
    """`insert_blocks` is idempotent only if it can FIND the block it wrote last
    time. Against a bare-marked prior block it used to find nothing and append a
    second aside beside the first."""
    book = f"# B\n\n## 1. One\n\nbody\n\n{BARE}\n"
    out = insert_blocks(book, {1: COMMENT})
    assert out.count("Body prose") == 1, "the prior aside was stacked, not replaced"
    assert "editorial:begin\n" not in out.replace(_BLOCK_OPEN, "")


def test_the_voice_pass_hides_a_bare_marked_aside_from_the_model() -> None:
    """`apply_fluency_adapt` sends `base_prose` to the model and re-appends the
    asides verbatim. A bare-marked aside used to fall into `base_prose` — which is
    how an editorial note came back wearing the narrator's voice."""
    body = f"Narrative paragraph.\n\n{BARE}\n"
    assert _EDITORIAL_SPAN_RE.findall(body), "aside invisible to the re-voice guard"
    base_prose = _EDITORIAL_SPAN_RE.sub("", body).strip()
    assert base_prose == "Narrative paragraph."
