"""The round trip: accepted corrections back into the book, through the Composer path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pull_corrections as pc  # noqa: E402
from correction_test_kit import FakeD1, book_md, make_book  # noqa: E402

Q1 = "patience is the key to every door"
Q2 = "the neighbour who is near"


def accept(fake, cid, quote, proposed, **kw):
    return fake.add_correction(id=cid, quote=quote, proposed_text=proposed, status="accepted", **kw)


def go(book, fake, tmp_path, *, apply=False):
    lines: list[str] = []
    report = pc.run(book, "demo", d1=fake, apply=apply, repo_root=tmp_path / "repo", out=lines.append)
    return report, "\n".join(lines)


def test_dry_run_prints_the_diff_and_changes_nothing(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", Q1, "patience opens every door")
    before = book_md(book)
    report, out = go(book, fake, tmp_path)
    assert report["ready"] == ["a"] and report["applied"] == []
    assert "-The teacher said that patience is the key to every door." in out
    assert "+The teacher said that patience opens every door." in out
    assert "DRY RUN" in out
    assert book_md(book) == before
    assert not (book / "_system" / "composer-edits.json").exists()
    assert fake.rows("SELECT status FROM correction")[0]["status"] == "accepted"
    assert fake.rows("SELECT * FROM correction_applied") == [] and fake.rows("SELECT * FROM access_event") == []
    assert not (tmp_path / "repo").exists()


def test_apply_goes_through_the_composer_path_and_stamps_the_database(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", Q1, "patience opens every door")
    report, out = go(book, fake, tmp_path, apply=True)
    assert report["applied"] == ["a"]
    md = book_md(book)
    assert "patience opens every door" in md and Q1 not in md
    assert "## 2. Second Chapter" in md and "Another chapter begins here" in md  # neighbours untouched
    # The Composer's own record: this is what makes the edit survive a re-compose.
    edits = json.loads((book / "_system" / "composer-edits.json").read_text())["edits"]
    assert [e["chapter_key"] for e in edits] == ["first chapter"]
    assert "patience opens every door" in edits[0]["body_md"]
    assert (book / "book" / "book.md.bak").exists()
    row = fake.rows("SELECT status, applied_at, updated_at FROM correction")[0]
    assert row["status"] == "applied" and row["applied_at"] == row["updated_at"]
    assert fake.rows("SELECT slug, anchor_key, old_text, new_text FROM correction_applied") == [
        {"slug": "demo", "anchor_key": "first chapter", "old_text": Q1, "new_text": "patience opens every door"}
    ]
    ev = fake.rows("SELECT actor, action, subject, scope_type, scope_id FROM access_event")
    assert ev == [
        {
            "actor": "pipeline",
            "action": "apply-correction",
            "subject": "demo",
            "scope_type": "correction",
            "scope_id": "a",
        }
    ]
    assert "publish_to_listener.py demo" in out and "Compose is NOT needed" in out


def test_two_corrections_in_one_chapter_both_apply(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", Q1, "patience opens every door")
    accept(fake, "b", Q2, "the neighbour who is close")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert sorted(report["applied"]) == ["a", "b"]
    md = book_md(book)
    assert "patience opens every door" in md and "the neighbour who is close" in md


def test_missing_ambiguous_and_formatted_quotes_are_orphaned_not_guessed(tmp_path):
    book = make_book(
        tmp_path,
        {"1. First Chapter": "one door and one door.\n\nthe neighbour who is **near** and dear\n\nsomething stays"},
    )
    fake = FakeD1()
    accept(fake, "twice", "one door", "x")
    accept(fake, "gone", "never written", "x")
    accept(fake, "bold", "who is near", "who is close")
    accept(fake, "nochapter", "something", "x", anchor_key="vanished chapter")
    before = book_md(book)
    report, out = go(book, fake, tmp_path, apply=True)
    assert sorted(i for i, _ in report["orphaned"]) == ["bold", "gone", "nochapter", "twice"]
    assert report["applied"] == [] and book_md(book) == before
    assert "2 places" in out and "spans formatting" in out and "no longer in the book" in out
    assert {r["status"] for r in fake.rows("SELECT status FROM correction")} == {"accepted"}


def test_overlapping_accepted_corrections_are_both_withheld(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", "patience is the key", "patience is a key")
    accept(fake, "b", "the key to every door", "the way through every door")
    accept(fake, "c", Q2, "the neighbour who is close")  # elsewhere: still fine
    report, out = go(book, fake, tmp_path, apply=True)
    assert sorted(i for i, _ in report["overlapping"]) == ["a", "b"]
    assert report["applied"] == ["c"]
    assert "neither is applied" in out
    assert "patience is the key to every door" in book_md(book)
    assert {r["id"]: r["status"] for r in fake.rows("SELECT id, status FROM correction")} == {
        "a": "accepted",
        "b": "accepted",
        "c": "applied",
    }


def test_narrative_frame_gate_blocks_a_change_of_narrator(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", "The teacher said that patience", "I said to them that patience")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert report["refused"] and "narrative-frame" in report["refused"][0][1][0]
    assert "The teacher said" in book_md(book)


ARABIC = {"1. First Chapter": "He taught the saying الصلاة عماد الدين to the students, and they wrote it down."}


def test_arabic_change_must_be_marks_only_at_apply_time(tmp_path):
    book = make_book(tmp_path, ARABIC)
    fake = FakeD1()
    accept(fake, "bad", "الصلاة عماد الدين", "الصلاة عماد الديانة", kind="arabic")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert "letters changed" in report["refused"][0][1][0] and "الديانة" not in book_md(book)
    fake2 = FakeD1()
    accept(fake2, "good", "الصلاة عماد الدين", "اَلصَّلَاةُ عِمَادُ الدِّينِ", kind="arabic")
    report2, _ = go(book, fake2, tmp_path, apply=True)
    assert report2["applied"] == ["good"] and "اَلصَّلَاةُ" in book_md(book)


def test_quranic_letter_change_is_never_applied(tmp_path):
    from _mushaf import is_quranic

    if not is_quranic("قُلْ هُوَ اللَّهُ أَحَدٌ"):
        pytest.skip("canonical mushaf mirror not present")
    book = make_book(tmp_path, {"1. First Chapter": "He recited قُلْ هُوَ اللَّهُ أَحَدٌ in the prayer, then sat quietly."})
    fake = FakeD1()
    accept(fake, "q", "قُلْ هُوَ اللَّهُ أَحَدٌ", "قُلْ هُوَ اللَّهُ أَحَدًا وَاحِدًا", kind="arabic")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert report["applied"] == [] and any("quran-letters" in r for _, rs in report["refused"] for r in rs)


def test_spoken_lane_books_keep_ninety_percent_of_a_chapter(tmp_path):
    body = "One two three four five six seven eight nine ten."
    book = make_book(tmp_path, {"1. First Chapter": body}, bucket="Sessions")
    fake = FakeD1()
    accept(fake, "a", "four five six", "FOUR")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert report["applied"] == [] and "word-retention" in report["refused"][0][1][0]
    assert body in book_md(book)


def test_proposal_equal_to_quote_is_refused(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    accept(fake, "a", Q1, Q1)
    report, _ = go(book, fake, tmp_path)
    assert report["refused"] and "equals the quote" in report["refused"][0][1][0]


def test_non_accepted_corrections_are_never_pulled(tmp_path):
    book = make_book(tmp_path)
    fake = FakeD1()
    fake.add_correction(id="o", quote=Q1, proposed_text="x", status="open")
    fake.add_correction(id="d", quote=Q2, proposed_text="x", status="dismissed")
    report, _ = go(book, fake, tmp_path, apply=True)
    assert report["accepted"] == 0 and Q1 in book_md(book)


def test_a_database_failure_after_the_write_says_how_to_finish(tmp_path):
    book = make_book(tmp_path)
    inner = FakeD1()
    accept(inner, "a", Q1, "patience opens every door")

    def flaky(sql, *, remote):
        if sql.lstrip().upper().startswith("UPDATE"):
            raise RuntimeError("D1 unavailable")
        return inner(sql, remote=remote)

    lines: list[str] = []
    pc.run(book, "demo", d1=flaky, apply=True, repo_root=tmp_path / "r", out=lines.append)
    out = "\n".join(lines)
    assert "patience opens every door" in book_md(book)  # the truth on disk is the book
    assert "DATABASE WRITE FAILED" in out and "UPDATE correction SET status = 'applied'" in out


def test_podcast_lane_and_read_along_are_reported(tmp_path):
    book = make_book(tmp_path, bucket="Audiobook")
    (book / "chapters").mkdir()
    (book / "chapters" / "ch01.txt").write_text(f"The host says {Q1} again.", encoding="utf-8")
    fake = FakeD1()
    accept(fake, "a", Q1, "patience opens every door")
    report, out = go(book, fake, tmp_path, apply=True)
    assert report["follow_ups"]["podcast_lane_still_old"] == [{"id": "a", "files": ["ch01.txt"]}]
    assert "still carries the OLD wording" in out
    assert "generate_reader_narration.py demo" in report["follow_ups"]["read_along"]
    assert report["follow_ups"]["read_along_chapters"] == ["1. First Chapter"]


def test_systemic_cluster_is_reported_and_ledgered_once_on_apply(tmp_path):
    book = make_book(
        tmp_path,
        {
            "1. First Chapter": "the neighbour near us.\n\nthe neighbour near them.\n\nthe neighbour near you.\n\nunrelated words here."
        },
    )
    fake = FakeD1()
    for i, who in enumerate(("us", "them", "you")):
        fake.add_correction(
            id=f"s{i}",
            quote=f"neighbour near {who}",
            proposed_text=f"neighbour far {who}",
            kind="meaning",
            status="open",
        )
    report, out = go(book, fake, tmp_path)  # dry run
    assert [c["count"] for c in report["systemic"]] == [3] and "pipeline defect" in out
    assert not (tmp_path / "repo" / "_learning" / "findings.jsonl").exists()  # dry run appends nothing
    go(book, fake, tmp_path, apply=True)
    go(book, fake, tmp_path, apply=True)  # idempotent
    ledger = (tmp_path / "repo" / "_learning" / "findings.jsonl").read_text().splitlines()
    assert len(ledger) == 1
    rec = json.loads(ledger[0])
    assert (rec["source"], rec["check_id"], rec["book"]) == ("pull_corrections", "CR-SYSTEMIC", "demo")
    assert "near -> far" in rec["signature"] and "s0" in rec["context_excerpt"]


def test_two_of_a_kind_is_not_systemic():
    rows = [{"id": str(i), "kind": "meaning", "quote": "near", "proposed_text": "far"} for i in range(2)]
    assert pc.systemic_clusters(rows) == []
    assert (
        len(pc.systemic_clusters(rows + [{"id": "3", "kind": "meaning", "quote": "near", "proposed_text": "far"}])) == 1
    )
    # A different kind is a different shape.
    mixed = rows + [{"id": "3", "kind": "typo", "quote": "near", "proposed_text": "far"}]
    assert pc.systemic_clusters(mixed) == []


def test_glossary_candidates_need_a_recurring_replaced_token(tmp_path):
    book = make_book(
        tmp_path,
        {
            "1. First Chapter": "the book of zawatah said.\n\nzawatah appears here.\n\nand zawatah once more.\n\nzawata alone."
        },
    )
    fake = FakeD1()
    fake.add_correction(
        id="g", quote="the book of zawatah", proposed_text="the book of zawata", kind="citation", status="open"
    )
    fake.add_correction(id="t", quote="alone", proposed_text="together", kind="typo", status="open")  # wrong kind
    report, out = go(book, fake, tmp_path)
    assert [(c["term"], c["rendering"], c["occurrences_in_book"]) for c in report["glossary_candidates"]] == [
        ("zawatah", "zawata", 3)
    ]
    assert "GLOSSARY CANDIDATES" in out and "never edited" in out


def test_glossary_candidates_ignore_stop_words_and_sentence_rewrites():
    book = "of of of of the and the and unless unless"
    rows = [
        {"id": "1", "kind": "meaning", "quote": "cup of tea", "proposed_text": "cup for tea"},  # stop-word swap
        {
            "id": "2",
            "kind": "meaning",
            "quote": "a long sentence with many words in it that is quite long",
            "proposed_text": "a long sentence with many words in it that is short",
        },
        {
            "id": "3",
            "kind": "citation",
            "quote": "one two",
            "proposed_text": "three four five six",
        },  # two changes' worth? single replace, but not a term in the book
    ]
    assert pc.glossary_candidates(rows, book) == []


def test_remote_is_refused_without_the_second_flag(capsys):
    assert pc.main(["demo", "--remote"]) == 2
    assert "--i-understand-remote" in capsys.readouterr().err
    assert pc.main(["demo", "--remote", "--apply"]) == 2


def test_word_changes_and_shape():
    assert pc.word_changes("The Neighbour near us", "the neighbour far us") == [("near", "far")]
    assert pc.shape_of({"kind": "meaning", "quote": "same", "proposed_text": "same"}) is None
