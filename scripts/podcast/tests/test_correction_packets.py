"""Correction packets: deterministic, complete, and gated before any model runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_correction_packets as bcp  # noqa: E402
from _correction_packets import (  # noqa: E402
    build_packet,
    gate_summary,
    gates_of,
    load_context,
    text_quality,
    verdict_from_gates,
    word_retention,
)
from correction_test_kit import FakeD1, add_source, make_book  # noqa: E402

QUOTE = "patience is the key to every door"


def _row(fake, **kw):
    return fake.add_correction(
        quote=kw.pop("quote", QUOTE), proposed_text=kw.pop("proposed_text", "patience opens every door"), **kw
    )


def _packet(book, row, others=()):
    ctx = load_context(book, "demo")
    return build_packet(ctx, row, [row, *others])


def _gate(packet, gate_id):
    return next((g for g in gates_of(packet) if g.id == gate_id), None)


def test_packet_has_every_block_and_a_stable_hash(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    row = _row(fake, rationale_html="<p>clearer <b>English</b></p>")
    a, b = _packet(book, row), _packet(book, row)
    assert a["packet_hash"] == b["packet_hash"]
    for block in (
        "claim",
        "passage",
        "source",
        "book_rules",
        "vocabulary",
        "prior_knowledge",
        "is_quranic",
        "other_lane",
        "gates",
    ):
        assert block in a
    assert a["claim"]["rationale"] == "clearer English"  # markup stripped for the reviewer
    assert a["passage"]["marked"].count("[[") == 1 and "[[" + QUOTE + "]]" in a["passage"]["marked"]
    assert [p["role"] for p in a["passage"]["paragraphs"]] == ["target", "after"]
    assert a["book_rules"]["narrative_frame"] == "transmitted_report"
    assert a["book_rules"]["lane"] == "Islamic"
    assert verdict_from_gates(gates_of(a)) is None  # nothing wrong: ask the AI


def test_hash_changes_when_the_proposal_is_edited(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    row = _row(fake)
    edited = dict(row, proposed_text="patience unlocks every door")
    assert _packet(book, row)["packet_hash"] != _packet(book, edited)["packet_hash"]


def test_book_without_source_yields_none_not_an_error(tmp_path):
    book = make_book(tmp_path)
    p = _packet(book, _row(FakeD1()))
    assert p["source"] == {"kind": "none", "spans": []}
    assert _gate(p, "source-span").result == "warn"


def test_source_span_is_matched_by_chapter_pages_and_labelled(tmp_path):
    book = make_book(tmp_path)
    add_source(
        book,
        pages={n: f"page {n} scan text " * 20 for n in range(1, 8)},
        crosswalk_pages={1: [1, 2, 3, 4, 5, 6, 7]},
        titles={1: "First Chapter"},
    )
    p = _packet(book, _row(FakeD1()))
    span = p["source"]["spans"][0]
    assert p["source"]["kind"] == "scan" and span["kind"] == "scan"
    assert span["selection"] == "proportional" and len(span["pages"]) <= 3
    assert span["chapter_pages"] == [1, 7]
    assert "[page" in span["text"]
    assert _gate(p, "source-span").result == "ok"


def test_flag_page_narrows_the_source_window_and_the_flag_is_prior_knowledge(tmp_path):
    book = make_book(tmp_path)
    add_source(
        book,
        pages={n: f"page {n} scan text " * 20 for n in range(1, 8)},
        crosswalk_pages={1: [1, 2, 3, 4, 5, 6, 7]},
        titles={1: "First Chapter"},
    )
    flags = [
        {
            "chapter": 1,
            "sev": "P2",
            "category": "meaning",
            "quote": QUOTE,
            "suggested": "x",
            "certainty": 60,
            "page": 6,
            "status": "open",
        }
    ]
    (book / "_system" / "arabic-verify-flags.json").write_text(json.dumps(flags), encoding="utf-8")
    p = _packet(book, _row(FakeD1()))
    assert p["source"]["spans"][0]["selection"] == "flag-page"
    assert 6 in p["source"]["spans"][0]["pages"]
    assert p["prior_knowledge"]["audit_flags"][0]["page"] == 6


def test_quote_must_resolve_to_exactly_one_place(tmp_path):
    book = make_book(tmp_path, {"1. First Chapter": "one door. one door.\n\nsomething else"})
    fake = FakeD1()
    twice = _packet(book, _row(fake, quote="one door"))
    assert _gate(twice, "quote-resolves").result == "no" and "2 places" in _gate(twice, "quote-resolves").note
    assert verdict_from_gates(gates_of(twice)) == "reject"
    gone = _packet(book, _row(fake, id="c2", quote="never written"))
    assert _gate(gone, "quote-resolves").result == "no"
    orphan = _packet(book, _row(fake, id="c3", anchor_key="no such chapter"))
    assert _gate(orphan, "quote-resolves").result == "no"


def test_overlap_with_another_live_correction_is_a_hard_no(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    a = _row(fake, id="a", start_offset=10, end_offset=40)
    b = _row(fake, id="b", start_offset=30, end_offset=60, quote="x", proposed_text="y")
    p = _packet(book, a, [b])
    assert _gate(p, "overlap").result == "no"
    assert verdict_from_gates(gates_of(p)) == "reject"
    assert "overlaps" in gate_summary(gates_of(p), "reject")
    apart = _packet(book, a, [dict(b, start_offset=80, end_offset=90)])
    assert _gate(apart, "overlap").result == "ok"
    dismissed = _packet(book, a, [dict(b, status="dismissed")])
    assert _gate(dismissed, "overlap").result == "ok"


ARABIC_PARA = {"1. First Chapter": "He taught the saying الصلاة عماد الدين to the students, and they wrote it down."}


def test_arabic_change_must_be_marks_only(tmp_path):
    book = make_book(tmp_path, ARABIC_PARA)
    fake = FakeD1()
    ok = _packet(book, _row(fake, quote="الصلاة عماد الدين", proposed_text="اَلصَّلَاةُ عِمَادُ الدِّينِ", kind="arabic"))
    assert _gate(ok, "arabic-marks-only").result == "ok"
    bad = _packet(
        book, _row(fake, id="c2", quote="الصلاة عماد الدين", proposed_text="الصلاة عماد الديانة", kind="arabic")
    )
    g = _gate(bad, "arabic-marks-only")
    assert g.result == "no" and "letters changed" in g.note
    assert verdict_from_gates(gates_of(bad)) == "reject"
    # An English-only change around untouched script is free.
    english = _packet(
        book,
        _row(
            fake,
            id="c3",
            quote="He taught the saying الصلاة عماد الدين",
            proposed_text="He taught the saying الصلاة عماد الدين",
            kind="typo",
        ),
    )
    assert _gate(english, "arabic-marks-only").result == "ok"


def test_arabic_run_count_change_is_refused(tmp_path):
    book = make_book(tmp_path, ARABIC_PARA)
    p = _packet(
        book, _row(FakeD1(), quote="الصلاة عماد الدين", proposed_text="prayer is the pillar of religion", kind="arabic")
    )
    assert _gate(p, "arabic-marks-only").result == "no"


def _mushaf_available() -> bool:
    from _mushaf import is_quranic

    return is_quranic("قُلْ هُوَ اللَّهُ أَحَدٌ")


@pytest.mark.skipif(not _mushaf_available(), reason="canonical mushaf mirror not present")
def test_quranic_letter_change_goes_to_a_person_never_the_model(tmp_path):
    book = make_book(tmp_path, {"1. First Chapter": "He recited قُلْ هُوَ اللَّهُ أَحَدٌ in the prayer, then sat quietly."})
    fake = FakeD1()
    letters = _packet(book, _row(fake, quote="قُلْ هُوَ اللَّهُ أَحَدٌ", proposed_text="قُلْ هُوَ اللَّهُ أَحَدًا وَاحِدًا", kind="arabic"))
    assert letters["is_quranic"] is True
    assert _gate(letters, "quran-letters").result == "no"
    assert verdict_from_gates(gates_of(letters)) == "needs_human"  # outranks the arabic gate's reject
    assert "person" in gate_summary(gates_of(letters), "needs_human")
    english_only = _packet(
        book,
        _row(
            fake,
            id="c2",
            quote="He recited قُلْ هُوَ اللَّهُ أَحَدٌ in the prayer",
            proposed_text="He recited قُلْ هُوَ اللَّهُ أَحَدٌ during the prayer",
        ),
    )
    assert _gate(english_only, "quran-letters").result == "ok"  # the verse is untouched; only English moved


def test_narrative_frame_gate_catches_a_change_of_narrator(tmp_path):
    book = make_book(tmp_path)
    p = _packet(
        book, _row(FakeD1(), quote="The teacher said that patience", proposed_text="I said to them that patience")
    )
    g = _gate(p, "narrative-frame")
    assert g.result == "no" and "first-person" in g.note
    assert verdict_from_gates(gates_of(p)) == "reject"


def test_existing_composer_edit_is_a_warning_not_a_refusal(tmp_path):
    book = make_book(tmp_path)
    (book / "_system" / "composer-edits.json").write_text(
        json.dumps(
            {
                "schema": "podcast.composer-edits/v1",
                "edits": [{"chapter_key": "first chapter", "body_md": "x", "saved_at": "t"}],
            }
        ),
        encoding="utf-8",
    )
    p = _packet(book, _row(FakeD1()))
    assert _gate(p, "composer-edit").result == "warn"
    assert p["prior_knowledge"]["composer_edit"]["present"] is True
    assert verdict_from_gates(gates_of(p)) is None


def test_spoken_lane_books_must_retain_ninety_percent_of_the_chapter(tmp_path):
    body = "The teacher spoke briefly. Patience is everything."
    book = make_book(tmp_path, {"1. First Chapter": body}, bucket="Sessions")
    fake = FakeD1()
    heavy = _packet(book, _row(fake, quote="The teacher spoke briefly. Patience is everything.", proposed_text="Wait."))
    g = _gate(heavy, "word-retention")
    assert g.result == "no" and verdict_from_gates(gates_of(heavy)) == "reject"
    light_book = make_book(
        tmp_path / "b",
        {"1. First Chapter": " ".join(["word"] * 40) + " patience is the key to every door"},
        bucket="Sessions",
    )
    light = _packet(light_book, _row(fake, id="c2", proposed_text="patience is the key to each door"))
    assert _gate(light, "word-retention").result == "ok"
    # Reading-lane books have no such gate at all.
    assert _gate(_packet(make_book(tmp_path / "c"), _row(fake, id="c3")), "word-retention") is None


def test_word_retention_counts_survivors_per_paragraph():
    old = "one two three four\n\nfive six"
    assert word_retention(old, old) == 1.0
    assert word_retention(old, "one two three FOUR\n\nfive six") == pytest.approx(5 / 6)


def test_other_lane_is_flagged_when_the_podcast_text_carries_the_same_words(tmp_path):
    book = make_book(tmp_path)
    (book / "chapters").mkdir()
    (book / "chapters" / "ch01-first.txt").write_text(
        "Here, patience is the key to every door, said the host.", encoding="utf-8"
    )
    p = _packet(book, _row(FakeD1()))
    assert p["other_lane"]["appears_in"] == ["ch01-first.txt"]
    assert "podcast" in p["other_lane"]["note"]


def test_vocabulary_carries_glossary_terms_present_in_the_passage(tmp_path):
    book = make_book(tmp_path, {"1. First Chapter": "The wali guided them, and patience is the key to every door."})
    (book / "_system" / "glossary.yml").write_text(
        'schema_version: 1\nentries:\n  - phonetic: "wali"\n    transliteration: "wali"\n    arabic_script: "وَلِيّ"\n  - phonetic: "zakat"\n    transliteration: "zakat"\n',
        encoding="utf-8",
    )
    p = _packet(book, _row(FakeD1()))
    assert [v["phonetic"] for v in p["vocabulary"]] == ["wali"]


def test_text_quality_grades_a_scan():
    assert text_quality("a clean sentence of ordinary words that reads perfectly well and goes on " * 3) == "clean"
    assert text_quality("x") == "unreliable"
    assert text_quality("~ ^ | ) ( ; ; : 1 1 2 . . , , - - = = _ _ " * 6) == "unreliable"


def test_build_all_writes_one_file_per_reviewable_correction(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    _row(fake, id="a")
    _row(fake, id="b", status="suggested")
    _row(fake, id="skip-me", status="applied")
    packets = bcp.build_all(book, "demo", d1=fake)
    assert sorted(p["correction_id"] for p in packets) == ["a", "b"]
    written = sorted(p.name for p in (book / "_system" / "corrections" / "packets").iterdir())
    assert written == ["a.json", "b.json"]
    assert json.loads((book / "_system" / "corrections" / "packets" / "a.json").read_text())["correction_id"] == "a"
    only = bcp.build_all(book, "demo", d1=fake, correction_id="b", write=False)
    assert [p["correction_id"] for p in only] == ["b"]


def test_cli_refuses_remote_without_the_second_flag(capsys):
    assert bcp.main(["demo", "--remote"]) == 2
    assert "--i-understand-remote" in capsys.readouterr().err


def test_a_persons_quality_verdict_on_the_scan_overrides_the_heuristic(tmp_path):
    book = make_book(tmp_path)
    add_source(
        book,
        pages={1: "the clean sentence of ordinary words " * 10},
        crosswalk_pages={1: [1]},
        titles={1: "First Chapter"},
    )
    assert _packet(book, _row(FakeD1()))["source"]["spans"][0]["quality"] == "clean"
    (book / "_system" / "source" / "ocr" / "quality.json").write_text('{"quality": "noisy"}', encoding="utf-8")
    assert _packet(book, _row(FakeD1(), id="c2"))["source"]["spans"][0]["quality"] == "noisy"
