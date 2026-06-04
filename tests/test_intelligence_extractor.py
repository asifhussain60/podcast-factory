"""tests/test_intelligence_extractor.py — B1 acceptance tests for the atom extractor.

Covers:
- extract_chapter: valid JSON response → atoms list
- extract_chapter: empty atoms response → empty list
- extract_chapter: claude exit code 1 → error field set
- extract_chapter: malformed JSON → error field set
- extract_chapter: markdown-fenced JSON response → parsed correctly
- _build_atom: valid quran raw dict → validated Atom
- _build_atom: valid hadith raw dict → validated Atom
- _build_atom: unknown type → None
- _build_atom: confidence < threshold → needs_review=True
- _build_atom: confidence >= threshold → needs_review=False
- extract_atoms_for_book: no chapters dir → empty summary, scratch file created
- extract_atoms_for_book: chapters dir with 2 txt files → scratch JSONL written
- extract_atoms_for_book: low-confidence atom → flushed to manual_review_queue
- atom_schemas: quran_canonical_id round-trips
- atom_schemas: hadith_canonical_id for "other" collection uses sha256
- atom_schemas: validate_atom raises on missing body fields
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
from intelligence.extractor import (
    ChapterExtractionResult,
    ExtractionSummary,
    _build_atom,
    extract_chapter,
    extract_atoms_for_book,
)
from knowledge._atom_schemas import (
    quran_canonical_id,
    hadith_canonical_id,
    validate_atom,
)


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_knowledge.db"
    monkeypatch.setattr(_db, "_DB_PATH", db_path)
    run_migrations(db_path=db_path)
    _reset_connection()
    yield db_path
    _reset_connection()


def _make_claude_caller(rc: int, payload: dict | None = None, raw_text: str | None = None):
    """Return a fake claude caller that returns the given payload as JSON."""
    def caller(prompt: str) -> tuple[int, str, str]:
        if rc != 0:
            return rc, "", "error"
        text = raw_text if raw_text is not None else json.dumps(payload or {"atoms": []})
        return 0, text, "0.002"
    return caller


# ─── atom schema unit tests ────────────────────────────────────────────────────

def test_quran_canonical_id_round_trips():
    assert quran_canonical_id(2, 255) == "quran:2:255"
    assert quran_canonical_id(1, 1) == "quran:1:1"


def test_quran_canonical_id_out_of_range():
    with pytest.raises(ValueError):
        quran_canonical_id(0, 1)
    with pytest.raises(ValueError):
        quran_canonical_id(115, 1)


def test_hadith_canonical_id_named_collection():
    assert hadith_canonical_id("bukhari", 1) == "hadith:bukhari:1"


def test_hadith_canonical_id_other_uses_sha256():
    cid = hadith_canonical_id("other", 999)
    assert cid.startswith("hadith:other:")
    assert len(cid) > len("hadith:other:")


def test_validate_atom_raises_on_missing_body_fields():
    with pytest.raises(ValueError, match="missing body fields"):
        validate_atom({"id": "quran:2:255", "type": "quran", "body": {}})


def test_validate_atom_raises_on_unknown_type():
    with pytest.raises(ValueError, match="Unknown atom type"):
        validate_atom({"id": "foo:1", "type": "foo", "body": {}})


# ─── _build_atom unit tests ───────────────────────────────────────────────────

def test_build_atom_valid_quran():
    raw = {"type": "quran", "surah": 2, "ayah": 255, "text_en": "Ayat al-Kursi", "confidence": 0.95}
    atom = _build_atom(raw, "test-book", "ch01")
    assert atom is not None
    assert atom["id"] == "quran:2:255"
    assert atom["type"] == "quran"
    assert atom["needs_review"] is False


def test_build_atom_valid_hadith():
    raw = {"type": "hadith", "collection": "bukhari", "number": 1, "text_en": "...", "grade": "sahih", "confidence": 0.9}
    atom = _build_atom(raw, "test-book", "ch01")
    assert atom is not None
    assert atom["id"] == "hadith:bukhari:1"
    assert atom["type"] == "hadith"


def test_build_atom_low_confidence_sets_needs_review():
    raw = {"type": "quran", "surah": 3, "ayah": 7, "text_en": "...", "confidence": 0.5}
    atom = _build_atom(raw, "book", "ch")
    assert atom is not None
    assert atom["needs_review"] is True


def test_build_atom_high_confidence_no_review():
    raw = {"type": "quran", "surah": 3, "ayah": 7, "text_en": "...", "confidence": 0.99}
    atom = _build_atom(raw, "book", "ch")
    assert atom is not None
    assert atom["needs_review"] is False


def test_build_atom_unknown_type_returns_none():
    raw = {"type": "unknown", "text": "something"}
    assert _build_atom(raw, "book", "ch") is None


# ─── extract_chapter tests ────────────────────────────────────────────────────

def test_extract_chapter_valid_response():
    payload = {
        "atoms": [
            {"type": "quran", "surah": 2, "ayah": 255, "text_en": "test", "confidence": 0.9},
        ]
    }
    result = extract_chapter("ch01", "some text", "book", claude_caller=_make_claude_caller(0, payload))
    assert result.error is None
    assert len(result.atoms) == 1
    assert result.atoms[0]["type"] == "quran"


def test_extract_chapter_empty_atoms():
    result = extract_chapter("ch01", "no citations", "book", claude_caller=_make_claude_caller(0, {"atoms": []}))
    assert result.error is None
    assert result.atoms == []


def test_extract_chapter_claude_failure():
    result = extract_chapter("ch01", "text", "book", claude_caller=_make_claude_caller(1))
    assert result.error is not None
    assert result.atoms == []


def test_extract_chapter_malformed_json():
    caller = _make_claude_caller(0, raw_text="not json at all")
    result = extract_chapter("ch01", "text", "book", claude_caller=caller)
    assert result.error is not None


def test_extract_chapter_markdown_fenced_json():
    payload = {"atoms": [{"type": "quran", "surah": 1, "ayah": 1, "text_en": "Al-Fatiha", "confidence": 0.95}]}
    raw_text = "```json\n" + json.dumps(payload) + "\n```"
    result = extract_chapter("ch01", "text", "book", claude_caller=_make_claude_caller(0, raw_text=raw_text))
    assert result.error is None
    assert len(result.atoms) == 1


def test_extract_chapter_cost_parsed():
    payload = {"atoms": []}
    def caller(prompt):
        return 0, json.dumps(payload), "0.042"
    result = extract_chapter("ch01", "text", "book", claude_caller=caller)
    assert abs(result.cost_usd - 0.042) < 0.001


# ─── extract_atoms_for_book tests ─────────────────────────────────────────────

def test_extract_atoms_for_book_no_chapters_dir(tmp_path, isolated_db):
    book_dir = tmp_path / "empty-book"
    book_dir.mkdir()
    caller = _make_claude_caller(0, {"atoms": []})
    summary = extract_atoms_for_book(book_dir, claude_caller=caller)
    assert summary.chapters_processed == 0
    assert summary.scratch_path.exists()


def test_extract_atoms_for_book_writes_scratch_jsonl(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True)
    (chapters_dir / "ch01.txt").write_text("In the name of Allah.")
    (chapters_dir / "ch02.txt").write_text("Another chapter.")

    payload = {
        "atoms": [
            {"type": "quran", "surah": 1, "ayah": 1, "text_en": "bismillah", "confidence": 0.95},
        ]
    }
    caller = _make_claude_caller(0, payload)
    summary = extract_atoms_for_book(book_dir, claude_caller=caller)

    assert summary.chapters_processed == 2
    assert summary.scratch_path.exists()
    lines = [ln for ln in summary.scratch_path.read_text().splitlines() if ln.strip()]
    # 1 atom per chapter × 2 chapters
    assert len(lines) == 2
    atom = json.loads(lines[0])
    assert atom["type"] == "quran"


def test_extract_atoms_for_book_low_confidence_queued(tmp_path, isolated_db):
    book_dir = tmp_path / "review-book"
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True)
    (chapters_dir / "ch01.txt").write_text("A verse.")

    payload = {
        "atoms": [
            {"type": "quran", "surah": 2, "ayah": 1, "text_en": "...", "confidence": 0.3},
        ]
    }
    caller = _make_claude_caller(0, payload)
    summary = extract_atoms_for_book(book_dir, claude_caller=caller)
    assert summary.needs_review_count == 1

    conn = get_connection()
    rows = conn.execute("SELECT payload FROM manual_review_queue").fetchall()
    atom_ids = [json.loads(r[0]).get("atom_id") for r in rows]
    assert "quran:2:1" in atom_ids
