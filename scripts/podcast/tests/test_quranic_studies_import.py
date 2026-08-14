#!/usr/bin/env python3
"""Tests for Quranic Studies corpus import scaffolding."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))

import import_quranic_studies as qsi

_SCHEMA = """
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


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA)
    return conn


def test_candidate_loader_normalizes_topics_and_verse_refs(tmp_path: Path) -> None:
    src = tmp_path / "candidates.jsonl"
    src.write_text(
        json.dumps(
            {
                "text_en": "The opening praise teaches that hamd is not casual thanks but the perfected recognition of the Lord.",
                "topics": [" HAMD ", "hamd", "Surah Al-Fateha"],
                "verses": ["Q1:2"],
                "series": "Surah Al-Fateha",
                "session": "008 Perfection Of HAMD",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    candidates, invalid = qsi.load_candidates(src)

    assert invalid == []
    assert len(candidates) == 1
    assert candidates[0].topic_tags == ["hamd", "surah al-fateha"]
    assert candidates[0].quran_refs == ["1:2"]
    assert candidates[0].atom_id.startswith("doctrine:quranic-studies:")


def test_dry_run_collapses_exact_input_duplicates() -> None:
    text = "A Quranic teaching about gratitude links increase to recognition, not merely to receiving more things."
    candidates = [
        qsi.Candidate(text_en=text, topic_tags=["gratitude"], quran_refs=["14:7"]),
        qsi.Candidate(text_en=text, topic_tags=["gratitude"], quran_refs=["14:7"]),
    ]

    summary = qsi.import_candidates(candidates, conn=_conn())

    assert summary.new_atoms == 1
    assert summary.exact_duplicates_in_input == 1
    assert summary.quran_refs == 2
    assert summary.topic_tags == 2


def test_apply_writes_new_atom_tags_and_source() -> None:
    conn = _conn()
    candidate = qsi.Candidate(
        text_en="The basmallah gathers mercy into the opening of action, so the act begins under divine care.",
        topic_tags=["basmallah", "mercy"],
        quran_refs=["1:1"],
        series="Surah Al-Fateha",
        session="005 Complete BASMALLAH",
        source_id="surah-al-fateha/005",
        locator="00:04:00",
    )

    summary = qsi.import_candidates([candidate], apply=True, conn=conn)

    assert summary.new_atoms == 1
    row = conn.execute("SELECT body, first_seen_book FROM atoms WHERE id=?", (candidate.atom_id,)).fetchone()
    assert row is not None
    body = json.loads(row[0])
    assert body["source_kind"] == "quranic_studies"
    assert body["quran_refs"] == ["1:1"]
    assert row[1] == "surah-al-fateha/005"
    tags = {r[0] for r in conn.execute("SELECT tag FROM atom_topic_tags WHERE atom_id=?", (candidate.atom_id,))}
    assert tags == {"basmallah", "mercy"}
    source = conn.execute("SELECT locator FROM atoms_sources WHERE atom_id=?", (candidate.atom_id,)).fetchone()
    assert source[0] == "00:04:00"


def test_near_duplicate_is_queued_for_review_not_inserted() -> None:
    conn = _conn()
    conn.execute(
        "INSERT INTO atoms (id, type, body) VALUES ('doctrine:existing', 'doctrine', ?)",
        (
            json.dumps(
                {
                    "text_en": "The Quranic teaching about gratitude links increase to grateful recognition before receiving more things."
                }
            ),
        ),
    )
    candidate = qsi.Candidate(
        text_en="The Quranic teaching about gratitude links increase to grateful recognition, not merely receiving more things.",
        topic_tags=["gratitude"],
        quran_refs=["14:7"],
        source_id="wise-reminder/014",
    )

    summary = qsi.import_candidates([candidate], apply=True, near_threshold=0.50, conn=conn)

    assert summary.new_atoms == 0
    assert summary.near_duplicates >= 1
    assert conn.execute("SELECT COUNT(*) FROM atoms WHERE id=?", (candidate.atom_id,)).fetchone()[0] == 0
    queued = conn.execute("SELECT reason, payload FROM manual_review_queue").fetchone()
    assert queued[0] == qsi.REVIEW_REASON
    payload = json.loads(queued[1])
    assert payload["candidate_id"] == candidate.atom_id
