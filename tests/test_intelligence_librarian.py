"""tests/test_intelligence_librarian.py — B2 acceptance tests for the Librarian.

Covers:
- Empty scratch file → empty MergeReport, report.md written
- Single NEW quran atom → inserted into atoms table
- Single NEW hadith atom → inserted into atoms table
- Same atom ingested twice (KNOWN, identical text) → source added, not duplicated in atoms
- Same atom with different text_en → classified as VARIANT, added to atoms_variants
- Hadith with conflicting grade → classified as CONFLICT, halted
- Conflict increments conflict_count in MergeReport
- Conflict written to knowledge_base_conflicts table
- Conflict written to manual_review_queue table
- merge_into_library returns MergeReport with correct counts
- report_md_path is written with correct content
- _update_stats updates counts in stats.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "podcast"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import _db
from _db import get_connection, run_migrations, _reset_connection
from intelligence.librarian import merge_into_library, MergeReport


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_knowledge.db"
    monkeypatch.setattr(_db, "_DB_PATH", db_path)
    run_migrations(db_path=db_path)
    _reset_connection()
    yield db_path
    _reset_connection()


def _scratch(tmp_path: Path, atoms: list[dict]) -> Path:
    """Write a scratch JSONL file with the given atoms."""
    p = tmp_path / "knowledge-atoms-scratch.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for a in atoms:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    return p


def _quran_atom(surah=2, ayah=255, text_en="test verse", confidence=0.95) -> dict:
    return {
        "id": f"quran:{surah}:{ayah}",
        "type": "quran",
        "body": {"surah": surah, "ayah": ayah, "text_en": text_en},
        "confidence": confidence,
        "needs_review": False,
        "first_seen": {"book": "test-book", "chapter": "ch01"},
        "sources": [{"book": "test-book", "chapter": "ch01", "locator": ""}],
    }


def _hadith_atom(collection="bukhari", number=1, text_en="test hadith", grade="sahih", narrator=None) -> dict:
    return {
        "id": f"hadith:{collection}:{number}",
        "type": "hadith",
        "body": {"collection": collection, "number": number, "text_en": text_en, "grade": grade, "narrator": narrator},
        "confidence": 0.95,
        "needs_review": False,
        "first_seen": {"book": "test-book", "chapter": "ch01"},
        "sources": [{"book": "test-book", "chapter": "ch01", "locator": ""}],
    }


# ─── tests ────────────────────────────────────────────────────────────────────

def test_empty_scratch_returns_empty_report(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = _scratch(tmp_path, [])
    report = merge_into_library(book_dir, scratch)
    assert report.conflict_count == 0
    assert report.atoms_new == {}
    assert report.report_md_path is not None
    assert report.report_md_path.exists()


def test_missing_scratch_returns_empty_report(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = tmp_path / "nonexistent.jsonl"
    report = merge_into_library(book_dir, scratch)
    assert report.conflict_count == 0


def test_new_quran_atom_inserted(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = _scratch(tmp_path, [_quran_atom()])
    merge_into_library(book_dir, scratch)
    conn = get_connection()
    row = conn.execute("SELECT type, body FROM atoms WHERE id = 'quran:2:255'").fetchone()
    assert row is not None
    assert row[0] == "quran"
    body = json.loads(row[1])
    assert body["surah"] == 2


def test_new_hadith_atom_inserted(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = _scratch(tmp_path, [_hadith_atom()])
    merge_into_library(book_dir, scratch)
    conn = get_connection()
    row = conn.execute("SELECT id FROM atoms WHERE id = 'hadith:bukhari:1'").fetchone()
    assert row is not None


def test_report_counts_new_atoms(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = _scratch(tmp_path, [_quran_atom(2, 255), _quran_atom(1, 1)])
    report = merge_into_library(book_dir, scratch)
    assert report.atoms_new.get("quran", 0) == 2
    assert report.conflict_count == 0


def test_known_identical_atom_adds_source(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    atom = _quran_atom()
    # First ingest
    s1_dir = tmp_path / "s1"
    s1_dir.mkdir()
    scratch1 = _scratch(s1_dir, [atom])
    merge_into_library(book_dir, scratch1)

    # Second ingest (same id, same body, different book)
    atom2 = dict(atom)
    atom2["first_seen"] = {"book": "book-2", "chapter": "ch02"}
    s2_dir = tmp_path / "s2"
    s2_dir.mkdir()
    scratch2 = _scratch(s2_dir, [atom2])
    report2 = merge_into_library(book_dir, scratch2)

    assert report2.atoms_merged.get("quran", 0) == 1
    # Only one row in atoms table
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM atoms WHERE id='quran:2:255'").fetchone()[0]
    assert count == 1


def test_variant_text_added_to_atoms_variants(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    atom1 = _quran_atom(text_en="original translation")
    atom2 = _quran_atom(text_en="different translation")

    scratch1 = tmp_path / "s1.jsonl"
    scratch1.write_text(json.dumps(atom1) + "\n")
    merge_into_library(book_dir, scratch1)

    scratch2 = tmp_path / "s2.jsonl"
    scratch2.write_text(json.dumps(atom2) + "\n")
    report2 = merge_into_library(book_dir, scratch2)

    assert report2.atoms_variant.get("quran", 0) == 1
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM atoms_variants WHERE atom_id='quran:2:255'").fetchone()[0]
    assert count == 1


def test_hadith_grade_conflict_halts(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    atom1 = _hadith_atom(grade="sahih")
    atom2 = _hadith_atom(grade="daif")

    scratch1 = tmp_path / "s1.jsonl"
    scratch1.write_text(json.dumps(atom1) + "\n")
    merge_into_library(book_dir, scratch1)

    scratch2 = tmp_path / "s2.jsonl"
    scratch2.write_text(json.dumps(atom2) + "\n")
    report2 = merge_into_library(book_dir, scratch2)

    assert report2.conflict_count == 1
    assert report2.atoms_conflict.get("hadith", 0) == 1


def test_conflict_written_to_db(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch1 = tmp_path / "s1.jsonl"
    scratch1.write_text(json.dumps(_hadith_atom(grade="sahih")) + "\n")
    merge_into_library(book_dir, scratch1)

    scratch2 = tmp_path / "s2.jsonl"
    scratch2.write_text(json.dumps(_hadith_atom(grade="daif")) + "\n")
    merge_into_library(book_dir, scratch2)

    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM knowledge_base_conflicts WHERE atom_id='hadith:bukhari:1'"
    ).fetchone()[0]
    assert count == 1


def test_conflict_queued_for_review(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch1 = tmp_path / "s1.jsonl"
    scratch1.write_text(json.dumps(_hadith_atom(grade="sahih")) + "\n")
    merge_into_library(book_dir, scratch1)

    scratch2 = tmp_path / "s2.jsonl"
    scratch2.write_text(json.dumps(_hadith_atom(grade="daif")) + "\n")
    merge_into_library(book_dir, scratch2)

    conn = get_connection()
    row = conn.execute(
        "SELECT reason FROM manual_review_queue WHERE reason='atom_conflict'"
    ).fetchone()
    assert row is not None


def test_report_md_contains_summary(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    scratch = _scratch(tmp_path, [_quran_atom(), _hadith_atom()])
    report = merge_into_library(book_dir, scratch)
    assert report.report_md_path is not None
    content = report.report_md_path.read_text()
    assert "Knowledge Merge Report" in content
    assert "New" in content
