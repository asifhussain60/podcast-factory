"""The student-reader lane decides by rule, not by model preference.

Asif's requirement (2026-08-06) is that statements are "purposefully selected,
not randomly by an AI". These tests pin the four places that could quietly become
model judgement: the closed defect vocabulary, the ranking, the per-chapter
budget, and the note identity that makes a re-run an update rather than a
duplicate.

Since 2026-08-06 the lane produces a QUESTION and the Ismaili Scholar writes the
card, so the gate's subject changed with it — what is checked now is whether the
question is answerable and whether the passage is real. The evidence fence these
tests used to pin is gone from this module on purpose: the Scholar grounds itself
and resolves its own citations, and a second, weaker fence here would have been a
second answer to where evidence comes from.
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
    gate_finding,
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

QUESTION = "What are the five conditions the Master refers to here, and where does the chapter name them?"


def finding(defect: str, quote: str, **kw):
    base = {"defect": defect, "quote": quote, "question": QUESTION}
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
    ok, reasons = gate_finding(finding("interesting-observation", "the condensation of heat, and"), PROSE)
    assert not ok
    assert any("not one of the" in r for r in reasons)


def test_every_declared_defect_kind_passes_the_gate() -> None:
    """The vocabulary and the gate must not disagree about what is allowed."""
    for kind in DEFECT_KINDS:
        ok, reasons = gate_finding(finding(kind, "the condensation of heat, and"), PROSE)
        assert ok, f"{kind}: {reasons}"


# ─── the question ────────────────────────────────────────────────────────────
def test_a_statement_dressed_as_a_finding_is_dropped() -> None:
    """The lane's output is an ASK. A sentence that does not ask anything is the
    old behaviour returning — a complaint about the book, which is what the
    Scholar exists to replace."""
    ok, reasons = gate_finding(
        finding(
            "undefined-term",
            "the condensation of heat, and",
            question="The chapter never explains what the condensation of heat is meant to be.",
        ),
        PROSE,
    )
    assert not ok
    assert any("statement" in r for r in reasons)


def test_a_question_too_short_to_be_answerable_is_dropped() -> None:
    ok, reasons = gate_finding(
        finding("undefined-term", "the condensation of heat, and", question="What is this?"),
        PROSE,
    )
    assert not ok
    assert any("under the" in r for r in reasons)


def test_a_question_long_enough_to_be_an_essay_is_dropped() -> None:
    ok, reasons = gate_finding(
        finding(
            "undefined-term",
            "the condensation of heat, and",
            question=" ".join(["word"] * 70) + "?",
        ),
        PROSE,
    )
    assert not ok
    assert any("over the" in r for r in reasons)


def test_assistant_voice_is_dropped() -> None:
    ok, reasons = gate_finding(
        finding(
            "undefined-term",
            "the condensation of heat, and",
            question="As an AI, what should I say about the condensation of heat in this passage?",
        ),
        PROSE,
    )
    assert not ok
    assert any("chatter" in r for r in reasons)


def test_saying_you_cannot_tell_is_the_FINDING_not_chatter() -> None:
    """The single most important non-rejection in this gate.

    The prompt asks the reader to mark where "you cannot tell what is meant", so
    a question built on that phrasing is the finding, worded. The pattern
    borrowed from the teacher lane rejected exactly that: measured on this book,
    all six candidates dropped across eight chapters were dropped for it, both of
    chapter 1's among them, and that chapter came back with no notes at all.
    """
    for phrase in (
        "I cannot tell which of the two the chapter means here — which is intended?",
        "I am unable to work out which referent is meant; who is the second one?",
    ):
        ok, reasons = gate_finding(
            finding("ambiguous-referent", "the condensation of heat, and", question=phrase),
            PROSE,
        )
        assert ok, f"{phrase!r}: {reasons}"


# ─── the anchor ──────────────────────────────────────────────────────────────
def test_a_quote_that_is_not_in_the_chapter_is_dropped() -> None:
    ok, reasons = gate_finding(finding("undefined-term", "a sentence the book never printed"), PROSE)
    assert not ok
    assert any("verbatim" in r for r in reasons)


def test_a_quote_too_short_to_locate_a_sentence_is_dropped() -> None:
    """A three-word quote matches in several places and highlights the wrong one."""
    ok, reasons = gate_finding(finding("undefined-term", "the boy did"), PROSE)
    assert not ok
    assert any("too short" in r for r in reasons)


# ─── selection is a rule, run twice ──────────────────────────────────────────
def test_selection_ranks_by_defect_priority_then_position() -> None:
    """A passage the reader cannot parse outranks one they cannot corroborate."""
    candidates = [
        finding("unsupported-claim", "The disciple accepted this without further question"),
        finding("unresolved-double-reading", "the matter of the five conditions"),
    ]
    chosen = select(candidates, PROSE, budget=1)
    assert chosen[0]["defect"] == "unresolved-double-reading"


def test_selection_returns_reading_order_not_severity_order() -> None:
    candidates = [
        finding("unsupported-claim", "the seven earths followed from it"),
        finding("unresolved-double-reading", "The disciple accepted this without further question"),
    ]
    chosen = select(candidates, PROSE, budget=2)
    quotes = [c["quote"] for c in chosen]
    assert quotes.index("the seven earths followed from it") < quotes.index(
        "The disciple accepted this without further question"
    ), "the reader meets notes while reading, not in order of severity"


def test_the_same_input_selects_the_same_notes_every_time() -> None:
    candidates = [
        finding(k, q)
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
        finding("undefined-term", "the condensation of heat, and"),
        finding("unsupported-claim", "the  CONDENSATION of heat,  and"),
    ]
    assert len(dedupe(dupes)) == 1, "same passage, whitespace and case folded"


# ─── identity: a re-run updates ──────────────────────────────────────────────
def test_note_id_is_stable_across_runs_and_insensitive_to_wording() -> None:
    a = note_id("three layers of knowledge", "the seven earths followed from it")
    b = note_id("three layers of knowledge", "the  Seven Earths followed from it ")
    assert a == b, "the same passage in the same chapter is the same note"


def test_note_id_differs_by_chapter() -> None:
    quote = "the seven earths followed from it"
    assert note_id("three layers of knowledge", quote) != note_id("a stranger in the city", quote)


# ─── what gets filed ─────────────────────────────────────────────────────────
def filed(**kw):
    base = dict(
        anchor="the condensation of heat, and",
        body="The condensation of heat is the stage at which…",
        etymology=[],
    )
    base.update(kw)
    return to_companion_note(finding("undefined-term", "the condensation of heat, and"), "one", **base)


def test_a_filed_note_is_stamped_proposed_and_never_as_the_human() -> None:
    note = filed()
    assert note["review"] == "proposed"
    assert note["source"]["provider"] != "manual", "a machine note must never wear his byline"


def test_a_filed_note_is_indistinguishable_from_one_the_Explain_button_made() -> None:
    """Same kind, same provider, same label — because it is the same persona
    through the same code. A different kind would render with a different icon
    and read as a different species of card."""
    note = filed()
    assert note["kind"] == "explanation"
    assert note["source"]["provider"] == "scholar"
    assert note["source"]["label"] == "Ismaili Scholar"


def test_the_id_keeps_the_student_prefix_under_the_scholars_byline() -> None:
    """The byline is what the reader sees; the prefix is what the writer owns.

    `_student_reader_store.OWNED_ID_RE` is the only thing standing between this
    pass and someone else's notes, and it matches on this prefix. Renaming it to
    match the new byline would make every existing note unrecognisable to its own
    writer — a re-run would file duplicates beside them and never update one.
    """
    assert filed()["id"].startswith("student:")


def test_the_body_is_the_scholars_verbatim_and_this_lane_adds_nothing() -> None:
    body = "The five conditions are named in the following chapter, not this one."
    assert filed(body=body)["body"] == body


def test_etymology_is_omitted_rather_than_written_empty() -> None:
    """An empty array and an absent key read differently to the store's cleaner;
    a card with nothing to say about a root should carry no key at all."""
    assert "etymology" not in filed(etymology=[])
    assert filed(etymology=["عِلْم: from ع-ل-م."])["etymology"] == ["عِلْم: from ع-ل-م."]
