"""tests/test_db.py — Tests for scripts/podcast/_db.py

Runs against a temporary SQLite database (never the live knowledge.db).
Uses _reset_connection() for isolation between tests.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the podcast scripts dir is importable.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "podcast"
sys.path.insert(0, str(SCRIPTS_DIR))

import _db  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    """Yield a fresh temporary database path and reset the singleton after."""
    db_path = tmp_path / "test_knowledge.db"
    yield db_path
    _db._reset_connection()


# ---------------------------------------------------------------------------
# run_migrations
# ---------------------------------------------------------------------------

def test_run_migrations_applies_all_schemas(tmp_db):
    applied = _db.run_migrations(db_path=tmp_db)
    assert isinstance(applied, list)
    # At least 16 schema files (001–016)
    assert len(applied) >= 16


def test_run_migrations_is_idempotent(tmp_db):
    _db._reset_connection()
    first = _db.run_migrations(db_path=tmp_db)
    _db._reset_connection()
    second = _db.run_migrations(db_path=tmp_db)
    # Second run should apply nothing new
    assert second == []
    # First run found at least 16 files
    assert len(first) >= 16


def test_run_migrations_records_in_schema_migrations_table(tmp_db):
    _db.run_migrations(db_path=tmp_db)
    conn = _db.get_connection(db_path=tmp_db)
    rows = conn.execute(
        "SELECT filename FROM schema_migrations ORDER BY filename"
    ).fetchall()
    filenames = [r[0] for r in rows]
    # Spot-check canonical schema files
    assert any("001" in f for f in filenames)
    assert any("016" in f for f in filenames)


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------

def test_get_connection_returns_singleton(tmp_db):
    _db._reset_connection()
    conn1 = _db.get_connection(db_path=tmp_db)
    conn2 = _db.get_connection(db_path=tmp_db)
    assert conn1 is conn2


def test_get_connection_has_wal_mode(tmp_db):
    _db._reset_connection()
    conn = _db.get_connection(db_path=tmp_db)
    row = conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0].lower() == "wal"


def test_get_connection_has_foreign_keys_on(tmp_db):
    _db._reset_connection()
    conn = _db.get_connection(db_path=tmp_db)
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


# ---------------------------------------------------------------------------
# Repository helpers — basic smoke tests (insert + retrieve)
# ---------------------------------------------------------------------------

def test_atoms_repository_upsert_and_get(tmp_db):
    _db._reset_connection()
    _db.run_migrations(db_path=tmp_db)
    conn = _db.get_connection(db_path=tmp_db)
    repo = _db.atoms_repository(conn)

    repo.upsert(
        "quran:2:255",
        "quran",
        "Allah — there is no deity except Him",
        first_seen_book="test-book",
        confidence=1.0,
    )
    found = repo.get("quran:2:255")
    assert found is not None
    assert found["id"] == "quran:2:255"
    assert found["type"] == "quran"


def test_atoms_repository_count(tmp_db):
    _db._reset_connection()
    _db.run_migrations(db_path=tmp_db)
    conn = _db.get_connection(db_path=tmp_db)
    repo = _db.atoms_repository(conn)
    assert repo.count() == 0
    repo.upsert("hadith:bukhari:1", "hadith", "Actions are judged by intentions")
    assert repo.count() == 1


def test_manual_review_queue_repository_enqueue_and_pending(tmp_db):
    _db._reset_connection()
    _db.run_migrations(db_path=tmp_db)
    conn = _db.get_connection(db_path=tmp_db)
    repo = _db.manual_review_queue_repository(conn)

    row_id = repo.enqueue("test-book", "Duplicate atom detected", chapter_id="ch01")
    assert isinstance(row_id, int)
    items = repo.pending()
    assert len(items) >= 1
    assert items[0]["reason"] == "Duplicate atom detected"
