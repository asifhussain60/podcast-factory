"""_db.py — SQLite connection and migration runner for podcast-factory.

Single source of truth for all database access. Callers MUST obtain their
connection through ``get_connection()`` — never open the database file
directly. WAL mode is enabled once at connection time and persists for the
lifetime of the process.

USAGE

    from _db import get_connection, run_migrations

    # On startup (idempotent — safe to call on every run):
    run_migrations()

    # All other access:
    conn = get_connection()
    rows = conn.execute("SELECT id FROM atoms WHERE type = ?", ("quran",)).fetchall()

REPOSITORY HELPERS

    atoms_repository(conn)
    atom_sources_repository(conn)
    atom_topic_tags_repository(conn)
    corpus_chapters_repository(conn)
    external_corpora_repository(conn)
    manual_review_queue_repository(conn)
    run_telemetry_repository(conn)

Each helper returns a small namespace of callables bound to ``conn``. They
are intentionally thin — complex queries belong in their caller, not here.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_SCHEMA_DIR = _HERE / "schema"
_DB_PATH = _REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"

# ---------------------------------------------------------------------------
# Connection singleton
# ---------------------------------------------------------------------------

_conn: sqlite3.Connection | None = None


def get_connection(*, db_path: Path | None = None) -> sqlite3.Connection:
    """Return the open WAL-mode connection, opening it on first call.

    The optional *db_path* override is used in tests to point at a
    temporary in-memory or file-based database. In production code, omit
    it — the canonical ``content/knowledge-base/knowledge.db`` is used.
    """
    global _conn
    if _conn is not None:
        return _conn
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    _conn = conn
    return conn


def _reset_connection() -> None:
    """Close and clear the singleton — used in tests only."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

def run_migrations(*, db_path: Path | None = None) -> list[str]:
    """Apply pending schema SQL files in lexicographic order.

    Idempotent: files already recorded in ``schema_migrations`` are skipped.
    Returns the list of filenames that were applied in this call.

    The function bootstraps ``schema_migrations`` itself so it is safe to
    call on a brand-new database.
    """
    conn = get_connection(db_path=db_path)
    # Bootstrap the tracking table before querying it.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(filename TEXT PRIMARY KEY, "
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))"
    )
    conn.commit()

    already_applied: set[str] = {
        row[0]
        for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()
    }

    sql_files = sorted(_SCHEMA_DIR.glob("*.sql"))
    applied: list[str] = []
    for sql_file in sql_files:
        name = sql_file.name
        if name in already_applied:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (filename) VALUES (?)", (name,)
        )
        conn.commit()
        applied.append(name)

    return applied


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------

def atoms_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``atoms`` table."""

    def get(atom_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM atoms WHERE id = ?", (atom_id,)).fetchone()

    def upsert(
        atom_id: str,
        atom_type: str,
        body: str,
        *,
        first_seen_book: str | None = None,
        first_seen_chapter: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        conn.execute(
            """
            INSERT INTO atoms (id, type, body, first_seen_book, first_seen_chapter, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                body             = excluded.body,
                confidence       = excluded.confidence,
                updated_at       = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            """,
            (atom_id, atom_type, body, first_seen_book, first_seen_chapter, confidence),
        )
        conn.commit()

    def list_by_type(atom_type: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM atoms WHERE type = ? ORDER BY id", (atom_type,)
        ).fetchall()

    def count() -> int:
        return conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]

    return SimpleNamespace(get=get, upsert=upsert, list_by_type=list_by_type, count=count)


def atom_sources_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``atoms_sources`` table."""

    def add(
        atom_id: str,
        book_slug: str,
        chapter_id: str | None = None,
        locator: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id, locator)
            VALUES (?, ?, ?, ?)
            """,
            (atom_id, book_slug, chapter_id, locator),
        )
        conn.commit()

    def list_for_atom(atom_id: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM atoms_sources WHERE atom_id = ? ORDER BY book_slug",
            (atom_id,),
        ).fetchall()

    def list_for_book(book_slug: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM atoms_sources WHERE book_slug = ? ORDER BY atom_id",
            (book_slug,),
        ).fetchall()

    return SimpleNamespace(add=add, list_for_atom=list_for_atom, list_for_book=list_for_book)


def atom_topic_tags_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``atom_topic_tags`` table."""

    def tag(atom_id: str, tag_value: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)",
            (atom_id, tag_value),
        )
        conn.commit()

    def tags_for(atom_id: str) -> list[str]:
        return [
            row[0]
            for row in conn.execute(
                "SELECT tag FROM atom_topic_tags WHERE atom_id = ? ORDER BY tag",
                (atom_id,),
            ).fetchall()
        ]

    def atoms_for_tag(tag_value: str) -> list[str]:
        return [
            row[0]
            for row in conn.execute(
                "SELECT atom_id FROM atom_topic_tags WHERE tag = ? ORDER BY atom_id",
                (tag_value,),
            ).fetchall()
        ]

    return SimpleNamespace(tag=tag, tags_for=tags_for, atoms_for_tag=atoms_for_tag)


