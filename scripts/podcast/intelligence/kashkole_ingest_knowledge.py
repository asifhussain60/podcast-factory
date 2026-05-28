"""intelligence/kashkole_ingest_knowledge.py — Kashkole corpus ingestion driver (B0).

Reads PASS and WARN chapters from the Kashkole extracted corpus and populates
the SQLite knowledge.db with 'doctrine' atoms.  Each adapted-extract.en.md is
split into ≤600-word chunks on section boundaries.  Every chunk becomes one
atom; topic tags come from the 18-row taxonomy in topic-type-map.json.

CLI usage:
    python3 scripts/podcast/intelligence/kashkole_ingest_knowledge.py --status
    python3 scripts/podcast/intelligence/kashkole_ingest_knowledge.py --dry-run
    python3 scripts/podcast/intelligence/kashkole_ingest_knowledge.py --chapter musawwadat/x8114-musawwadat
    python3 scripts/podcast/intelligence/kashkole_ingest_knowledge.py --re-ingest --chapter <binder/chapter>
    python3 scripts/podcast/intelligence/kashkole_ingest_knowledge.py

Python API:
    from intelligence.kashkole_ingest_knowledge import (
        ingest_all, ingest_chapter, print_status, seed_lookup_tables
    )
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- path bootstrap (works when run directly or imported) ---
_HERE = Path(__file__).resolve().parent          # …/scripts/podcast/intelligence
_SCRIPTS = _HERE.parent                          # …/scripts/podcast
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import yaml

from _db import get_connection, run_migrations
from _paths import REPO_ROOT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CORPUS_ROOT = (
    REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted" / "kashkole"
)
TOPIC_MAP_PATH = (
    REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "topic-type-map.json"
)
MAX_CHUNK_WORDS = 600
PASS_WARN = frozenset({"PASS", "WARN"})
_SECTION_RE = re.compile(r"<!--\s*section\s+\d+\s*\(id=(\d+)[^>]*-->")
_QURAN_REF_RE = re.compile(r"⟪quran\s+(\d+:\d+)⟫")
_VERDICT_RE = re.compile(r"\*\*Verdict:\*\*\s*(PASS|WARN|FAIL)")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    binder_slug: str
    chapter_slug: str
    verdict: str
    atoms_created: int = 0
    atoms_skipped: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class IngestSummary:
    total_chapters: int = 0
    ingested: int = 0
    skipped_verdict: int = 0
    skipped_existing: int = 0
    total_atoms_created: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers — file parsing
# ---------------------------------------------------------------------------

def _load_topic_map() -> tuple[dict[str, dict], dict[str, int]]:
    """Return (topic_types, topic_type_assignments) from topic-type-map.json."""
    data = json.loads(TOPIC_MAP_PATH.read_text(encoding="utf-8"))
    return data.get("topic_types", {}), data.get("topic_type_assignments", {})


def _parse_verdict(chapter_dir: Path) -> str | None:
    """Return 'PASS', 'WARN', 'FAIL', or None if the report is absent."""
    report = chapter_dir / "_system" / "source" / "text" / "kashkole-challenger-report.md"
    if not report.exists():
        return None
    m = _VERDICT_RE.search(report.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _parse_bundle(chapter_dir: Path) -> dict[str, Any]:
    """Parse bundle.yml and return a flat dict of metadata."""
    bundle_path = chapter_dir / "bundle.yml"
    if not bundle_path.exists():
        return {}
    data = yaml.safe_load(bundle_path.read_text(encoding="utf-8")) or {}
    shelf = data.get("shelf", {})
    book = data.get("book", {})
    sections_meta = data.get("sections", {})
    items = sections_meta.get("items", []) if isinstance(sections_meta, dict) else []
    section_ids = [s["id"] for s in items if isinstance(s, dict) and "id" in s]
    return {
        "binder_id": shelf.get("id"),
        "binder_slug": shelf.get("slug", ""),
        "binder_name": shelf.get("name", ""),
        "chapter_id": book.get("id"),
        "chapter_slug": book.get("slug", ""),
        "chapter_name": book.get("name", ""),
        "section_ids": section_ids,
    }


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _make_chunk(
    idx: int,
    text_en: str,
    sec_ids: list[int],
    topic_types: dict[str, dict],
    assignments: dict[str, int],
) -> dict:
    tags: list[str] = []
    for sid in sec_ids:
        type_id = assignments.get(str(sid), 0)
        if type_id and str(type_id) in topic_types:
            tag = topic_types[str(type_id)].get("name_en", "")
            if tag and tag != "Unknown" and tag not in tags:
                tags.append(tag)
    return {
        "chunk_index": idx,
        "text_en": text_en.strip(),
        "section_ids": sec_ids,
        "topic_tags": tags,
        "quran_refs": _QURAN_REF_RE.findall(text_en),
    }


def _chunk_text(
    text: str,
    topic_types: dict[str, dict],
    assignments: dict[str, int],
) -> list[dict]:
    """Split adapted extract on section markers; group into ≤MAX_CHUNK_WORDS chunks."""
    parts = _SECTION_RE.split(text)
    # parts: [pre-text, id1, body1, id2, body2, ...]
    raw_sections: list[tuple[int | None, str]] = []
    if parts[0].strip():
        raw_sections.append((None, parts[0]))
    i = 1
    while i + 1 < len(parts):
        raw_sections.append((int(parts[i]), parts[i + 1]))
        i += 2

    chunks: list[dict] = []
    buf_parts: list[str] = []
    buf_ids: list[int] = []
    buf_words = 0
    chunk_idx = 0

    for sec_id, sec_text in raw_sections:
        words = len(sec_text.split())
        if buf_words + words > MAX_CHUNK_WORDS and buf_parts:
            body = "".join(buf_parts).strip()
            if body:
                chunks.append(_make_chunk(chunk_idx, body, buf_ids, topic_types, assignments))
                chunk_idx += 1
            buf_parts, buf_ids, buf_words = [], [], 0
        buf_parts.append(sec_text)
        if sec_id is not None:
            buf_ids.append(sec_id)
        buf_words += words

    if buf_parts:
        body = "".join(buf_parts).strip()
        if body:
            chunks.append(_make_chunk(chunk_idx, body, buf_ids, topic_types, assignments))

    return chunks


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def seed_lookup_tables(conn) -> None:
    """Idempotent: register 'kashkole' in external_corpora."""
    conn.execute(
        "INSERT OR IGNORE INTO external_corpora (id, display_name, corpus_type)"
        " VALUES ('kashkole', 'Kashkole Corpus', 'scholarly')"
    )
    conn.commit()


def _iter_chapter_dirs() -> list[tuple[Path, str, str]]:
    """Yield (chapter_dir, binder_dirname, chapter_dirname) for every chapter."""
    result: list[tuple[Path, str, str]] = []
    if not CORPUS_ROOT.is_dir():
        return result
    for binder_dir in sorted(CORPUS_ROOT.iterdir()):
        if not binder_dir.is_dir():
            continue
        for chapter_dir in sorted(binder_dir.iterdir()):
            if not chapter_dir.is_dir():
                continue
            result.append((chapter_dir, binder_dir.name, chapter_dir.name))
    return result


def _delete_chapter_atoms(conn, binder_id: int, chapter_id: int) -> None:
    """Delete all doctrine atoms for one chapter (for re-ingest)."""
    prefix = f"doctrine:kashkole:{binder_id}:{chapter_id}:%"
    conn.execute("DELETE FROM atoms WHERE id LIKE ?", (prefix,))
    conn.commit()


# ---------------------------------------------------------------------------
# Core ingest
# ---------------------------------------------------------------------------

def _ingest_chapter_dir(
    chapter_dir: Path,
    *,
    re_ingest: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    bundle = _parse_bundle(chapter_dir)
    if not bundle:
        return IngestResult("?", "?", "UNKNOWN", error=f"No bundle.yml in {chapter_dir}")

    binder_slug = bundle["binder_slug"]
    chapter_slug = bundle["chapter_slug"]
    binder_id = bundle.get("binder_id")
    chapter_id = bundle.get("chapter_id")
    if not binder_id or not chapter_id:
        return IngestResult(binder_slug, chapter_slug, "UNKNOWN",
                            error="Missing binder_id or chapter_id")

    verdict = _parse_verdict(chapter_dir) or "UNKNOWN"
    if verdict not in PASS_WARN:
        return IngestResult(binder_slug, chapter_slug, verdict, atoms_skipped=1)

    adapted = chapter_dir / "_system" / "source" / "text" / "adapted-extract.en.md"
    if not adapted.exists():
        return IngestResult(binder_slug, chapter_slug, verdict,
                            error="adapted-extract.en.md not found")

    topic_types, assignments = _load_topic_map()
    chunks = _chunk_text(adapted.read_text(encoding="utf-8"), topic_types, assignments)

    if dry_run:
        return IngestResult(binder_slug, chapter_slug, verdict, atoms_created=len(chunks))

    conn = get_connection()
    prefix = f"doctrine:kashkole:{binder_id}:{chapter_id}:%"
    existing = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE id LIKE ?", (prefix,)
    ).fetchone()[0]

    if existing and not re_ingest:
        return IngestResult(binder_slug, chapter_slug, verdict, atoms_skipped=existing)

    if re_ingest and existing:
        _delete_chapter_atoms(conn, binder_id, chapter_id)

    seed_lookup_tables(conn)

    row_id = f"kashkole:{binder_id}:{chapter_id}"
    conn.execute(
        "INSERT OR IGNORE INTO corpus_chapters (id, corpus_id, number, title_en)"
        " VALUES (?, 'kashkole', ?, ?)",
        (row_id, chapter_id, bundle.get("chapter_name", chapter_slug)),
    )
    needs_review = 1 if verdict == "WARN" else 0
    conn.execute(
        """UPDATE corpus_chapters
           SET ingestion_status = ?,
               verdict          = ?,
               binder_id        = ?,
               chapter_id_num   = ?,
               binder_slug      = ?,
               chapter_slug     = ?,
               needs_review     = ?,
               last_ingested_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
               correction_count = CASE WHEN ? THEN correction_count + 1 ELSE correction_count END
           WHERE id = ?""",
        ("re_ingested" if re_ingest else "ingested",
         verdict, binder_id, chapter_id, binder_slug, chapter_slug,
         needs_review, re_ingest, row_id),
    )

    atoms_created = 0
    for chunk in chunks:
        atom_id = f"doctrine:kashkole:{binder_id}:{chapter_id}:{chunk['chunk_index']}"
        body = json.dumps({
            "tradition": "ismaili",
            "binder_id": binder_id,
            "binder_slug": binder_slug,
            "chapter_id": chapter_id,
            "chapter_slug": chapter_slug,
            "section_ids": chunk["section_ids"],
            "chunk_index": chunk["chunk_index"],
            "topic_tags": chunk["topic_tags"],
            "text_en": chunk["text_en"],
            "quran_refs": chunk["quran_refs"],
        }, ensure_ascii=False)
        conn.execute(
            "INSERT OR REPLACE INTO atoms"
            " (id, type, body, first_seen_book, first_seen_chapter, confidence)"
            " VALUES (?, 'doctrine', ?, 'kashkole', ?, 1.0)",
            (atom_id, body, chapter_slug),
        )
        for tag in chunk["topic_tags"]:
            conn.execute(
                "INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)",
                (atom_id, tag),
            )
        atoms_created += 1

    conn.commit()

    # Keep external_corpora.atom_count current
    total = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE type = 'doctrine'"
    ).fetchone()[0]
    conn.execute(
        "UPDATE external_corpora"
        " SET atom_count = ?, last_synced = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"
        " WHERE id = 'kashkole'",
        (total,),
    )
    conn.commit()

    return IngestResult(binder_slug, chapter_slug, verdict, atoms_created=atoms_created)


def ingest_chapter(
    binder_slug: str,
    chapter_slug: str,
    *,
    re_ingest: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest one Kashkole chapter by its binder and chapter slugs."""
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        b = _parse_bundle(ch_dir)
        if b.get("binder_slug") == binder_slug and b.get("chapter_slug") == chapter_slug:
            return _ingest_chapter_dir(ch_dir, re_ingest=re_ingest, dry_run=dry_run)
    return IngestResult(binder_slug, chapter_slug, "UNKNOWN",
                        error=f"Chapter not found: {binder_slug}/{chapter_slug}")


