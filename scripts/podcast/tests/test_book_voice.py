"""0book-voice — the author-companion re-voice pass's deterministic gates.

These tests pin the fidelity gates a re-voiced chapter must survive before it
replaces the faithful base, above all the narrative-opening gate: a chapter must
begin as a chapter, not with the narrator announcing the act of narration.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_voice import narrative_opening_findings, revoice_gates  # noqa: E402


# ─── the reported bug, verbatim ──────────────────────────────────────────────
def test_the_reported_sentence_trips_the_gate() -> None:
    """Found live 2026-07-19 on the-master-and-the-disciple, chapter opening."""
    text = (
        "Let me set down, as faithfully as I can, how my Master opened the "
        "matter — the first of the causes of the manifest order, and how its "
        "creation began."
    )
    assert narrative_opening_findings(text)


# ─── other real instances found across the corpus ────────────────────────────
def test_let_me_tell_you_how_trips_the_gate() -> None:
    text = "Let me tell you how a certain conversation reached us, because everything about the way you read it depends on hearing it the way it was first spoken."
    assert narrative_opening_findings(text)


def test_i_want_to_tell_you_trips_the_gate() -> None:
    text = "I want to tell you what happened next, because everything that follows in this book turns on it."
    assert narrative_opening_findings(text)


def test_before_i_set_down_trips_the_gate() -> None:
    text = "Before I set down a single word of what follows, let me speak the words I have always begun with, for they are not ornament but the doorway itself."
    assert narrative_opening_findings(text)


def test_i_held_this_book_back_trips_the_gate() -> None:
    text = "I held this book back from the press for a long time, and I want to tell you why before I tell you anything else."
    assert narrative_opening_findings(text)


# ─── the voice is intentionally first-person and warm — don't over-match ─────
def test_a_chapter_that_simply_begins_in_first_person_is_not_flagged() -> None:
    """The prompt explicitly wants first-person, warm address — only the specific
    'I am now going to narrate' framing move is forbidden, not first person itself."""
    text = "I remember the courtyard well, the smell of rain on stone, and the old man who waited there for us."
    assert narrative_opening_findings(text) == []


def test_let_me_used_mid_sentence_for_emphasis_is_not_flagged() -> None:
    """'Let me be clear' as emphasis, not narrated at the chapter's very start,
    must not trip the gate — position matters, not just the phrase."""
    text = "The courtyard was quiet. Let me be clear: nothing about that silence was peaceful."
    assert narrative_opening_findings(text) == []


def test_let_me_be_clear_at_the_opening_is_not_flagged() -> None:
    """Emphasis, not narration-announcement — 'let me be clear' is not in the
    forbidden verb set (tell/set down/speak/recount/say)."""
    text = "Let me be clear about what happened that morning: nothing was as it seemed."
    assert narrative_opening_findings(text) == []


def test_a_short_chapter_opening_is_not_flagged() -> None:
    assert narrative_opening_findings("The rain had not stopped in three days.") == []


# ─── wired into the full gate set ─────────────────────────────────────────────
def test_revoice_gates_reverts_a_narrative_announcement_opening() -> None:
    base = "The teacher began his lesson at dawn, as he always did, speaking first of patience."
    revoiced = "Let me tell you how the teacher began his lesson at dawn, as he always did, speaking first of patience."
    gate = revoice_gates(base, revoiced)
    assert any("narrative-announcement" in f for f in gate)


def test_revoice_gates_keeps_a_clean_re_voice() -> None:
    base = "The teacher began his lesson at dawn, as he always did, speaking first of patience."
    revoiced = "The teacher always began at dawn, and that morning he spoke first of patience."
    assert revoice_gates(base, revoiced) == []
