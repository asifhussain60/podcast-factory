"""The writer cannot repeat 2026-07-28.

docs/rca/2026-07-28-automation-deleted-companion-notes.md: an automatic pass
regenerated every chapter and dropped the prior generated notes on its way past,
destroying a curated set. The writer was removed entirely as the remedy. Asif
asked for direct filing again on 2026-08-06, so it is back — and these tests are
the reason that is safe rather than a repeat.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _student_reader_store import (  # noqa: E402
    file_notes,
    merge_notes,
    read_doc,
)

NOW = "2026-08-06T14:00:00Z"
OWNED = "student:0123456789abcdef"
OTHER = "student:fedcba9876543210"

HUMAN = {"id": "8445c19a-067e", "kind": "explanation", "body": "Asif wrote this.", "review": None}


def owned(nid: str = OWNED, body: str = "A student's question about this passage.", **kw):
    n = {"id": nid, "kind": "question", "body": body, "quote": "a passage", "review": "proposed"}
    n.update(kw)
    return n


def test_a_human_note_is_carried_through_untouched() -> None:
    out = merge_notes([HUMAN], [owned()], now=NOW)
    assert out[0] == HUMAN, "his note must come out byte-identical"
    assert len(out) == 2


def test_the_pass_cannot_write_a_note_it_does_not_own() -> None:
    with pytest.raises(ValueError, match="does not own"):
        merge_notes([], [{"id": "8445c19a-067e", "body": "x"}], now=NOW)


def test_a_re_run_refreshes_in_place_rather_than_duplicating() -> None:
    first = merge_notes([], [owned(body="First reading of the passage here.")], now=NOW)
    second = merge_notes(first, [owned(body="Second reading, slightly reworded.")], now=NOW)

    assert len(second) == 1, "the same passage is the same note, not a second one"
    assert second[0]["body"] == "Second reading, slightly reworded."


def test_an_accepted_note_stays_accepted_across_a_re_run() -> None:
    """A pass that reset `review` would ask him to re-accept everything, forever."""
    accepted = merge_notes([], [owned()], now=NOW)
    accepted[0]["review"] = "kept"

    after = merge_notes(accepted, [owned(body="Re-run wording of the same finding.")], now=NOW)

    assert after[0]["review"] == "kept"


def test_created_at_survives_a_refresh() -> None:
    first = merge_notes([], [owned()], now="2026-08-06T10:00:00Z")
    second = merge_notes(first, [owned(body="Reworded on a later run entirely.")], now=NOW)
    assert second[0]["createdAt"] == "2026-08-06T10:00:00Z"
    assert second[0]["updatedAt"] == NOW


def test_a_finding_no_longer_proposed_is_left_in_place_not_swept() -> None:
    """Withdrawing its own earlier findings would delete his acceptances."""
    before = merge_notes([], [owned(nid=OWNED), owned(nid=OTHER)], now=NOW)
    after = merge_notes(before, [owned(nid=OWNED)], now=NOW)
    assert {n["id"] for n in after} == {OWNED, OTHER}


def test_an_unreadable_file_raises_rather_than_reading_as_empty(tmp_path: Path) -> None:
    """Treating corrupt as empty is how a merge becomes an overwrite."""
    d = tmp_path / "book"
    (d / "_system" / "companion-notes").mkdir(parents=True)
    (d / "_system" / "companion-notes" / "1-x.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(Exception):
        read_doc(d, "1-x", "slug")


def test_file_notes_round_trips_to_disk(tmp_path: Path) -> None:
    d = tmp_path / "book"
    (d / "_system" / "companion-notes").mkdir(parents=True)
    path = d / "_system" / "companion-notes" / "1-x.json"
    path.write_text(json.dumps({"slug": "s", "chapter": "1-x", "notes": [HUMAN]}), encoding="utf-8")

    created, refreshed = file_notes(d, "1-x", "s", [owned()], now=NOW)

    doc = json.loads(path.read_text(encoding="utf-8"))
    assert (created, refreshed) == (1, 0)
    assert [n["id"] for n in doc["notes"]] == ["8445c19a-067e", OWNED]


def test_a_traversing_chapter_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        file_notes(tmp_path, "../../etc/passwd", "s", [], now=NOW)


# ─── the chapter-key mirror ──────────────────────────────────────────────────
# section_key mirrors companion/keys.ts sectionKeyFromHeading. A divergence does
# not raise: the note lands in a file the reader never opens and the chapter
# silently shows nothing. These cases are the ones that actually differ between
# the two Python key rules in this repo.
def test_section_key_keeps_the_ordinal_unlike_anchor_key() -> None:
    from _book_edits import anchor_key
    from _student_reader_store import section_key

    heading = "1. The Persian Who Was Dead and Revived"
    assert section_key(heading) == "1-the-persian-who-was-dead-and-revived"
    assert anchor_key(heading) == "the persian who was dead and revived"
    assert section_key(heading) != anchor_key(heading), (
        "if these ever agree, one of them has changed and notes will be misfiled"
    )


def test_section_key_matches_the_files_this_book_already_has() -> None:
    """Pinned to real filenames, not to a restatement of the rule."""
    from _student_reader_store import section_key

    cases = {
        "## 3. The Boy at the Door — Limits and Conditions": "3-the-boy-at-the-door-limits-and-conditions",
        "## 5. The World, the Hereafter, and the Speech of Parables": "5-the-world-the-hereafter-and-the-speech-of-parables",
        "## 8. Homecoming, the Father, and the Debate with Abu Malik": "8-homecoming-the-father-and-the-debate-with-abu-malik",
    }
    for heading, expected in cases.items():
        assert section_key(heading) == expected


def test_section_key_output_always_satisfies_the_traversal_guard() -> None:
    from _student_reader_store import CHAPTER_KEY_RE, section_key

    for heading in ("## 1. A — B, C", "## Introduction to the Book", "## 12. Ma'rifah & Zawq"):
        assert CHAPTER_KEY_RE.match(section_key(heading)), heading


# ─── not asking twice ────────────────────────────────────────────────────────
# The determinism guarantee. Measured on chapter 2 of the-master-and-the-disciple
# (2026-08-06): asked twice about identical prose, the model named two findings
# that did not overlap its first two at all. Each anchored to a different
# sentence, so each minted a different id, and the file went 2 -> 4 notes. The
# merge was correct; the input was not stable. So the pass does not ask twice.
def test_a_chapter_read_before_with_unchanged_prose_is_current(tmp_path: Path) -> None:
    from _student_reader_store import already_current, prose_fingerprint

    d = tmp_path / "book"
    (d / "_system" / "companion-notes").mkdir(parents=True)
    prose = "The Master spoke, and the boy did not ask."
    file_notes(d, "1-x", "s", [owned()], now=NOW, prose=prose)

    assert already_current(d, "1-x", "s", prose)
    assert prose_fingerprint(prose) == prose_fingerprint("  The Master spoke,\n  and the boy did not ask.  "), (
        "reflowing a paragraph is not an edit"
    )


def test_edited_prose_is_read_again(tmp_path: Path) -> None:
    from _student_reader_store import already_current

    d = tmp_path / "book"
    (d / "_system" / "companion-notes").mkdir(parents=True)
    file_notes(d, "1-x", "s", [owned()], now=NOW, prose="The Master spoke.")

    assert not already_current(d, "1-x", "s", "The Master spoke at length.")


def test_a_chapter_with_only_human_notes_is_not_current(tmp_path: Path) -> None:
    """A fingerprint without any of this pass's own notes means it never ran."""
    from _student_reader_store import already_current, prose_fingerprint, write_chapter

    d = tmp_path / "book"
    (d / "_system" / "companion-notes").mkdir(parents=True)
    prose = "The Master spoke."
    write_chapter(d, "1-x", "s", [HUMAN], now=NOW, fingerprint=prose_fingerprint(prose))

    assert not already_current(d, "1-x", "s", prose)
