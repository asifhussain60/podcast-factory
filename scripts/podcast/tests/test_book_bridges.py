"""Bridges: fixes for a comprehension finding that survive the next compose.

The naive fix — editing book.md directly — is erased by the next compose, which
regenerates that file from source. These tests pin the two properties that make
a durable fix actually durable: idempotent re-injection, and refusal to guess
when an anchor no longer matches the prose.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_bridges import (  # noqa: E402
    BRIDGE_CLOSE,
    BRIDGE_OPEN,
    apply_bridges,
    gate_bridge,
    inject,
    read_bridges,
    sidecar_path,
    strip_bridges,
    write_bridges,
)


def bridge(**kw) -> dict:
    base = {"term": "natiq", "anchor": "we begin with the natiq", "text": "The natiq is the speaking prophet."}
    base.update(kw)
    return base


# ─── the gate ─────────────────────────────────────────────────────────────────
def test_a_well_formed_bridge_passes() -> None:
    ok, reasons = gate_bridge(bridge())
    assert ok, reasons


def test_a_bridge_with_no_anchor_is_rejected() -> None:
    ok, reasons = gate_bridge(bridge(anchor=""))
    assert not ok and "anchor" in reasons[0]


def test_an_essay_length_bridge_is_rejected() -> None:
    ok, reasons = gate_bridge(bridge(text=" ".join(["word"] * 60)))
    assert not ok
    assert "one sentence" in reasons[0]


def test_a_cross_reference_is_rejected_in_favour_of_real_orientation() -> None:
    ok, reasons = gate_bridge(bridge(text="See chapter 6 for the full explanation of the natiq."))
    assert not ok
    assert "orientation" in reasons[0]


# ─── injection and idempotence ────────────────────────────────────────────────
def test_a_bridge_lands_after_the_paragraph_its_anchor_names() -> None:
    md = "## One\n\nWe begin with the natiq here in this opening line.\n\nA second paragraph follows after.\n"

    out, unplaced = inject(md, [bridge(anchor="we begin with the natiq")])

    assert unplaced == []
    assert BRIDGE_OPEN in out and BRIDGE_CLOSE in out
    assert out.index("natiq is the speaking prophet") > out.index("opening line")
    assert out.index("natiq is the speaking prophet") < out.index("second paragraph")


def test_an_anchor_no_longer_in_the_prose_is_reported_not_guessed() -> None:
    md = "## One\n\nThe prose has changed completely since the review ran.\n"

    out, unplaced = inject(md, [bridge(anchor="a phrase that is no longer here")])

    assert len(unplaced) == 1
    assert BRIDGE_OPEN not in out, "an unplaced bridge must not appear anywhere"


def test_re_injecting_the_same_bridges_produces_the_same_output() -> None:
    """Idempotence — a convergence loop re-enters compose many times."""
    md = "## One\n\nWe begin with the natiq here in this opening line.\n"
    once, _ = inject(md, [bridge()])
    twice, _ = inject(once, [bridge()])
    assert once == twice


def test_updating_a_bridges_text_replaces_the_old_one_not_stacks_it() -> None:
    md = "## One\n\nWe begin with the natiq here in this opening line.\n"
    first, _ = inject(md, [bridge(text="The old orienting sentence for this term.")])
    second, _ = inject(first, [bridge(text="The new orienting sentence for this term.")])
    assert "old orienting" not in second
    assert "new orienting" in second
    assert second.count(BRIDGE_OPEN) == 1


def test_strip_bridges_removes_every_fenced_span() -> None:
    md = "## One\n\nprose\n\n" + f"{BRIDGE_OPEN}\n> *note*\n{BRIDGE_CLOSE}\n" + "\nmore prose\n"
    stripped = strip_bridges(md)
    assert BRIDGE_OPEN not in stripped
    assert "prose" in stripped and "more prose" in stripped


def test_an_ungated_bridge_is_not_injected() -> None:
    md = "## One\n\nWe begin with the natiq here.\n"
    out, unplaced = inject(md, [bridge(anchor="")])
    assert BRIDGE_OPEN not in out
    assert len(unplaced) == 1


def test_a_rejected_bridge_still_appears_in_unplaced_for_the_caller_to_see() -> None:
    out, unplaced = inject("## One\n\ntext\n", [bridge(text="")])
    assert unplaced and unplaced[0]["term"] == "natiq"


# ─── the sidecar ──────────────────────────────────────────────────────────────
def test_bridges_round_trip_through_the_sidecar(tmp_path: Path) -> None:
    write_bridges(tmp_path, [bridge()])
    assert read_bridges(tmp_path) == [bridge()]
    assert sidecar_path(tmp_path).exists()


def test_a_missing_sidecar_is_an_empty_list(tmp_path: Path) -> None:
    assert read_bridges(tmp_path) == []


def test_an_unreadable_sidecar_never_raises(tmp_path: Path) -> None:
    sidecar_path(tmp_path).parent.mkdir(parents=True)
    sidecar_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert read_bridges(tmp_path) == []


# ─── the compose-time entry point ────────────────────────────────────────────
def test_apply_bridges_writes_book_md_in_place(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("## One\n\nWe begin with the natiq here in this line.\n", encoding="utf-8")
    write_bridges(bd, [bridge()])

    result = apply_bridges(bd, log=lambda *a: None)

    assert result["applied"] == 1
    assert BRIDGE_OPEN in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_apply_bridges_with_no_stored_bridges_leaves_the_book_untouched(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    original = "## One\n\nprose that must not change.\n"
    (bd / "book" / "book.md").write_text(original, encoding="utf-8")

    result = apply_bridges(bd, log=lambda *a: None)

    assert result == {"applied": 0, "unplaced": []}
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == original


def test_apply_bridges_is_idempotent_across_two_calls(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("## One\n\nWe begin with the natiq here in this line.\n", encoding="utf-8")
    write_bridges(bd, [bridge()])

    apply_bridges(bd, log=lambda *a: None)
    first = (bd / "book" / "book.md").read_text(encoding="utf-8")
    apply_bridges(bd, log=lambda *a: None)
    second = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert first == second


def test_a_missing_book_is_not_an_error(tmp_path: Path) -> None:
    assert apply_bridges(tmp_path, log=lambda *a: None) == {"applied": 0, "unplaced": []}


def test_the_bridge_marker_is_stripped_from_the_rendered_pdf() -> None:
    """The renderer must hide the fence, or a bridge prints as literal <!-- --> text."""
    renderer = (Path(__file__).resolve().parents[3] / "plan-dashboard" / "scripts" / "lib" / "book-html.mjs").read_text(
        encoding="utf-8"
    )
    assert "bridge" in renderer, "book-html.mjs must know to strip bridge:begin/end fences"


def test_sidecar_round_trip_preserves_json_shape(tmp_path: Path) -> None:
    write_bridges(tmp_path, [bridge()])
    raw = json.loads(sidecar_path(tmp_path).read_text(encoding="utf-8"))
    assert raw["schema"] == "book.comprehension-bridges/v1"
    assert raw["bridges"] == [bridge()]
