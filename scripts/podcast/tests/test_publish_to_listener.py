#!/usr/bin/env python3
"""The SQL the publisher emits, executed against real SQLite.

Two greps on the TypeScript side guard the locked rule that `status` and
`open_to_all` are never written. A grep proves a string is absent; it does not
prove the emitted SQL is correct. This runs it.

Also here: the session-disagreement report. The pipeline DERIVES sessions from a
book's plan and the Listener READS them from folder names, the folder names win,
and until now nothing compared the two — which is how Degrees of Excellence
shipped under a lone "Session 4", numbered from its source-chapter index instead
of its position in the series.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import publish_to_listener as ptl  # noqa: E402
from _listener_book import Asset, Book, Chapter, ChapterNarration, Episode, Session  # noqa: E402
from _listener_media import collect_reader_narration  # noqa: E402
from publish_to_listener import build_sql, remote_batches, session_concerns  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parents[3] / "listener" / "migrations"


def db_with_schema() -> sqlite3.Connection:
    """Every migration, in order, exactly as wrangler applies them."""
    conn = sqlite3.connect(":memory:")
    for path in sorted(MIGRATIONS.glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))
    return conn


def a_book(tmp_path: Path) -> Book:
    book = Book(
        slug="test-book",
        bucket="Islamic",
        directory=tmp_path,
        title="Test Book",
        title_arabic="كتاب",
        title_language="ar",
        study_track=None,
        blurb="<p>A blurb.</p>",
        edition_note=None,
    )
    book.chapters.append(Chapter(anchor="one", idx=1, title="1. One", markdown="a b c", html="<p>a b c</p>"))
    book.episodes.append(Episode(number=1, title="Episode one", blurb=None, style="deep_dive"))
    return book


def test_the_emitted_sql_actually_runs(tmp_path):
    conn = db_with_schema()
    conn.executescript(build_sql(a_book(tmp_path), published_at="2026-08-04T00:00:00Z", commit="abc123"))

    # Scoped to the slug: `0003_seed_catalog.sql` already put a row in
    # `content_unit` for every book in the repo, so an unscoped count here would
    # be measuring the seed rather than this write.
    assert conn.execute("SELECT count(*) FROM chapter WHERE slug='test-book'").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM episode WHERE slug='test-book'").fetchone()[0] == 1
    assert conn.execute("SELECT title FROM content_unit WHERE slug='test-book'").fetchone()[0] == "Test Book"
    assert conn.execute("SELECT title_arabic, title_language FROM unit_detail WHERE slug='test-book'").fetchone() == (
        "كتاب",
        "ar",
    )


def test_a_newly_published_book_is_a_draft_nobody_can_see(tmp_path):
    """THE locked rule. The publish step never names `status` or `open_to_all`, so
    the schema defaults apply and a book arrives complete and invisible until a
    human turns it on in /admin. Asserted on the ROW, not on the source text."""
    conn = db_with_schema()
    conn.executescript(build_sql(a_book(tmp_path), published_at="2026-08-04T00:00:00Z", commit=None))

    status, open_to_all = conn.execute(
        "SELECT status, open_to_all FROM content_unit WHERE slug = 'test-book'"
    ).fetchone()
    assert status == "draft"
    assert open_to_all == 0


def test_re_publishing_does_not_flip_a_book_back_to_draft(tmp_path):
    """The upsert must not undo a human's decision to publish. A book already
    switched on in /admin stays on when its prose is corrected."""
    conn = db_with_schema()
    book = a_book(tmp_path)
    conn.executescript(build_sql(book, published_at="2026-08-04T00:00:00Z", commit=None))
    conn.execute("UPDATE content_unit SET status = 'published', open_to_all = 1 WHERE slug = 'test-book'")

    conn.executescript(build_sql(book, published_at="2026-08-05T00:00:00Z", commit=None))

    assert conn.execute("SELECT status, open_to_all FROM content_unit WHERE slug = 'test-book'").fetchone() == (
        "published",
        1,
    )


def test_a_dropped_chapter_stops_being_readable(tmp_path):
    """Each table is cleared and rewritten so DELETION works — an upsert-only
    script would leave a removed chapter readable forever."""
    conn = db_with_schema()
    book = a_book(tmp_path)
    book.chapters.append(Chapter(anchor="two", idx=2, title="2. Two", markdown="d", html="<p>d</p>"))
    conn.executescript(build_sql(book, published_at="x", commit=None))
    assert conn.execute("SELECT count(*) FROM chapter WHERE slug='test-book'").fetchone()[0] == 2

    book.chapters.pop()
    conn.executescript(build_sql(book, published_at="x", commit=None))

    assert [r[0] for r in conn.execute("SELECT anchor_key FROM chapter WHERE slug='test-book'")] == ["one"]


def test_chapter_narration_is_rewritten_with_the_chapter(tmp_path):
    conn = db_with_schema()
    book = a_book(tmp_path)
    audio = tmp_path / "book" / "narration" / "one.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"MP3")
    asset = Asset(
        key="test-book/narration/one.mp3",
        slug="test-book",
        kind="audio",
        content_type="audio/mpeg",
        path=audio,
    )
    book.assets.append(asset)
    book.chapters[0].narration = ChapterNarration(
        audio=asset,
        duration_s=12.5,
        source_hash="abc",
        voice="aria",
        cues=[{"idx": 0, "blockIndex": 0, "startS": 0, "endS": 12.5, "text": "a b c"}],
    )

    old_root = ptl.REPO_ROOT
    ptl.REPO_ROOT = tmp_path
    try:
        conn.executescript(ptl.build_sql(book, published_at="x", commit=None))
    finally:
        ptl.REPO_ROOT = old_root

    row = conn.execute(
        "SELECT audio_key, duration_s, source_hash, voice, cues_json "
        "FROM chapter_narration WHERE slug='test-book' AND anchor_key='one'"
    ).fetchone()
    assert row[0] == "test-book/narration/one.mp3"
    assert row[1] == 12.5
    assert row[2] == "abc"
    assert row[3] == "aria"
    assert '"blockIndex": 0' in row[4]
    assert '"text"' not in row[4]
    assert conn.execute("SELECT kind FROM media_asset WHERE key='test-book/narration/one.mp3'").fetchone()[0] == "audio"


def test_chapter_narration_publish_key_is_url_safe(tmp_path):
    book = a_book(tmp_path)
    book.chapters[0].anchor = "the persian who was dead and revived"
    audio = tmp_path / "book" / "narration" / "the persian who was dead and revived.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"MP3")
    (tmp_path / "book" / "narration" / "manifest.json").write_text(
        json.dumps(
            {
                "chapters": {
                    "the persian who was dead and revived": {
                        "audio": "book/narration/the persian who was dead and revived.mp3",
                        "duration_s": 12.5,
                        "source_hash": "abc",
                        "voice": "aria",
                        "cues": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    collect_reader_narration(book)

    assert book.assets[0].key == "test-book/narration/the-persian-who-was-dead-and-revived.mp3"
    assert book.chapters[0].narration is not None
    assert book.chapters[0].narration.audio.key == book.assets[0].key


def test_sessions_are_rewritten_so_a_renumbered_folder_leaves_no_stale_row(tmp_path):
    """Renaming `Session 4 — ...` to `Session 1 — ...` must not leave both."""
    conn = db_with_schema()
    book = a_book(tmp_path)
    book.sessions.append(Session(number=4, title="The Treatise"))
    conn.executescript(build_sql(book, published_at="x", commit=None))

    book.sessions = [Session(number=1, title="The Treatise")]
    conn.executescript(build_sql(book, published_at="x", commit=None))

    assert [r[0] for r in conn.execute("SELECT number FROM book_session")] == [1]


# ---------------------------------------------------------------------------
# The two answers about sessions
# ---------------------------------------------------------------------------


def test_a_lone_session_numbered_from_the_source_index_is_reported(tmp_path):
    """The live defect, caught at its source.

    Six episodes under one folder called `Session 4` rendered as a session
    numbered 4 with no 1, 2 or 3 above it — which reads to a reader as a book
    missing three of its parts.
    """
    book = a_book(tmp_path)
    book.sessions.append(Session(number=4, title="The Treatise"))

    concerns = session_concerns(book)

    assert len(concerns) == 1
    assert "numbered [4]" in concerns[0]


def test_contiguous_sessions_are_silent(tmp_path):
    book = a_book(tmp_path)
    book.sessions = [Session(number=n, title=f"Part {n}") for n in (1, 2, 3)]
    assert session_concerns(book) == []


def test_a_flat_book_is_silent(tmp_path):
    """Most books are flat by design and that is not a fault."""
    assert session_concerns(a_book(tmp_path)) == []


def test_a_derived_grouping_with_no_folders_is_reported(tmp_path):
    """The other half of the disagreement: the plan says this book has parts and
    the author never arranged the recordings into them, so it publishes flat and
    the grouping is silently lost."""
    book = a_book(tmp_path)
    toc = tmp_path / "_system" / "source" / "text" / "_chunks" / "0d"
    toc.mkdir(parents=True)
    (toc / "source-toc.json").write_text(
        """{"source_chapters": [
             {"sc_index": 1, "source_title": "Part One — Beginnings", "episode_count": 5,
              "episodes": [{"ep_num": 1}, {"ep_num": 2}, {"ep_num": 3}, {"ep_num": 4}, {"ep_num": 5}]},
             {"sc_index": 2, "source_title": "Part Two — Endings", "episode_count": 5,
              "episodes": [{"ep_num": 6}, {"ep_num": 7}, {"ep_num": 8}, {"ep_num": 9}, {"ep_num": 10}]}
           ]}""",
        encoding="utf-8",
    )

    concerns = session_concerns(book)

    assert len(concerns) == 1
    assert "publishes flat" in concerns[0]
    assert "Beginnings" in concerns[0]


def test_the_report_never_blocks_a_book_from_shipping(tmp_path):
    """It is a report, like `unmatched_audio`. A book with a disagreement still
    produces valid SQL and still publishes — the alternative is a gate that stops
    a finished podcast reaching anyone over a numbering question."""
    conn = db_with_schema()
    book = a_book(tmp_path)
    book.sessions.append(Session(number=9, title="Out of nowhere"))

    assert session_concerns(book) != []
    conn.executescript(build_sql(book, published_at="x", commit=None))
    assert conn.execute("SELECT count(*) FROM book_session").fetchone()[0] == 1


def test_remote_batches_preserve_order_and_stay_bounded():
    statements = ["SELECT 1;", "SELECT '" + ("x" * 20) + "';", "SELECT 3;"]

    batches = remote_batches(statements, max_bytes=25)

    assert "\n".join(batches).split("\n") == statements
    assert all(len(batch.encode("utf-8")) <= 45 for batch in batches)


def test_execute_batches_local_statements_instead_of_importing_file(tmp_path):
    with mock.patch.object(ptl.subprocess, "run") as run:
        ptl.execute(tmp_path / "book.sql", remote=False, statements=["SELECT 1;"])

    command = run.call_args.args[0]
    assert "--local" in command
    assert "--command" in command
    assert all(not str(part).startswith("--file=") for part in command)
