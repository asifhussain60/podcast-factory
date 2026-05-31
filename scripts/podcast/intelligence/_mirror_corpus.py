"""intelligence/_mirror_corpus.py — shared helpers for the mirror-primary corpus importers.

WC1 (update_2026_05_31_mirror_primary): the KQUR / KASHKOLE / KSESSIONS source
databases are now available on disk as the FTS5 mirror at
``content/knowledge-base/mirror.db`` (built earlier by source_library_mirror.py).
These helpers let the per-source importers read that mirror read-only and write
canonical, tradition-stamped, idempotent rows into knowledge.db — no Docker, no
SQL Server, consistent with the machine-agnostic mandate.

Every write here is additive and idempotent:
  * atoms          — INSERT OR IGNORE by canonical id (never overwrites an atom
                     an upstream pipeline already authored) unless ``replace=True``.
  * external_corpora / corpus_chapters — INSERT OR IGNORE + targeted UPDATE.
Re-running an importer produces zero new rows.

Shared contract: each importer exposes ``ingest_all(*, dry_run=False) -> MirrorSummary``
so it slots straight into populate_corpus.SOURCES.
"""
from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # …/scripts/podcast/intelligence
_SCRIPTS = _HERE.parent                           # …/scripts/podcast
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _paths import REPO_ROOT

MIRROR_PATH = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"


@dataclass
class MirrorSummary:
    """Run summary shaped to match the populate_corpus runner's expectations.

    ``total_chapters`` / ``total_atoms_created`` are read by the runner; the
    extra fields make the per-source report legible.
    """

    source: str = ""
    total_chapters: int = 0          # corpus_chapters rows touched
    total_atoms_created: int = 0     # atoms newly inserted (not counting no-op IGNOREs)
    atoms_skipped_existing: int = 0  # canonical id already present — left untouched
    corpora_registered: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def open_mirror_ro() -> sqlite3.Connection | None:
    """Return a read-only connection to mirror.db, or None if it is absent."""
    if not MIRROR_PATH.exists():
        return None
    conn = sqlite3.connect(f"file:{MIRROR_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_corpus(conn, corpus_id: str, display_name: str, corpus_type: str) -> None:
    """Register an external_corpora row idempotently (corpus_type in quran|hadith|scholarly)."""
    conn.execute(
        "INSERT OR IGNORE INTO external_corpora (id, display_name, corpus_type)"
        " VALUES (?, ?, ?)",
        (corpus_id, display_name, corpus_type),
    )


def upsert_chapter(
    conn,
    chapter_id: str,
    corpus_id: str,
    *,
    number: int | None = None,
    title_en: str | None = None,
    title_ar: str | None = None,
    verse_count: int | None = None,
) -> bool:
    """Insert a corpus_chapters row if absent. Returns True if a new row was created."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO corpus_chapters"
        " (id, corpus_id, number, title_en, title_ar, verse_count, ingestion_status, last_ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'ingested', strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
        (chapter_id, corpus_id, number, title_en, title_ar, verse_count),
    )
    return cur.rowcount > 0


def insert_atom(
    conn,
    atom_id: str,
    atom_type: str,
    body: str,
    tradition: str,
    *,
    first_seen_book: str,
    topic_tags: list[str] | None = None,
    replace: bool = False,
) -> bool:
    """Insert one tradition-stamped atom. Returns True if a NEW row was created.

    Default is INSERT OR IGNORE — a canonical id already authored by an upstream
    pipeline is left exactly as-is (non-destructive, D7/never-destroy). Pass
    ``replace=True`` only for sources that are the sole authority for that id.
    """
    if not tradition:
        raise ValueError(f"atom {atom_id} has no tradition — D5 requires every atom stamped")
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    cur = conn.execute(
        f"{verb} INTO atoms"
        " (id, type, body, tradition, first_seen_book, confidence)"
        " VALUES (?, ?, ?, ?, ?, 1.0)",
        (atom_id, atom_type, body, tradition, first_seen_book),
    )
    created = cur.rowcount > 0
    if created:
        for tag in topic_tags or []:
            conn.execute(
                "INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)",
                (atom_id, tag),
            )
    return created


def refresh_corpus_count(conn, corpus_id: str, atom_type: str) -> None:
    """Keep external_corpora.atom_count + last_synced current for one corpus."""
    total = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE type = ?", (atom_type,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE external_corpora"
        " SET atom_count = ?, last_synced = strftime('%Y-%m-%dT%H:%M:%SZ','now')"
        " WHERE id = ?",
        (total, corpus_id),
    )


def ingest_terms(mirror, conn, summary: "MirrorSummary", *, source: str, dry_run: bool) -> None:
    """Shared term_index -> 'term' atom path (used by KQUR and KASHKOLE importers).

    Terms carry their own tradition (D5). Atom id: ``term:<source>:<slug(term)>``.
    """
    import json

    rows = mirror.execute(
        "SELECT term, arabic, root, grammar_tag, definition, etymology, tradition, related"
        " FROM term_index WHERE source = ?",
        (source,),
    ).fetchall()
    for r in rows:
        tradition = (r["tradition"] or "universal").strip() or "universal"
        if dry_run:
            summary.total_atoms_created += 1
            continue
        atom_id = f"term:{source.lower()}:{slugify(r['term'])}"
        body = json.dumps({
            "term": r["term"], "arabic": r["arabic"], "root": r["root"],
            "grammar_tag": r["grammar_tag"], "definition": r["definition"],
            "etymology": r["etymology"], "related": r["related"],
            "source": source, "tradition": tradition,
        }, ensure_ascii=False)
        if insert_atom(conn, atom_id, "term", body, tradition, first_seen_book=source.lower()):
            summary.total_atoms_created += 1
        else:
            summary.atoms_skipped_existing += 1


def slugify(value: str) -> str:
    """Lowercase, keep alnum, collapse the rest into single hyphens."""
    out, prev_dash = [], False
    for ch in value.strip().lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")
