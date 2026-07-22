"""augment_book.py is unwired from every live caller (verified before touching it —
zero imports anywhere in the pipeline), but it shares the same knowledge.db shape
as the live intelligence/augmenter.py path and was named explicitly in the
narrator-attribution backlog item. Closing the gap here too, so a future wiring
of this module inherits the policy rather than needing to rediscover it.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import augment_book as AB  # noqa: E402


def _fake_db(tmp_path: Path, atoms: list[dict]) -> Path:
    db_path = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE atoms (
            id TEXT PRIMARY KEY, type TEXT, body TEXT,
            tradition TEXT, first_seen_book TEXT, content_level TEXT
        )
    """)
    conn.execute("CREATE TABLE atom_topic_tags (atom_id TEXT, tag TEXT)")
    for a in atoms:
        conn.execute(
            "INSERT INTO atoms (id, type, body, tradition, first_seen_book, content_level) VALUES (?,?,?,?,?,?)",
            (a["id"], a["type"], json.dumps(a["body"], ensure_ascii=False), "universal", "book", None),
        )
    conn.commit()
    conn.close()
    return db_path


def test_a_quote_attributed_to_a_restricted_narrator_never_loads(tmp_path: Path, monkeypatch) -> None:
    db_path = _fake_db(
        tmp_path,
        [
            {
                "id": "quote:umar:x",
                "type": "quote",
                "body": {"speaker": "Umar", "text_en": "excluded quote text"},
            },
            {
                "id": "quote:ali:y",
                "type": "quote",
                "body": {"speaker": "Imam Ali", "text_en": "approved quote text"},
            },
        ],
    )
    monkeypatch.setattr(AB, "KB_PATH", db_path)

    atoms = AB._load_atoms()

    ids = {a["id"] for a in atoms}
    assert "quote:ali:y" in ids
    assert "quote:umar:x" not in ids


def test_a_hadith_with_a_restricted_narrator_never_loads(tmp_path: Path, monkeypatch) -> None:
    db_path = _fake_db(
        tmp_path,
        [{"id": "hadith:x", "type": "hadith", "body": {"narrator": "Aisha", "text_en": "excluded hadith text"}}],
    )
    monkeypatch.setattr(AB, "KB_PATH", db_path)

    assert AB._load_atoms() == []


def test_atoms_with_no_narrator_field_are_unaffected(tmp_path: Path, monkeypatch) -> None:
    db_path = _fake_db(
        tmp_path,
        [{"id": "doctrine:x", "type": "doctrine", "body": {"text_en": "ordinary doctrinal prose"}}],
    )
    monkeypatch.setattr(AB, "KB_PATH", db_path)

    atoms = AB._load_atoms()

    assert len(atoms) == 1
    assert atoms[0]["id"] == "doctrine:x"
