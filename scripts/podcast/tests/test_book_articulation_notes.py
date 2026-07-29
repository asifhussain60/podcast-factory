"""Unit tests for _book_articulation_notes (REQ-BA-160): the out-of-band
ambiguity/comprehension/terminology notes block, extracted before gating so it
never reaches book.md."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_articulation_notes import (  # noqa: E402
    EMPTY_NOTES,
    extract_articulation_notes,
    leaked_marker_findings,
)


def test_no_block_is_a_noop() -> None:
    prose, notes = extract_articulation_notes("Just the chapter prose, nothing else.")
    assert prose == "Just the chapter prose, nothing else."
    assert notes == EMPTY_NOTES
    assert notes is not EMPTY_NOTES  # caller must get its own dict, not the shared constant


def test_empty_candidate_is_a_noop() -> None:
    prose, notes = extract_articulation_notes("")
    assert prose == ""
    assert notes == EMPTY_NOTES


def test_extracts_all_three_note_kinds_and_strips_the_block() -> None:
    candidate = (
        "The teacher spoke of patience at length.\n\n"
        "===ARTICULATION-NOTES===\n"
        "AMBIGUITY: unclear whether 'the elder' refers to the Master or his father\n"
        "COMPREHENSION: a modern reader may not recognize the reference to the well\n"
        "TERMINOLOGY: elder — standardize to 'elder' rather than 'old man'\n"
        "===END-NOTES===\n"
    )
    prose, notes = extract_articulation_notes(candidate)
    assert prose == "The teacher spoke of patience at length."
    assert notes["editorial_queries"] == ["unclear whether 'the elder' refers to the Master or his father"]
    assert notes["comprehension_flags"] == ["a modern reader may not recognize the reference to the well"]
    assert notes["terminology_notes"] == ["elder — standardize to 'elder' rather than 'old man'"]


def test_block_with_only_some_kinds_present() -> None:
    candidate = "Prose here.\n\n===ARTICULATION-NOTES===\nAMBIGUITY: one thing is unclear\n===END-NOTES===\n"
    prose, notes = extract_articulation_notes(candidate)
    assert prose == "Prose here."
    assert notes["editorial_queries"] == ["one thing is unclear"]
    assert notes["comprehension_flags"] == []
    assert notes["terminology_notes"] == []


def test_malformed_block_missing_end_marker_is_left_alone() -> None:
    """A truncated/malformed block does not get silently half-parsed — it is left
    in the candidate, which then trips `leaked_marker_findings` downstream."""
    candidate = "Prose.\n\n===ARTICULATION-NOTES===\nAMBIGUITY: something\n"
    prose, notes = extract_articulation_notes(candidate)
    assert prose == candidate  # unchanged: no END marker, no match
    assert notes == EMPTY_NOTES
    assert leaked_marker_findings(prose)


def test_leaked_marker_findings_clean_text() -> None:
    assert leaked_marker_findings("Ordinary chapter prose with nothing unusual.") == []


def test_leaked_marker_findings_catches_residual_notes_marker() -> None:
    assert leaked_marker_findings("Some prose ===ARTICULATION-NOTES=== stray text") != []


def test_leaked_marker_findings_catches_inline_editorial_query() -> None:
    assert leaked_marker_findings("Some prose [Editorial query: this is unclear] more prose") != []
