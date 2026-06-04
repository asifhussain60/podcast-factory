"""tests/test_source_library_mirror.py — Wave J (J1): mirror builder + query tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── helpers ────────────────────────────────────────────────────────────────


def _make_mirror(db_path: Path) -> sqlite3.Connection:
    """Create a tiny populated mirror.db for testing (no SQL Server needed)."""
    from scripts.podcast.source_library_mirror import _SCHEMA

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.execute("BEGIN;")
    # Quran: 3 sample verses
    conn.executemany(
        "INSERT INTO fts_quran VALUES (?,?,?,?,?,?,?)",
        [
            (1, 1, "بِسْمِ اللَّهِ", "In the name of Allah", "In Allah's name", "", "bismillah"),
            (1, 2, "الْحَمْدُ لِلَّهِ", "All praise is for Allah", "Praise belongs to Allah", "", "alhamdulillah"),
            (2, 255, "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ", "Allah - there is no deity", "God, there is no god", "", "ayat al-kursi"),
        ],
    )
    # Topics: 2 sample topics
    conn.executemany(
        "INSERT INTO fts_topics VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 0, "التأويل", "Tawil", "Esoteric interpretation", "Binder 1", "Ch 1", "The inner meaning of revelation"),
            (2, 0, "الحقيقة", "Haqiqa", "Spiritual reality", "Binder 1", "Ch 2", "The ultimate truth beyond the apparent"),
        ],
    )
    # Sessions: 1 sample
    conn.execute(
        "INSERT INTO fts_sessions VALUES (?,?,?,?)",
        (101, "Lecture on Tawil", 5, "The inner meaning of the Quran is revealed to the Imam"),
    )
    # term_index: 3 entries
    conn.executemany(
        "INSERT OR IGNORE INTO term_index "
        "(term, arabic, root, grammar_tag, definition, etymology, tradition, source) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            ("tawil", "تأويل", "awl", "noun", "Esoteric interpretation", "From root a-w-l", "ismaili", "KASHKOLE"),
            ("haqiqa", "حقيقة", "hqq", "noun", "Spiritual reality", "From root h-q-q", "ismaili", "KASHKOLE"),
            ("tanzil", "تنزيل", "nzl", "noun", "Exoteric revelation", "From root n-z-l", "ismaili", "KQUR"),
        ],
    )
    conn.execute("COMMIT;")
    conn.close()
    return db_path


# ── schema tests ───────────────────────────────────────────────────────────


def test_schema_creates_all_tables():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        conn = sqlite3.connect(str(db_path))
        from scripts.podcast.source_library_mirror import _SCHEMA
        conn.executescript(_SCHEMA)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','shadow')"
            ).fetchall()
        }
        conn.close()
    assert "term_index" in tables


def test_schema_has_term_index_indexes():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        conn = sqlite3.connect(str(db_path))
        from scripts.podcast.source_library_mirror import _SCHEMA
        conn.executescript(_SCHEMA)
        indexes = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        conn.close()
    assert "idx_term_index_term" in indexes
    assert "idx_term_index_root" in indexes


# ── open_mirror tests ──────────────────────────────────────────────────────


def test_open_mirror_returns_none_when_absent():
    from scripts.podcast.source_library_mirror import open_mirror
    result = open_mirror(Path("/nonexistent/path/mirror.db"))
    assert result is None


def test_open_mirror_returns_connection_when_present():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror
        conn = open_mirror(db_path)
        assert conn is not None
        conn.close()


# ── fts_quran_search tests ─────────────────────────────────────────────────


def test_fts_quran_search_finds_verse():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, fts_quran_search
        conn = open_mirror(db_path)
        results = fts_quran_search("praise", conn=conn)
        conn.close()
    assert len(results) >= 1
    assert any(r["surah"] == 1 for r in results)


def test_fts_quran_search_returns_empty_without_mirror():
    from scripts.podcast.source_library_mirror import fts_quran_search
    results = fts_quran_search("praise", conn=None)
    # No mirror → returns []
    assert results == []


def test_fts_quran_search_respects_limit():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, fts_quran_search
        conn = open_mirror(db_path)
        results = fts_quran_search("Allah", limit=1, conn=conn)
        conn.close()
    assert len(results) <= 1


# ── fts_topics_search tests ────────────────────────────────────────────────


def test_fts_topics_search_finds_topic():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, fts_topics_search
        conn = open_mirror(db_path)
        results = fts_topics_search("esoteric", conn=conn)
        conn.close()
    assert len(results) >= 1
    assert any("Tawil" in r.get("name_en", "") for r in results)


def test_fts_topics_search_returns_empty_without_mirror():
    from scripts.podcast.source_library_mirror import fts_topics_search
    results = fts_topics_search("esoteric", conn=None)
    assert results == []


# ── term_index_lookup tests ────────────────────────────────────────────────


def test_term_index_exact_lookup():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, term_index_lookup
        conn = open_mirror(db_path)
        result = term_index_lookup("tawil", conn=conn)
        conn.close()
    assert result is not None
    assert result["definition"] == "Esoteric interpretation"
    assert result["root"] == "awl"


def test_term_index_prefix_lookup():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, term_index_lookup
        conn = open_mirror(db_path)
        result = term_index_lookup("tan", conn=conn)  # prefix match on "tanzil"
        conn.close()
    assert result is not None
    assert "tanzil" in result["term"]


def test_term_index_returns_none_on_miss():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        from scripts.podcast.source_library_mirror import open_mirror, term_index_lookup
        conn = open_mirror(db_path)
        result = term_index_lookup("zzzznotaword", conn=conn)
        conn.close()
    assert result is None


def test_term_index_lookup_returns_none_without_mirror():
    from scripts.podcast.source_library_mirror import term_index_lookup
    result = term_index_lookup("tawil", conn=None)
    assert result is None


# ── build_mirror dry-run test ──────────────────────────────────────────────


def test_build_mirror_dry_run_does_not_write():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "should-not-exist.db"
        # patch query_json so it doesn't need Docker
        fake_rows = [{"surah": 1, "ayat": 1, "arabic": "", "pickthall": "test",
                      "asad": "", "urdu": "", "phonetic": ""}]
        with patch(
            "scripts.podcast.source_library_mirror.query_json",
            return_value=fake_rows,
        ):
            from scripts.podcast.source_library_mirror import build_mirror
            build_mirror(db_path=db_path, dry_run=True)
        assert not db_path.exists()


# ── queries fallback tests ─────────────────────────────────────────────────


def test_word_etymology_uses_mirror_when_available():
    """word_etymology should return mirror data without touching SQL Server."""
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mirror.db"
        _make_mirror(db_path)
        with patch(
            "scripts.podcast.source_library_mirror.MIRROR_PATH", db_path
        ):
            from importlib import reload
            import scripts.podcast.source_library_mirror as m
            m.MIRROR_PATH = db_path
            from scripts.podcast import source_library_queries as q
            result = q.word_etymology("tawil")
    assert result.get("source") == "mirror"
    assert "root" in result