def corpus_chapters_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``corpus_chapters`` table."""

    def get(chapter_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM corpus_chapters WHERE id = ?", (chapter_id,)
        ).fetchone()

    def list_for_corpus(corpus_id: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM corpus_chapters WHERE corpus_id = ? ORDER BY number",
            (corpus_id,),
        ).fetchall()

    def upsert(
        chapter_id: str,
        corpus_id: str,
        *,
        number: int | None = None,
        title_en: str | None = None,
        title_ar: str | None = None,
        verse_count: int | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO corpus_chapters (id, corpus_id, number, title_en, title_ar, verse_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                number     = excluded.number,
                title_en   = excluded.title_en,
                title_ar   = excluded.title_ar,
                verse_count = excluded.verse_count
            """,
            (chapter_id, corpus_id, number, title_en, title_ar, verse_count),
        )
        conn.commit()

    return SimpleNamespace(get=get, list_for_corpus=list_for_corpus, upsert=upsert)


def external_corpora_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``external_corpora`` table."""

    def get(corpus_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM external_corpora WHERE id = ?", (corpus_id,)
        ).fetchone()

    def list_all() -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM external_corpora ORDER BY id"
        ).fetchall()

    def upsert(
        corpus_id: str,
        display_name: str,
        corpus_type: str,
        *,
        atom_count: int = 0,
        last_synced: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO external_corpora (id, display_name, corpus_type, atom_count, last_synced)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                corpus_type  = excluded.corpus_type,
                atom_count   = excluded.atom_count,
                last_synced  = excluded.last_synced
            """,
            (corpus_id, display_name, corpus_type, atom_count, last_synced),
        )
        conn.commit()

    return SimpleNamespace(get=get, list_all=list_all, upsert=upsert)


def manual_review_queue_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``manual_review_queue`` table."""

    def enqueue(
        book_slug: str,
        reason: str,
        *,
        chapter_id: str | None = None,
        payload: str | None = None,
    ) -> int:
        cur = conn.execute(
            """
            INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)
            VALUES (?, ?, ?, ?)
            """,
            (book_slug, chapter_id, reason, payload),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def pending(book_slug: str | None = None) -> list[sqlite3.Row]:
        if book_slug:
            return conn.execute(
                "SELECT * FROM manual_review_queue WHERE resolved_at IS NULL AND book_slug = ?"
                " ORDER BY created_at",
                (book_slug,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM manual_review_queue WHERE resolved_at IS NULL ORDER BY created_at"
        ).fetchall()

    def resolve(row_id: int, resolution: str) -> None:
        conn.execute(
            """
            UPDATE manual_review_queue
            SET resolved_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
                resolution  = ?
            WHERE id = ?
            """,
            (resolution, row_id),
        )
        conn.commit()

    return SimpleNamespace(enqueue=enqueue, pending=pending, resolve=resolve)


def run_telemetry_repository(conn: sqlite3.Connection) -> SimpleNamespace:
    """Thin access helpers for the ``run_telemetry`` table."""

    def start_run(
        run_id: str,
        book_slug: str,
        phase: str,
        started_at: str,
    ) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO run_telemetry (run_id, book_slug, phase, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, book_slug, phase, started_at),
        )
        conn.commit()

    def complete_run(
        run_id: str,
        finished_at: str,
        *,
        cost_usd: float = 0.0,
        atoms_extracted: int = 0,
        status: str = "completed",
    ) -> None:
        conn.execute(
            """
            UPDATE run_telemetry
            SET finished_at     = ?,
                cost_usd        = ?,
                atoms_extracted = ?,
                status          = ?
            WHERE run_id = ?
            """,
            (finished_at, cost_usd, atoms_extracted, status, run_id),
        )
        conn.commit()

    def total_cost(book_slug: str) -> float:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) FROM run_telemetry WHERE book_slug = ?",
            (book_slug,),
        ).fetchone()
        return float(row[0])

    def recent(limit: int = 20) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM run_telemetry ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return SimpleNamespace(
        start_run=start_run,
        complete_run=complete_run,
        total_cost=total_cost,
        recent=recent,
    )
