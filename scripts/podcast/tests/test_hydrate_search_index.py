"""The cross-content search index: what it indexes, and what it must not miss.

Two failures are pinned here because both were live on 2026-08-31:

  1. Only `chapters/*.txt` was read. The Sessions lane has no such directory —
     its books compose straight into `book/book.md` — so Love Of The Prophet and
     Surah Al-Fateha contributed nothing to the index that exists to make
     sessions searchable. 146,000 words, silently absent.

  2. Arabic was unfindable. FTS5's `remove_diacritics` is a Latin-alphabet
     feature; Arabic tashkeel survive it. Since every Arabic run in these
     editions is vowelled by standing rule and nobody types tashkeel into a
     search box, the corpus that is most Arabic-bearing was the one that could
     not be searched in Arabic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _db  # noqa: E402
import hydrate_search_index as H  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    _db._reset_connection()
    conn = _db.get_connection(db_path=tmp_path / "k.db")
    _db.run_migrations(db_path=tmp_path / "k.db")
    monkeypatch.setattr(H, "LOG_PATH", tmp_path / "log.jsonl")
    yield conn
    _db._reset_connection()


def _book(tmp: Path, slug: str, *, chapters=None, book_md=None, title="A Book") -> object:
    from types import SimpleNamespace

    d = tmp / slug
    (d / "_system").mkdir(parents=True)
    (d / "meta.yml").write_text(yaml.safe_dump({"title": title}), encoding="utf-8")
    (d / "_system" / "series-config.yaml").write_text(
        yaml.safe_dump({"content_profile": "islamic_session"}), encoding="utf-8"
    )
    (d / "_system" / "orchestrator-state.json").write_text('{"phase":"0d","phase_status":"running"}', encoding="utf-8")
    if chapters:
        (d / "chapters").mkdir()
        for name, text in chapters.items():
            (d / "chapters" / name).write_text(text, encoding="utf-8")
    if book_md:
        (d / "book").mkdir()
        (d / "book" / "book.md").write_text(book_md, encoding="utf-8")
    return SimpleNamespace(slug=slug, dir=str(d), bucket="Sessions")


# ── the Arabic fold ──────────────────────────────────────────────────────────
def test_arabic_is_folded_to_its_skeleton_for_search():
    assert H.searchable("حُدُود") == "حدود"


def test_english_passes_through_the_fold_untouched():
    assert H.searchable("the love of the world") == "the love of the world"


def test_a_bilingual_line_keeps_its_english_and_its_word_boundaries():
    """`normalize_arabic` returns a bare skeleton with no spaces — right for
    comparing two spans, wrong for an index. Folding must be per-run."""
    got = H.searchable("The hudud (حُدُود) are ranks")
    assert got == "The hudud (حدود) are ranks"


def test_an_unvowelled_query_finds_vowelled_prose(db, tmp_path):
    ref = _book(tmp_path, "b1", chapters={"ch01-x.txt": "The ranks are حُدُود in the tradition."})
    H.hydrate_book(db, ref)
    H.rebuild_fts(db)
    assert H.search(db, "حدود"), "an unvowelled query must reach vowelled text"


def test_a_vowelled_query_still_works(db, tmp_path):
    ref = _book(tmp_path, "b1", chapters={"ch01-x.txt": "The ranks are حُدُود in the tradition."})
    H.hydrate_book(db, ref)
    H.rebuild_fts(db)
    assert H.search(db, "حُدُود")


def test_the_snippet_keeps_its_diacritics(db, tmp_path):
    """Snippets come from `refined_text`, never the folded copy — what a reader
    is shown must keep the marks the edition prints."""
    ref = _book(tmp_path, "b1", chapters={"ch01-x.txt": "The ranks are حُدُود in the tradition."})
    H.hydrate_book(db, ref)
    H.rebuild_fts(db)
    assert "حُدُود" in H.search(db, "حدود")[0]["snippet"]


# ── what gets indexed ────────────────────────────────────────────────────────
def test_a_book_with_no_chapters_dir_is_read_from_its_reading_edition(db, tmp_path):
    ref = _book(tmp_path, "sess", book_md="# T\n\nfront\n\n## Envy\n\nbody one\n\n## Anger\n\nbody two\n")
    rep = H.hydrate_book(db, ref)
    assert rep["chapters"] == 2, "the Sessions lane composes into book.md, not chapters/"
    titles = [r[0] for r in db.execute("SELECT chapter_title FROM chapters ORDER BY chapter_id")]
    assert titles == ["Envy", "Anger"]


def test_front_matter_before_the_first_heading_is_not_a_chapter(db, tmp_path):
    ref = _book(tmp_path, "sess", book_md="# Title\n\nIntroduction prose.\n\n## Real Chapter\n\nbody\n")
    assert H.hydrate_book(db, ref)["chapters"] == 1


def test_chapters_on_disk_win_over_the_reading_edition(db, tmp_path):
    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "from the chapter file"}, book_md="## X\n\nfrom book.md\n")
    H.hydrate_book(db, ref)
    assert "chapter file" in db.execute("SELECT refined_text FROM chapters").fetchone()[0]


# ── incremental, and safe to re-run ──────────────────────────────────────────
def test_an_unchanged_book_is_skipped_on_the_second_pass(db, tmp_path):
    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "text"})
    assert H.hydrate_book(db, ref)["event"] == "book.hydrated"
    assert H.hydrate_book(db, ref)["event"] == "book.skipped"


def test_force_re_reads_an_unchanged_book(db, tmp_path):
    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "text"})
    H.hydrate_book(db, ref)
    assert H.hydrate_book(db, ref, force=True)["event"] == "book.hydrated"


def test_edited_content_is_re_read_without_force(db, tmp_path):
    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "text"})
    H.hydrate_book(db, ref)
    (Path(ref.dir) / "chapters" / "ch01-a.txt").write_text("different text", encoding="utf-8")
    assert H.hydrate_book(db, ref)["event"] == "book.hydrated"


def test_a_removed_chapter_leaves_the_index(db, tmp_path):
    """A re-segmentation drops seventeen chapters and writes twenty-four. An
    upsert alone would leave the seventeen searchable for ever."""
    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "one", "ch02-b.txt": "two"})
    H.hydrate_book(db, ref)
    (Path(ref.dir) / "chapters" / "ch02-b.txt").unlink()
    H.hydrate_book(db, ref)
    assert db.execute("SELECT count(*) FROM chapters").fetchone()[0] == 1


# ── logging, and failing softly ──────────────────────────────────────────────
def test_every_action_is_logged_as_one_json_object_per_line(db, tmp_path):
    import json

    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "text"})
    H.hydrate_book(db, ref)
    H.hydrate_book(db, ref)  # a skip is an action too
    lines = [json.loads(x) for x in H.LOG_PATH.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [x["event"] for x in lines] == ["book.hydrated", "book.skipped"]
    assert all("at" in x and "slug" in x for x in lines)


def test_one_unreadable_book_does_not_stop_the_others(db, tmp_path):
    from types import SimpleNamespace

    rep = H.hydrate_book(db, SimpleNamespace(slug="ghost", dir=str(tmp_path / "nope"), bucket="Sessions"))
    # A missing folder yields an empty book rather than an exception; either way
    # the walk must continue and the outcome must be on the record.
    assert rep["event"] in {"book.hydrated", "book.failed"}


def test_a_book_whose_meta_carries_a_yaml_date_still_indexes(db, tmp_path):
    """`published: 2026-08-14` parses to a datetime.date, which json.dumps
    refuses. Eleven of twenty-eight books failed on exactly this."""
    import datetime

    ref = _book(tmp_path, "b", chapters={"ch01-a.txt": "text"})
    (Path(ref.dir) / "meta.yml").write_text(
        yaml.safe_dump({"title": "T", "published": datetime.date(2026, 8, 14)}), encoding="utf-8"
    )
    assert H.hydrate_book(db, ref)["event"] == "book.hydrated"


# ── search behaviour ─────────────────────────────────────────────────────────
def test_search_can_be_scoped_to_one_shelf(db, tmp_path):
    H.hydrate_book(db, _book(tmp_path, "s1", chapters={"ch01-a.txt": "ostentation here"}))
    H.rebuild_fts(db)
    assert H.search(db, "ostentation", bucket="Sessions")
    assert H.search(db, "ostentation", bucket="Islamic") == []