def ingest_all(
    verdicts: list[str] | None = None,
    *,
    dry_run: bool = False,
) -> IngestSummary:
    """Ingest all chapters whose verdict is in *verdicts* (default PASS+WARN)."""
    allowed = frozenset(verdicts) if verdicts else PASS_WARN
    summary = IngestSummary()
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        summary.total_chapters += 1
        result = _ingest_chapter_dir(ch_dir, dry_run=dry_run)
        if result.verdict not in allowed:
            summary.skipped_verdict += 1
        elif result.error:
            summary.errors.append(f"{result.binder_slug}/{result.chapter_slug}: {result.error}")
        elif result.atoms_skipped and not result.atoms_created:
            summary.skipped_existing += 1
        else:
            summary.ingested += 1
            summary.total_atoms_created += result.atoms_created
    return summary


# ---------------------------------------------------------------------------
# Status table
# ---------------------------------------------------------------------------

def print_status() -> None:
    """Print a table of all Kashkole chapters with ingestion status."""
    conn = get_connection()
    run_migrations()
    seed_lookup_tables(conn)
    cols = f"{'BINDER':<30} {'CHAPTER':<42} {'VERDICT':<8} {'STATUS':<18} {'ATOMS':>6}"
    print(cols)
    print("-" * len(cols))
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        b = _parse_bundle(ch_dir)
        if not b:
            continue
        verdict = _parse_verdict(ch_dir) or "?"
        bs = b.get("binder_slug", "?")
        cs = b.get("chapter_slug", "?")
        bid = b.get("binder_id")
        cid = b.get("chapter_id")
        if bid and cid:
            prefix = f"doctrine:kashkole:{bid}:{cid}:%"
            atom_count = conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE id LIKE ?", (prefix,)
            ).fetchone()[0]
            row = conn.execute(
                "SELECT ingestion_status FROM corpus_chapters WHERE id = ?",
                (f"kashkole:{bid}:{cid}",),
            ).fetchone()
            status = row[0] if row else "pending"
        else:
            atom_count, status = 0, "?"
        print(f"{bs:<30} {cs:<42} {verdict:<8} {status:<18} {atom_count:>6}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    run_migrations()

    parser = argparse.ArgumentParser(description="Kashkole corpus ingestion driver (B0)")
    parser.add_argument("--status", action="store_true",
                        help="Print ingestion status for all chapters")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without writing to the DB")
    parser.add_argument("--chapter", metavar="BINDER/CHAPTER",
                        help="Ingest a single chapter (format: binder_slug/chapter_slug)")
    parser.add_argument("--re-ingest", action="store_true",
                        help="Delete existing atoms and re-ingest from corrected extract")
    parser.add_argument("--force", action="store_true",
                        help="Override FAIL verdict (for manually cleared chapters)")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.chapter:
        parts = args.chapter.split("/", 1)
        if len(parts) != 2:
            print(f"ERROR: --chapter must be binder_slug/chapter_slug, got: {args.chapter}",
                  file=sys.stderr)
            sys.exit(1)
        r = ingest_chapter(parts[0], parts[1],
                           re_ingest=args.re_ingest, dry_run=args.dry_run)
        if r.error:
            print(f"ERROR: {r.error}", file=sys.stderr)
            sys.exit(1)
        flag = " (dry-run)" if args.dry_run else ""
        print(f"{r.binder_slug}/{r.chapter_slug}: verdict={r.verdict}"
              f" atoms_created={r.atoms_created} skipped={r.atoms_skipped}{flag}")
    else:
        summary = ingest_all(dry_run=args.dry_run)
        flag = " (dry-run)" if args.dry_run else ""
        print(f"\nIngestion{flag} complete:")
        print(f"  Total chapters scanned:  {summary.total_chapters}")
        print(f"  Ingested:                {summary.ingested}")
        print(f"  Skipped (verdict):       {summary.skipped_verdict}")
        print(f"  Skipped (already done):  {summary.skipped_existing}")
        print(f"  Atoms created:           {summary.total_atoms_created}")
        if summary.errors:
            print(f"  Errors ({len(summary.errors)}):")
            for e in summary.errors:
                print(f"    - {e}")
