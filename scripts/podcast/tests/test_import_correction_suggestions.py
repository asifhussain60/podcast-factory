"""Audit findings become `suggested` corrections a moderator confirms, without ever
becoming replacement text that is really an instruction."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_correction_suggestions as ics  # noqa: E402
from _correction_text import block_texts, read_chapters  # noqa: E402
from correction_test_kit import FakeD1, make_book  # noqa: E402

CHAPTERS = {
    "1. First Chapter": "The teacher said that patience is the key to every door.\n\nA second paragraph about the neighbour who is near and the one far away.\n\nRepeat this. Repeat this.",
    "2. Second Chapter": "The seeker prayed الصلاة عماد الدين at dawn, and then he rested.",
}


def flag(chapter, quote, suggested, **kw):
    f = {
        "chapter": chapter,
        "sev": "P2",
        "category": "meaning",
        "quote": quote,
        "suggested": suggested,
        "certainty": 70,
        "page": 9,
        "status": "open",
    }
    f.update(kw)
    return f


def book_with(tmp_path, flags, chapters=CHAPTERS):
    book = make_book(tmp_path, chapters)
    (book / "_system" / "arabic-verify-flags.json").write_text(json.dumps(flags, ensure_ascii=False), encoding="utf-8")
    toc = {"chapters": [{"bk_index": i + 1, "title": h.split(". ", 1)[1]} for i, h in enumerate(chapters)]}
    (book / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")
    return book


def run(book, d1, *, dry_run=False):
    lines: list[str] = []
    result = ics.run(book, "demo", d1=d1, dry_run=dry_run, out=lines.append)
    return result, "\n".join(lines)


def test_imports_only_open_findings_as_suggested_sweep_corrections(tmp_path):
    flags = [
        flag(1, "patience is the key to every door", "patience opens every door", sev="P1", page=12),
        flag(1, "neighbour who is near", "neighbour who is close", status="applied"),
    ]
    book, fake = book_with(tmp_path, flags), FakeD1()
    result, _ = run(book, fake)
    assert [s["quote"] for s in result["importable"]] == ["patience is the key to every door"]
    row = fake.rows("SELECT * FROM correction")[0]
    assert (row["status"], row["origin"], row["raised_by"], row["certainty"]) == ("suggested", "sweep", "pipeline", 70)
    assert row["id"].startswith("sweep-") and row["kind"] == "meaning" and row["batch_id"] is None
    assert row["rationale_html"] == "Found by the Arabic verification audit (page 12, severity P1)."
    assert row["proposed_text"] == "patience opens every door" and row["anchor_key"] == "first chapter"
    assert row["raised_at"] == row["updated_at"] and row["raised_at"].endswith("Z")


def test_stored_anchor_matches_what_the_reader_computes(tmp_path):
    q = "neighbour who is near"
    book, fake = book_with(tmp_path, [flag(1, q, "neighbour who is close")]), FakeD1()
    run(book, fake)
    row = fake.rows("SELECT * FROM correction")[0]
    text = block_texts(read_chapters(book)[0].body)[row["block_index"]]
    assert text[row["start_offset"] : row["end_offset"]] == q
    assert text[max(0, row["start_offset"] - 48) : row["start_offset"]] == row["prefix"]
    assert row["block_index"] == 1


def test_rerun_is_idempotent(tmp_path):
    book, fake = (
        book_with(tmp_path, [flag(1, "patience is the key to every door", "patience opens every door")]),
        FakeD1(),
    )
    run(book, fake)
    again, out = run(book, fake)
    assert again["already_present"] == 1 and again["to_insert"] == 0
    assert len(fake.rows("SELECT * FROM correction")) == 1
    assert len(fake.rows("SELECT * FROM access_event")) == 1  # nothing new, so no second event
    assert "already imported" in out


def test_id_is_deterministic_and_depends_on_the_suggestion():
    a = ics.correction_id("demo", "q", "s")
    assert a == ics.correction_id("demo", "q", "s") and a.startswith("sweep-")
    assert a != ics.correction_id("demo", "q", "other") and a != ics.correction_id("demo2", "q", "s")


def test_findings_that_cannot_be_anchored_or_are_noops_are_skipped_with_reasons(tmp_path):
    flags = [
        flag(1, "text that is not in the chapter", "anything"),
        flag(1, "Repeat this.", "Repeat that."),  # occurs twice
        flag(1, "patience is the key", "patience is the key"),  # suggestion equals quote
        flag(1, "the key to every door", ""),  # nothing suggested
        flag(9, "patience", "x"),  # no such chapter
    ]
    book, fake = book_with(tmp_path, flags), FakeD1()
    result, out = run(book, fake)
    reasons = " | ".join(s["reason"] for s in result["skipped"])
    assert result["importable"] == [] and len(result["skipped"]) == 5
    for needle in (
        "not in the chapter",
        "2 places",
        "equals the quote",
        "no suggested wording",
        "chapter 9 is not in the book",
    ):
        assert needle in reasons
    assert fake.rows("SELECT * FROM correction") == [] and fake.rows("SELECT * FROM access_event") == []
    assert "skipped" in out


def test_an_instruction_is_never_imported_as_replacement_text(tmp_path):
    quote = "patience is the key to every door"
    instructions = [
        "Add translation.",
        "Delete the second block",
        "(uncertain) something else",
        "Probably: 'a different reading'",
        "...so that facing each rank",
        "No change needed",
        "Note that the source is missing an item",
        "Either keep it or drop it",
        "patience opens every door (ambiguous)",
    ]
    book = book_with(tmp_path, [flag(1, quote, s) for s in instructions])
    result, _ = run(book, FakeD1(), dry_run=True)
    assert result["importable"] == [] and len(result["skipped"]) == len(instructions)
    assert {("instruction" in s["reason"], "editorial note" in s["reason"]) for s in result["skipped"]} == {
        (True, False),
        (False, True),
    }


def test_a_note_the_quote_itself_carries_is_not_an_editorial_note():
    assert ics.not_replacement_wording("blessings (peace be upon them)", "the imams (peace be upon them)") is None
    assert ics.not_replacement_wording("blessings (peace be upon them)", "the imams") is not None


def test_wrapping_quote_marks_added_by_the_audit_are_removed():
    assert ics.clean_suggestion("plain quote", "'Observe mourning abundantly.'") == "Observe mourning abundantly."
    assert ics.clean_suggestion("'quoted' start", "'x'") == "'x'"
    assert ics.clean_suggestion("q", "no quotes here") == "no quotes here"


def test_the_capital_of_a_sentence_start_is_carried_over_and_never_invented():
    # The audit lowercased the start of a list item it was replacing.
    assert (
        ics.clean_suggestion("Truthfulness in one's home", "truthfulness in every situation")
        == "Truthfulness in every situation"
    )
    # A quote that did not start with a capital is left exactly alone.
    assert (
        ics.clean_suggestion("truthfulness at home", "truthfulness in every situation")
        == "truthfulness in every situation"
    )
    # Arabic (and anything else non-ASCII) is never touched.
    assert ics.clean_suggestion("Ali", "\u0639\u0644\u064a") == "\u0639\u0644\u064a"
    # A suggestion that already starts with a capital is unchanged.
    assert ics.clean_suggestion("The house", "The home") == "The home"


def test_category_maps_to_kind():
    assert ics.kind_for("meaning", "plain") == "meaning"
    assert ics.kind_for("citation", "plain") == "citation"
    assert ics.kind_for("bare-arabic", "plain") == "arabic"
    assert ics.kind_for(None, "the saying الصلاة عماد الدين") == "arabic"
    assert ics.kind_for("meaning", "the saying الصلاة عماد الدين") == "meaning"  # the audit's own category wins
    assert ics.kind_for("omission", "plain") == "other" and ics.kind_for(None, "plain") == "other"
    assert ics.kind_for("attribution", "plain") == "other"


def test_arabic_quote_is_imported_as_an_arabic_correction(tmp_path):
    flags = [flag(2, "الصلاة عماد الدين", "اَلصَّلَاةُ عِمَادُ الدِّينِ", category=None)]
    book, fake = book_with(tmp_path, flags), FakeD1()
    run(book, fake)
    row = fake.rows("SELECT kind, anchor_key FROM correction")[0]
    assert (row["kind"], row["anchor_key"]) == ("arabic", "second chapter")


def test_dry_run_reads_and_writes_no_database(tmp_path):
    book = book_with(tmp_path, [flag(1, "patience is the key to every door", "patience opens every door")])
    result, out = run(book, None, dry_run=True)
    assert len(result["importable"]) == 1 and result["to_insert"] == 1 and "would be inserted" in out


def test_writes_are_one_event_per_run_with_the_import_action(tmp_path):
    flags = [
        flag(1, "patience is the key to every door", "patience opens every door"),
        flag(1, "neighbour who is near", "neighbour who is close"),
    ]
    book, fake = book_with(tmp_path, flags), FakeD1()
    run(book, fake)
    ev = fake.rows("SELECT actor, action, subject, scope_type, detail FROM access_event")
    assert ev == [
        {
            "actor": "pipeline",
            "action": "import-suggestions",
            "subject": "demo",
            "scope_type": "correction",
            "detail": "imported 2",
        }
    ]


def test_chapter_mapping_is_proven_against_the_toc(tmp_path):
    book = book_with(tmp_path, [])
    mapping, proof = ics.chapter_map(book, read_chapters(book))
    assert proof == {"toc_entries": 2, "matched_by_title": 2, "agree_with_printed_number": 2, "disagree": []}
    assert mapping[2].key == "second chapter"


def test_toc_title_wins_when_it_disagrees_with_the_printed_number(tmp_path):
    book = make_book(tmp_path, {"3. Alpha": "aaa", "4. Beta": "bbb"})
    (book / "book" / "book-toc.json").write_text(
        json.dumps({"chapters": [{"bk_index": 1, "title": "Alpha"}, {"bk_index": 2, "title": "Beta"}]})
    )
    mapping, proof = ics.chapter_map(book, read_chapters(book))
    assert mapping[1].heading == "3. Alpha" and len(proof["disagree"]) == 2


def test_applied_claim_is_verified_against_the_book(tmp_path):
    flags = [
        flag(1, "a phrase long gone from the book", "x", status="applied"),
        flag(
            1, "patience is the key to every door", "Add translation", status="applied"
        ),  # instruction-type: the block stays
        flag(
            1, "neighbour who is near", "neighbour who is close", status="applied"
        ),  # claims applied but still present
    ]
    book = book_with(tmp_path, flags)
    result, out = run(book, FakeD1(), dry_run=True)
    ac = result["applied_check"]
    assert (ac["claimed"], ac["absent_from_book"], ac["instruction_type"]) == (3, 1, 1)
    assert [p["quote"] for p in ac["still_present"]] == ["neighbour who is near"]
    assert "1 still present" in out


def test_cli_refuses_remote_without_the_second_flag(capsys):
    assert ics.main(["demo", "--remote"]) == 2
    assert "--i-understand-remote" in capsys.readouterr().err


def test_a_suggestion_the_arabic_gate_would_refuse_is_not_imported(tmp_path):
    flags = [flag(2, "prayed الصلاة عماد الدين at dawn", "prayed at dawn", category=None)]  # script removed
    book, fake = book_with(tmp_path, flags), FakeD1()
    result, _ = run(book, fake)
    assert result["importable"] == [] and "Arabic gate" in result["skipped"][0]["reason"]
