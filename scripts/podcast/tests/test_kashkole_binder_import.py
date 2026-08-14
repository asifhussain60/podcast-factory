#!/usr/bin/env python3
"""Tests for verified Kashkole binder corpus import."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))

import import_kashkole_binder as kbi

_MIRROR_SCHEMA = """
CREATE TABLE fts_topics (
    topic_id INTEGER PRIMARY KEY,
    topic_type_id INTEGER,
    name TEXT,
    name_en TEXT,
    description TEXT,
    binder TEXT,
    chapter TEXT,
    body_plain TEXT
);
CREATE TABLE topic_translation (
    topic_id INTEGER PRIMARY KEY,
    name_en TEXT NOT NULL DEFAULT '',
    body_en TEXT NOT NULL DEFAULT '',
    source_sha TEXT NOT NULL,
    source_chars INTEGER NOT NULL DEFAULT 0,
    output_chars INTEGER NOT NULL DEFAULT 0,
    windows INTEGER NOT NULL DEFAULT 0,
    model TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT '',
    standard_sha TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    translated_at TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'ok',
    concerns TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE fts_quran (
    surah INTEGER,
    ayat INTEGER,
    arabic TEXT,
    pickthall TEXT,
    asad TEXT,
    urdu TEXT,
    phonetic TEXT
);
"""

_KB_SCHEMA = """
CREATE TABLE atoms (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    body TEXT NOT NULL,
    first_seen_book TEXT,
    first_seen_chapter TEXT,
    first_seen_date TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    tradition TEXT NOT NULL DEFAULT 'universal',
    content_level TEXT
);
CREATE TABLE atoms_sources (
    atom_id TEXT NOT NULL,
    book_slug TEXT NOT NULL,
    chapter_id TEXT,
    locator TEXT,
    PRIMARY KEY (atom_id, book_slug, chapter_id)
);
CREATE TABLE atom_topic_tags (
    atom_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (atom_id, tag)
);
CREATE TABLE manual_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_slug TEXT NOT NULL,
    chapter_id TEXT,
    reason TEXT NOT NULL,
    payload TEXT
);
"""


def _mirror() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_MIRROR_SCHEMA)
    return conn


def _kb() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(_KB_SCHEMA)
    return conn


def _add_topic(
    conn: sqlite3.Connection,
    topic_id: int,
    *,
    binder: str = "Quranic Studies",
    status: str | None = "ok",
    body_en: str | None = None,
) -> None:
    source = "Urdu source with Quran marker ⟪quran 1:2⟫"
    rendered = (
        body_en
        if body_en is not None
        else (
            "The Quranic teaching explains hamd as perfected praise rooted in recognition of the Lord. "
            "It links the opening of the Book with worship, gratitude, and divine mercy."
        )
    )
    conn.execute(
        "INSERT INTO fts_topics (topic_id, name, binder, chapter, body_plain) VALUES (?, ?, ?, ?, ?)",
        (topic_id, f"Topic {topic_id}", binder, "Opening", source),
    )
    if status is not None:
        conn.execute(
            """
            INSERT INTO topic_translation
                (topic_id, name_en, body_en, source_sha, source_chars, output_chars,
                 windows, model, prompt_version, standard_sha, run_id, translated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'test', '1.0', 'std', 'run', '2026-08-14', ?)
            """,
            (topic_id, f"Topic {topic_id}", rendered, f"sha-{topic_id}", len(source), len(rendered), status),
        )
    conn.commit()


def test_dry_run_builds_topic_chunks_without_writing() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(mirror, 4664)

    summary = kbi.import_binder("Quranic Studies", mirror_conn=mirror, knowledge_conn=kb)

    assert summary.errors == []
    assert summary.total_topics == 1
    assert summary.eligible_topics == 1
    assert summary.new_atoms == 1
    assert kb.execute("SELECT COUNT(*) FROM atoms").fetchone()[0] == 0


def test_apply_writes_atom_source_tags_and_content_level() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(mirror, 4664)

    summary = kbi.import_binder("Quranic Studies", apply=True, mirror_conn=mirror, knowledge_conn=kb)

    assert summary.new_atoms == 1
    row = kb.execute("SELECT id, body, content_level, tradition FROM atoms").fetchone()
    assert row[0] == "doctrine:kashkole:4664:0"
    assert row[2] == "taveel"
    assert row[3] == "fatimid-ismaili"
    body = json.loads(row[1])
    assert body["source_kind"] == "kashkole_binder_translation"
    assert body["topic_id"] == 4664
    tags = {r[0] for r in kb.execute("SELECT tag FROM atom_topic_tags WHERE atom_id=?", (row[0],))}
    assert {"quranic_taveel", "haqaiq", "kashkole", "topic:4664"} <= tags
    source = kb.execute("SELECT locator FROM atoms_sources WHERE atom_id=?", (row[0],)).fetchone()
    assert source[0] == "topic:4664:chunk:0"


def test_second_apply_is_idempotent_existing_not_new() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(mirror, 4664)

    first = kbi.import_binder("Quranic Studies", apply=True, mirror_conn=mirror, knowledge_conn=kb)
    second = kbi.import_binder("Quranic Studies", apply=True, mirror_conn=mirror, knowledge_conn=kb)

    assert first.new_atoms == 1
    assert second.new_atoms == 0
    assert second.existing_atoms == 1
    assert kb.execute("SELECT COUNT(*) FROM atoms").fetchone()[0] == 1


def test_incomplete_binder_is_blocked_by_default() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(mirror, 4664)
    _add_topic(mirror, 4665, status=None)

    summary = kbi.import_binder("Quranic Studies", mirror_conn=mirror, knowledge_conn=kb)

    assert summary.errors
    assert "not complete" in summary.errors[0]
    assert summary.new_atoms == 0


def test_empty_translated_topic_is_counted_but_not_imported() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(mirror, 4664)
    _add_topic(mirror, 5678, body_en="")

    summary = kbi.import_binder("Quranic Studies", mirror_conn=mirror, knowledge_conn=kb)

    assert summary.errors == []
    assert summary.translated_topics == 2
    assert summary.eligible_topics == 1
    assert summary.empty_topics == 1
    assert summary.new_atoms == 1


def test_near_duplicate_is_queued_not_inserted() -> None:
    mirror = _mirror()
    kb = _kb()
    text = (
        "The Quranic teaching explains hamd as perfected praise rooted in recognition of the Lord. "
        "It links the opening of the Book with worship, gratitude, and divine mercy."
    )
    _add_topic(mirror, 4664, body_en=text)
    kb.execute(
        "INSERT INTO atoms (id, type, body, tradition) VALUES ('doctrine:existing', 'doctrine', ?, 'fatimid-ismaili')",
        (json.dumps({"text_en": text.replace("perfected", "complete")}),),
    )

    summary = kbi.import_binder(
        "Quranic Studies", apply=True, near_threshold=0.50, mirror_conn=mirror, knowledge_conn=kb
    )

    assert summary.new_atoms == 0
    assert summary.near_duplicates >= 1
    assert kb.execute("SELECT COUNT(*) FROM atoms WHERE id='doctrine:kashkole:4664:0'").fetchone()[0] == 0
    queued = kb.execute("SELECT reason, payload FROM manual_review_queue").fetchone()
    assert queued[0] == kbi.REVIEW_REASON
    assert json.loads(queued[1])["candidate_id"] == "doctrine:kashkole:4664:0"


def test_apply_can_hydrate_only_referenced_quran_atoms() -> None:
    mirror = _mirror()
    kb = _kb()
    _add_topic(
        mirror,
        4664,
        body_en=(
            "The teaching points to Quran 7:180, where the beautiful names mark the proper way to call upon Allah."
        ),
    )
    mirror.execute(
        "INSERT INTO fts_quran (surah, ayat, arabic, pickthall, asad, urdu, phonetic) VALUES (7, 180, ?, ?, ?, ?, ?)",
        ("AR", "And Allah's are the fairest names...", "Asad", "Urdu", "phonetic"),
    )

    summary = kbi.import_binder(
        "Quranic Studies", apply=True, hydrate_quran_refs=True, mirror_conn=mirror, knowledge_conn=kb
    )

    assert summary.hydrated_quran_atoms == 1
    assert summary.missing_quran_atoms == []
    quran = kb.execute("SELECT body FROM atoms WHERE id='quran:7:180'").fetchone()
    assert quran is not None
    assert json.loads(quran[0])["text_en"] == "And Allah's are the fairest names..."
