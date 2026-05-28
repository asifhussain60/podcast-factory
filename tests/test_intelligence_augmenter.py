"""tests/test_intelligence_augmenter.py — B3 acceptance tests for the DB-backed augmenter.

Covers:
- augment_episode_text: disabled by default (no meta.yml) → text unchanged
- augment_episode_text: enabled in meta.yml, no atoms in DB → text unchanged
- augment_episode_text: enabled, matching atoms → block prepended
- augment_episode_text: Arabic script stripped from injected block (DR-012)
- fetch_atoms_for_tags: empty tags → empty list
- fetch_atoms_for_tags: tags with no match → empty list
- fetch_atoms_for_tags: tags match doctrine atom → returned
- fetch_atoms_for_tags: needs_review=1 atom excluded (not in atoms table without needs_review column)
- fetch_atoms_for_tags: max_atoms limit respected
- _build_context_block: contains header and source attribution
- _strip_arabic: removes Arabic characters
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
from intelligence.augmenter import (
    augment_episode_text,
    fetch_atoms_for_tags,
    _build_context_block,
    _strip_arabic,
    _augmentation_enabled,
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


def _insert_doctrine_atom(conn, atom_id: str, text_en: str, tag: str,
                           binder_slug: str = "binder1", chapter_slug: str = "ch01") -> None:
    body = json.dumps({"text_en": text_en, "binder_slug": binder_slug, "chapter_slug": chapter_slug})
    conn.execute(
        "INSERT OR IGNORE INTO atoms (id, type, body, confidence) VALUES (?, 'doctrine', ?, 1.0)",
        (atom_id, body),
    )
    conn.execute(
        "INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)",
        (atom_id, tag),
    )
    conn.commit()


def _meta_yml(book_dir: Path, enabled: bool = True, tags: list | None = None) -> None:
    """Write a minimal meta.yml to enable/disable augmentation."""
    book_dir.mkdir(parents=True, exist_ok=True)
    lines = ["series:"]
    lines.append(f"  enable_knowledge_augmenter: {'true' if enabled else 'false'}")
    if tags:
        lines.append("knowledge_tags:")
        for t in tags:
            lines.append(f"  - {t}")
    (book_dir / "meta.yml").write_text("\n".join(lines) + "\n")


# ─── unit tests ───────────────────────────────────────────────────────────────

def test_strip_arabic_removes_arabic():
    result = _strip_arabic("Hello \u0628\u0633\u0645 world")
    assert "\u0628\u0633\u0645" not in result
    assert "Hello" in result
    assert "world" in result


def test_strip_arabic_clean_text_unchanged():
    text = "The soul is perfect"
    assert _strip_arabic(text) == text


def test_build_context_block_contains_header():
    atoms = [{"id": "doctrine:wisdom:b1:ch01:0", "body": {"text_en": "Doctrine text.", "binder_slug": "b1", "chapter_slug": "ch01"}}]
    block = _build_context_block(atoms)
    assert "[PRIOR DOCTRINAL CONTEXT" in block
    assert "Doctrine text." in block


def test_build_context_block_contains_source():
    atoms = [{"id": "doctrine:wisdom:b1:ch01:0", "body": {"text_en": "test", "binder_slug": "binder1", "chapter_slug": "ch01"}}]
    block = _build_context_block(atoms)
    assert "Kashkole" in block
    assert "binder1" in block


def test_build_context_block_skips_empty_text():
    atoms = [{"id": "doctrine:wisdom:b1:ch01:0", "body": {"text_en": "", "binder_slug": "b1"}}]
    block = _build_context_block(atoms)
    # Block is just the header with nothing meaningful
    assert "Source:" not in block


# ─── augmentation_enabled tests ──────────────────────────────────────────────

def test_augmentation_disabled_by_default(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    book_dir.mkdir()
    # No meta.yml → default False
    assert _augmentation_enabled(book_dir) is False


def test_augmentation_enabled_via_meta_yml(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    _meta_yml(book_dir, enabled=True)
    assert _augmentation_enabled(book_dir) is True


def test_augmentation_disabled_via_meta_yml(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    _meta_yml(book_dir, enabled=False)
    assert _augmentation_enabled(book_dir) is False


# ─── fetch_atoms_for_tags tests ───────────────────────────────────────────────

def test_fetch_atoms_empty_tags(isolated_db):
    atoms = fetch_atoms_for_tags([])
    assert atoms == []


def test_fetch_atoms_no_match(isolated_db):
    atoms = fetch_atoms_for_tags(["nonexistent-tag"])
    assert atoms == []


def test_fetch_atoms_matches_doctrine_atom(isolated_db):
    conn = get_connection()
    _insert_doctrine_atom(conn, "doctrine:wisdom:b1:ch01:0", "Allah is One.", "tawhid")
    atoms = fetch_atoms_for_tags(["tawhid"])
    assert len(atoms) == 1
    assert atoms[0]["id"] == "doctrine:wisdom:b1:ch01:0"


def test_fetch_atoms_max_limit_respected(isolated_db):
    conn = get_connection()
    for i in range(5):
        _insert_doctrine_atom(conn, f"doctrine:wisdom:b1:ch0{i}:0", f"Text {i}", "ethics")
    atoms = fetch_atoms_for_tags(["ethics"], max_atoms=3)
    assert len(atoms) == 3


def test_fetch_atoms_only_doctrine_type(isolated_db):
    conn = get_connection()
    # Insert a quran atom with the same tag — should NOT appear in results
    conn.execute(
        "INSERT OR IGNORE INTO atoms (id, type, body, confidence) VALUES (?, 'quran', ?, 1.0)",
        ("quran:2:255", json.dumps({"surah": 2, "ayah": 255, "text_en": "Ayat al-Kursi"})),
    )
    conn.execute("INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)", ("quran:2:255", "tawhid"))
    _insert_doctrine_atom(conn, "doctrine:wisdom:b1:ch01:0", "Doctrine of Oneness", "tawhid")
    conn.commit()
    atoms = fetch_atoms_for_tags(["tawhid"])
    ids = [a["id"] for a in atoms]
    assert "quran:2:255" not in ids
    assert "doctrine:wisdom:b1:ch01:0" in ids


# ─── augment_episode_text integration tests ───────────────────────────────────

def test_augment_text_disabled_returns_original(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    book_dir.mkdir()
    original = "Episode text here."
    result = augment_episode_text(original, book_dir, ["tawhid"])
    assert result == original


def test_augment_text_no_atoms_returns_original(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    _meta_yml(book_dir, enabled=True)
    original = "Episode text here."
    result = augment_episode_text(original, book_dir, ["tawhid"])
    assert result == original


def test_augment_text_with_atoms_prepends_block(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    _meta_yml(book_dir, enabled=True)
    conn = get_connection()
    _insert_doctrine_atom(conn, "doctrine:wisdom:b1:ch01:0", "The soul is eternal.", "eschatology")
    result = augment_episode_text("Episode.", book_dir, ["eschatology"])
    assert "[PRIOR DOCTRINAL CONTEXT" in result
    assert "The soul is eternal." in result
    assert result.endswith("Episode.")


def test_augment_text_arabic_stripped(tmp_path, isolated_db):
    book_dir = tmp_path / "my-book"
    _meta_yml(book_dir, enabled=True)
    conn = get_connection()
    _insert_doctrine_atom(conn, "doctrine:wisdom:b1:ch01:0", "\u0627\u0644\u0644\u0647 is One.", "tawhid")
    result = augment_episode_text("Episode.", book_dir, ["tawhid"])
    assert "\u0627\u0644\u0644\u0647" not in result
    assert "is One." in result
