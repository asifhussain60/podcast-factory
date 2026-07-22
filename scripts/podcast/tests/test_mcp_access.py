"""Tests for intelligence/mcp_access.py — the pipeline-safe knowledge access layer.

The module's core contract is "never raises": every wrapper returns a typed
result or a safe empty value even when the underlying source-library query
throws (mirror missing, OrbStack down). All underlying query functions are
patched in the mcp_access namespace — no SQLite mirror, no docker, $0 cost.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.podcast.intelligence import mcp_access as ma


# ---------------------------------------------------------------- pattern 1: citation verify
def test_verify_quran_citation_returns_record():
    verse = {"surah": 14, "ayat": 7, "arabic": "...", "pickthall": "If ye give thanks..."}
    with mock.patch.object(ma, "quran_lookup", return_value=verse) as q:
        assert ma.verify_quran_citation("14", "7") == verse
    q.assert_called_once_with(14, 7)  # coerced to ints


def test_verify_quran_citation_error_and_exception_return_none():
    with mock.patch.object(ma, "quran_lookup", return_value={"error": "no such verse"}):
        assert ma.verify_quran_citation(999, 1) is None
    with mock.patch.object(ma, "quran_lookup", side_effect=RuntimeError("mirror down")):
        assert ma.verify_quran_citation(1, 1) is None


# ---------------------------------------------------------------- pattern 2: concept search
def test_search_quran_by_concept_strips_and_passes_limit():
    hits = [{"surah": 2, "ayat": 255}]
    with mock.patch.object(ma, "quran_theme_search", return_value=hits) as q:
        assert ma.search_quran_by_concept("  gratitude ", limit=2) == hits
    q.assert_called_once_with("gratitude", limit=2)


def test_search_quran_by_concept_never_raises():
    with mock.patch.object(ma, "quran_theme_search", side_effect=OSError("docker exec failed")):
        assert ma.search_quran_by_concept("gratitude") == []


# ---------------------------------------------------------------- pattern 3: hadith
def test_find_hadith_passes_through_and_never_raises():
    hits = [{"hadith_id": 5, "english": "Actions are by intentions"}]
    with mock.patch.object(ma, "hadith_lookup", return_value=hits) as q:
        assert ma.find_hadith(" intentions ", limit=1) == hits
    q.assert_called_once_with("intentions", limit=1)
    with mock.patch.object(ma, "hadith_lookup", side_effect=Exception("boom")):
        assert ma.find_hadith("intentions") == []


# ---------------------------------------------------------------- pattern 4: etymology
def test_get_etymology_error_and_exception_return_none():
    record = {"root": {"letters": "w-l-y"}, "derivatives": [], "source": "mirror"}
    with mock.patch.object(ma, "word_etymology", return_value=record):
        assert ma.get_etymology(" wilaya ") == record
    with mock.patch.object(ma, "word_etymology", return_value={"error": "not found"}):
        assert ma.get_etymology("xyzzy") is None
    with mock.patch.object(ma, "word_etymology", side_effect=RuntimeError):
        assert ma.get_etymology("wilaya") is None


# ---------------------------------------------------------------- pattern 5: style reference
def test_get_style_reference_forwards_group_id():
    passages = [{"session_id": 3, "passage": "..."}]
    with mock.patch.object(ma, "session_style_fetch", return_value=passages) as q:
        assert ma.get_style_reference("patience", group_id=7, limit=2) == passages
    q.assert_called_once_with("patience", group_id=7, limit=2)
    with mock.patch.object(ma, "session_style_fetch", side_effect=Exception):
        assert ma.get_style_reference("patience") == []


# ---------------------------------------------------------------- pattern 6: doctrine context
_TOPICS = [
    {"topic_id": 1, "topic_type_id": 17, "name": "hadith A"},  # prophetic hadith
    {"topic_id": 2, "topic_type_id": 31, "name": "poem"},  # manqabat
    {"topic_id": 3, "topic_type_id": None, "name": "sql-fallback row"},  # no type col
    {"topic_id": 4, "topic_type_id": 23, "name": "hadith commentary"},
]


def test_doctrine_context_filters_by_type_ids_and_keeps_untyped_rows():
    with mock.patch.object(ma, "topic_search", return_value=list(_TOPICS)):
        out = ma.get_doctrine_context("wilaya", type_ids=ma.HADITH_TYPE_IDS, limit=5)
    assert [t["topic_id"] for t in out] == [1, 3, 4]  # poem filtered; untyped kept


def test_doctrine_context_default_is_unfiltered_and_respects_limit():
    with mock.patch.object(ma, "topic_search", return_value=list(_TOPICS)) as q:
        out = ma.get_doctrine_context("wilaya", limit=2)
    assert [t["topic_id"] for t in out] == [1, 2]
    q.assert_called_once_with("wilaya", limit=6)  # over-fetches 3x for filtering


def test_doctrine_context_empty_and_exception_return_empty():
    with mock.patch.object(ma, "topic_search", return_value=[]):
        assert ma.get_doctrine_context("wilaya") == []
    with mock.patch.object(ma, "topic_search", side_effect=Exception("no mirror")):
        assert ma.get_doctrine_context("wilaya") == []


# ---------------------------------------------------------------- doctrine topic by id
def test_get_doctrine_topic_success_and_error():
    full = {"topic": {"topic_id": 9}, "ayats": [{"surah": 1, "ayat": 5}], "glossary": []}
    with mock.patch.object(ma, "topic_get", return_value=full):
        assert ma.get_doctrine_topic(9) == full
    with mock.patch.object(ma, "topic_get", return_value={"error": "not found"}):
        assert ma.get_doctrine_topic(999) is None


def _mirror_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE fts_topics (topic_id, topic_type_id, name, name_en, description, binder, chapter, body_plain)"
    )
    conn.execute("INSERT INTO fts_topics VALUES (42, 18, 'نصیحت', 'Counsel', 'desc', 'binder-1', 'ch-2', 'body text')")
    conn.commit()
    return conn


def test_get_doctrine_topic_falls_back_to_mirror_when_sql_raises():
    with (
        mock.patch.object(ma, "topic_get", side_effect=RuntimeError("OrbStack down")),
        mock.patch.object(ma, "open_mirror", return_value=_mirror_conn()),
    ):
        out = ma.get_doctrine_topic(42)
    assert out is not None
    assert out["topic"]["topic_id"] == 42
    assert out["topic"]["name_en"] == "Counsel"
    assert out["ayats"] == []  # docstring: not available without SQL Server


def test_get_doctrine_topic_mirror_miss_or_absent_returns_none():
    with (
        mock.patch.object(ma, "topic_get", side_effect=RuntimeError),
        mock.patch.object(ma, "open_mirror", return_value=_mirror_conn()),
    ):
        assert ma.get_doctrine_topic(777) is None  # no such row
    with (
        mock.patch.object(ma, "topic_get", side_effect=RuntimeError),
        mock.patch.object(ma, "open_mirror", return_value=None),
    ):
        assert ma.get_doctrine_topic(42) is None  # no mirror at all
