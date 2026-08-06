"""The student-reader lane decides by rule, not by model preference.

Asif's requirement (2026-08-06) is that statements are "purposefully selected,
not randomly by an AI". These tests pin the four places that could quietly become
model judgement: the closed defect vocabulary, the ranking, the per-chapter
budget, and the note identity that makes a re-run an update rather than a
duplicate. Plus the evidence fence, which is what keeps an `unsupported-claim`
note from becoming a verdict on a religious tradition.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _student_reader import (  # noqa: E402
    DEFECT_KINDS,
    MAX_NOTES,
    MIN_NOTES,
    chapter_budget,
    dedupe,
    gate_note,
    note_id,
    select,
    to_companion_note,
)

PROSE = (
    "The Master spoke of the condensation of heat, and the boy did not ask what it was. "
    "He said the seven earths followed from it. "
    "Then he turned to the matter of the five conditions, which he did not name here. "
    "The disciple accepted this without further question."
)


def note(defect: str, quote: str, **kw):
    base = {
        "defect": defect,
        "quote": quote,
        "body": " ".join(["word"] * 40),
        "anchor": "a label",
        "citations": [],
    }
    base.update(kw)
    return base


# ─── the budget ──────────────────────────────────────────────────────────────
def test_budget_scales_with_length_between_a_floor_and_a_cap() -> None:
    # This book's real spread: a 1,160-word opener and a 15,167-word finale.
    assert chapter_budget(1160) == MIN_NOTES, "a short chapter still gets the floor"
    assert chapter_budget(15167) == MAX_NOTES, "the longest is capped, not proportional"
    assert chapter_budget(3639) == 4
    assert chapter_budget(7113) == 6


def test_budget_never_returns_zero() -> None:
    """A chapter with no measurable length must not be silently skipped."""
    assert chapter_budget(0) == MIN_NOTES
    assert chapter_budget(-5) == MIN_NOTES


# ─── the closed vocabulary ───────────────────────────────────────────────────
def test_a_defect_outside_the_vocabulary_is_dropped_not_coerced() -> None:
    ok, reasons = gate_note(note("interesting-observation", "the condensation of heat, and"), PROSE)
    assert not ok
    assert any("not one of the" in r for r in reasons)


def test_every_declared_defect_kind_passes_the_gate() -> None:
    """The vocabulary and the gate must not disagree about what is allowed."""
    for kind in DEFECT_KINDS:
        ok, reasons = gate_note(note(kind, "the condensation of heat, and"), PROSE)
        assert ok, f"{kind}: {reasons}"


# ─── chatter, and what is NOT chatter ────────────────────────────────────────
def test_assistant_voice_is_dropped() -> None:
    chatter = note("undefined-term", "the condensation of heat, and")
    chatter["body"] = "As an AI I cannot judge this passage, but " + " ".join(["word"] * 30)
    ok, reasons = gate_note(chatter, PROSE)
    assert not ok
    assert any("chatter" in r for r in reasons)


def test_a_note_that_talks_about_the_passage_is_NOT_chatter() -> None:
    """This lane's whole job is to talk about a passage.

    The broader pattern borrowed from the teacher lane rejects 'the passage
    above' and 'here is the' — measured on this book, that threw away every
    candidate of a chapter for describing what it had read.
    """
    fine = note("ambiguous-referent", "the condensation of heat, and")
    fine["body"] = "The passage above never says which of the two it means, and here is the difficulty: " + " ".join(
        ["word"] * 25
    )
    ok, reasons = gate_note(fine, PROSE)
    assert ok, reasons


# ─── the anchor ──────────────────────────────────────────────────────────────
def test_a_quote_that_is_not_in_the_chapter_is_dropped() -> None:
    ok, reasons = gate_note(note("undefined-term", "a sentence the book never printed"), PROSE)
    assert not ok
    assert any("verbatim" in r for r in reasons)


def test_a_quote_too_short_to_locate_a_sentence_is_dropped() -> None:
    """A three-word quote matches in several places and highlights the wrong one."""
    ok, reasons = gate_note(note("undefined-term", "the boy did"), PROSE)
    assert not ok
    assert any("too short" in r for r in reasons)


# ─── the evidence fence ──────────────────────────────────────────────────────
def test_claiming_support_without_a_citation_is_a_verdict_and_is_dropped() -> None:
    ok, reasons = gate_note(note("unsupported-claim", "the seven earths followed from it", claims_support=True), PROSE)
    assert not ok
    assert any("verdict" in r for r in reasons)


def test_a_citation_naming_an_invented_corpus_is_dropped() -> None:
    ok, reasons = gate_note(
        note(
            "unsupported-claim",
            "the seven earths followed from it",
            claims_support=True,
            citations=[{"corpus": "wikipedia", "ref": "Seven Earths"}],
        ),
        PROSE,
    )
    assert not ok
    assert any("no real corpus" in r for r in reasons)


def test_a_located_citation_is_accepted() -> None:
    ok, reasons = gate_note(
        note(
            "unsupported-claim",
            "the seven earths followed from it",
            claims_support=True,
            citations=[{"corpus": "quran", "ref": "65:12"}],
        ),
        PROSE,
    )
    assert ok, reasons


# ─── selection is a rule, run twice ──────────────────────────────────────────
def test_selection_ranks_by_defect_priority_then_position() -> None:
    """A passage the reader cannot parse outranks one they cannot corroborate."""
    candidates = [
        note("unsupported-claim", "The disciple accepted this without further question"),
        note("unresolved-double-reading", "the matter of the five conditions"),
    ]
    chosen = select(candidates, PROSE, budget=1)
    assert chosen[0]["defect"] == "unresolved-double-reading"


def test_selection_returns_reading_order_not_severity_order() -> None:
    candidates = [
        note("unsupported-claim", "the seven earths followed from it"),
        note("unresolved-double-reading", "The disciple accepted this without further question"),
    ]
    chosen = select(candidates, PROSE, budget=2)
    quotes = [c["quote"] for c in chosen]
    assert quotes.index("the seven earths followed from it") < quotes.index(
        "The disciple accepted this without further question"
    ), "the reader meets notes while reading, not in order of severity"


def test_the_same_input_selects_the_same_notes_every_time() -> None:
    candidates = [
        note(k, q)
        for k, q in [
            ("unsupported-claim", "the seven earths followed from it"),
            ("undefined-term", "the condensation of heat, and"),
            ("unresolved-double-reading", "the matter of the five conditions"),
        ]
    ]
    first = [c["quote"] for c in select(list(candidates), PROSE, budget=2)]
    second = [c["quote"] for c in select(list(reversed(candidates)), PROSE, budget=2)]
    assert first == second, "input order must not change the outcome"


def test_one_note_per_passage() -> None:
    dupes = [
        note("undefined-term", "the condensation of heat, and"),
        note("unsupported-claim", "the  CONDENSATION of heat,  and"),
    ]
    assert len(dedupe(dupes)) == 1, "same passage, whitespace and case folded"


# ─── identity: a re-run updates ──────────────────────────────────────────────
def test_note_id_is_stable_across_runs_and_insensitive_to_wording_of_the_body() -> None:
    a = note_id("three layers of knowledge", "the seven earths followed from it")
    b = note_id("three layers of knowledge", "the  Seven Earths followed from it ")
    assert a == b, "the same passage in the same chapter is the same note"


def test_note_id_differs_by_chapter() -> None:
    quote = "the seven earths followed from it"
    assert note_id("three layers of knowledge", quote) != note_id("a stranger in the city", quote)


def test_a_filed_note_is_stamped_proposed_and_never_as_the_human() -> None:
    filed = to_companion_note(note("undefined-term", "the condensation of heat, and"), "one")
    assert filed["review"] == "proposed"
    assert filed["source"]["provider"] == "student"
    assert filed["source"]["provider"] != "manual", "a machine note must never wear his byline"
    assert filed["id"].startswith("student:")
