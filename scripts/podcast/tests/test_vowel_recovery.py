"""Salvaging a refused vowelling instead of losing the whole run.

The defect these pin, found 2026-07-30: `rejection_reason` is all-or-nothing per RUN,
so one disputed letter cost the marks on everything around it — 94 refusals in the
first real source pass, 92 of them over a single character, each leaving a bare hole
in the middle of an otherwise-marked paragraph. The recovery re-asks the run in
pieces under the SAME gate. These tests exist to prove it cannot become a way to
admit anything the gate would refuse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _vowel_recovery import askable, assemble, plan, recover, segment_answer, segments  # noqa: E402
from _vowelling import rejection_reason, skeleton  # noqa: E402

# The real passage that surfaced this. The scan reads `ويرثله`; the model answered
# `ويرتله` — almost certainly the right word, `يُرَتِّلُهُ`, but a changed letter, so
# the gate refused and ~120 characters of good vowelling went with it.
REFUSED_RUN = (
    "فأقبل العالم يتلو العهد على الغلام ويرثله ويعقده عليه، "
    "والغلام لا يملك نفسه جزعاً. ودموعه تنحدر من شدة العبرة، حتى بلغ به آخر العهد."
)


@pytest.mark.parametrize(
    "sample",
    [
        "",
        "قال",
        REFUSED_RUN,
        "لا فواصل هنا ولا نقاط",
        "جملة. جملة أخرى؛ وثالثة، ورابعة؟ وخامسة!",
        "  مسافات   قبل وبعد.  ",
    ],
)
def test_the_cut_loses_nothing(sample: str) -> None:
    """Rejoining the segments must reproduce the run byte for byte.

    This is the property the whole assembly rests on: a segment left un-vowelled
    contributes its SOURCE bytes, so the skeleton of the whole cannot move.
    """
    assert "".join(segments(sample)) == sample


def test_a_run_with_no_boundary_offers_no_plan() -> None:
    assert plan("لا فواصل") is None


def test_the_real_refused_run_splits_into_askable_pieces() -> None:
    parts = plan(REFUSED_RUN)
    assert parts is not None
    assert len(parts) > 1
    assert sum(1 for p in parts if askable(p)) >= 2


def test_assembly_keeps_the_source_where_a_piece_failed() -> None:
    """An un-answered piece contributes its own text, and the result still gates."""
    parts = plan(REFUSED_RUN)
    assert parts is not None
    # Answer nothing at all: the run must come back unchanged, not mangled.
    text, still_bare = assemble(REFUSED_RUN, parts, {})
    assert text == REFUSED_RUN
    assert still_bare  # and it reports what is bare


def test_assembly_admits_marks_only() -> None:
    """A piece answered with real marks is kept; the whole still passes the gate."""
    parts = plan(REFUSED_RUN)
    assert parts is not None
    marked = {i: p.replace("ا", "اَ") for i, p in enumerate(parts) if askable(p)}
    # The stand-in above only ADDS a fatha, so each piece is admissible on its own.
    for i, p in list(marked.items()):
        if rejection_reason(parts[i], p):
            del marked[i]
    assert marked, "the fixture must produce at least one admissible piece"
    text, _bare = assemble(REFUSED_RUN, parts, marked)
    assert text != REFUSED_RUN
    assert rejection_reason(REFUSED_RUN, text) is None
    assert skeleton(text) == skeleton(REFUSED_RUN)


def test_assembly_fails_closed_when_a_piece_moved_a_letter() -> None:
    """The one thing this must never do: let a letter change in through the side door.

    `assemble` re-checks its own output against the unmodified gate, so a piece that
    somehow carried a letter change discards the whole salvage rather than writing it.
    """
    parts = plan(REFUSED_RUN)
    assert parts is not None
    i = next(i for i, p in enumerate(parts) if askable(p))
    text, still_bare = assemble(REFUSED_RUN, parts, {i: parts[i].replace("ث", "ت")})
    assert text == REFUSED_RUN
    assert still_bare == [REFUSED_RUN.strip()]


def test_segment_answer_gates_each_piece() -> None:
    piece = "والغلام لا يملك نفسه جزعاً."
    assert segment_answer(piece, piece.replace("ا", "اَ")) is not None
    # A changed letter in the piece is refused exactly as it would be in a run.
    assert segment_answer(piece, piece.replace("غ", "ع")) is None


def test_recover_returns_none_when_every_piece_is_refused() -> None:
    """No marks recovered means no claim made — the caller keeps the original refusal."""
    assert recover(REFUSED_RUN, ask=lambda part: part.replace("ل", "ن")) is None


def test_recover_marks_what_it_can() -> None:
    out = recover(REFUSED_RUN, ask=lambda part: part.replace("ا", "اَ"))
    assert out is not None
    text, _bare = out
    assert text != REFUSED_RUN
    assert rejection_reason(REFUSED_RUN, text) is None
