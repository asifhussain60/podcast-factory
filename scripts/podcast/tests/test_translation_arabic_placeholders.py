"""Inline Arabic spans are protected from the model and restored verbatim."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _translation_chunk as tc  # noqa: E402

SPAN1 = "⟪ar:وَاعْلَمُوا أَنَّمَا⟫"
SPAN2 = "⟪ar:وَابْنِ السَّبِيلِ⟫"


def test_protect_replaces_spans_with_tokens() -> None:
    table: dict[str, str] = {}
    out = tc._protect_spans(f"a {SPAN1} b {SPAN2}", table)
    assert out == "a [[AR1]] b [[AR2]]"
    assert table == {"[[AR1]]": SPAN1, "[[AR2]]": SPAN2}


def test_restore_is_verbatim_and_leaves_unknown_tokens() -> None:
    table = {"[[AR1]]": SPAN1}
    assert tc._restore_spans("x [[AR1]] y [[AR7]]", table) == f"x {SPAN1} y [[AR7]]"


def test_round_trip_is_identity() -> None:
    table: dict[str, str] = {}
    body = f"one {SPAN1} two {SPAN2} three"
    assert tc._restore_spans(tc._protect_spans(body, table), table) == body


def test_hint_only_when_script_dropped() -> None:
    assert tc._token_hint(["speech tag cut"]) == ""
    assert "[[ARn]]" in tc._token_hint(["Arabic script dropped (1 run(s))"])
