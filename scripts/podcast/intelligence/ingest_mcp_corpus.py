"""ingest_mcp_corpus.py — B5: pull hadith, etymology, and poetry atoms into knowledge.db.

Reads from the local SQLite FTS5 mirror (content/knowledge-base/mirror.db)
built by source_library_mirror.py and writes three new atom types into
knowledge.db:

  hadith:kashkole:<topic_id>   — KASHKOLE TypeID 17 (Prophetic Hadith) +
                                   TypeID 23 (Hadith Commentary)
  poetry:kashkole:<topic_id>   — KASHKOLE TypeID 31 (manqabat praise poems)
  etymology:<transliteration>  — KQUR Roots + Derivatives (all 58 term_index rows)

Rules:
  - Zero claude -p calls.  All reads are from mirror.db (SQLite, sub-ms).
  - Idempotent: INSERT OR IGNORE — running twice is safe.
  - Tradition: hadith/poetry atoms default to 'ismaili' (all KASHKOLE content
    is from the Ismaili tradition corpus).  Etymology atoms are 'universal'
    (Arabic roots transcend tradition).
  - OrbStack NOT required: the mirror is pre-built and committed to the repo.
    Only run source_library_mirror.py to refresh if source data changes.

CLI:
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py --status
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py --dry-run
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py --type hadith
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py --type poetry
    python3 scripts/podcast/intelligence/ingest_mcp_corpus.py --type etymology
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
_REPO = _SCRIPTS.parents[1]
for p in (str(_SCRIPTS), str(_REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from _db import get_connection, run_migrations
from scripts.podcast.source_library_mirror import open_mirror, MIRROR_PATH

# ---------------------------------------------------------------------------
# KASHKOLE TypeID constants (matches mcp_access.py)
# ---------------------------------------------------------------------------

_HADITH_TYPE_IDS = (17, 23)   # حدیث نبوی + معنی الحدیث
_POETRY_TYPE_IDS = (31,)       # منقبت

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class IngestSummary:
    hadith_created: int = 0
    hadith_skipped: int = 0
    poetry_created: int = 0
    poetry_skipped: int = 0
    etymology_created: int = 0
    etymology_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_created(self) -> int:
        return self.hadith_created + self.poetry_created + self.etymology_created

    @property
    def total_skipped(self) -> int:
        return self.hadith_skipped + self.poetry_skipped + self.etymology_skipped


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_atom(
    conn,
    atom_id: str,
    atom_type: str,
    body: dict,
    tradition: str,
) -> bool:
    """Insert one atom. Returns True if created, False if already existed."""
    existing = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE id = ?", (atom_id,)
    ).fetchone()[0]
    if existing:
        return False
    conn.execute(
        "INSERT INTO atoms (id, type, body, first_seen_date, tradition) "
        "VALUES (?, ?, ?, strftime('%Y-%m-%d', 'now'), ?)",
        (atom_id, atom_type, json.dumps(body, ensure_ascii=False), tradition),
    )
    return True


# ---------------------------------------------------------------------------
# Hadith ingest
# ---------------------------------------------------------------------------

def _ingest_hadith(
    mirror_conn, db_conn, dry_run: bool
) -> tuple[int, int, list[str]]:
    """Pull hadith topics from KASHKOLE fts_topics and write to knowledge.db.

    Returns (created, skipped, errors).
    """
    created = skipped = 0
    errors: list[str] = []

    rows = mirror_conn.execute(
        "SELECT topic_id, topic_type_id, name, description, binder, chapter, body_plain "
        "FROM fts_topics WHERE topic_type_id IN (17, 23)"
    ).fetchall()

    for row in rows:
        topic_id = row["topic_id"]
        atom_id = f"hadith:kashkole:{topic_id}"
        body = {
            "topic_id":     topic_id,
            "topic_type_id": row["topic_type_id"],
            "title":        row["name"],
            "description":  row["description"] or "",
            "binder":       row["binder"] or "",
            "chapter":      row["chapter"] or "",
            "text_ur":      row["body_plain"] or "",
            "tradition":    "ismaili",
            "source":       "kashkole",
        }
        if dry_run:
            existing = db_conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE id = ?", (atom_id,)
            ).fetchone()[0]
            if existing:
                skipped += 1
            else:
                created += 1
        else:
            try:
                if _insert_atom(db_conn, atom_id, "hadith", body, "ismaili"):
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"hadith {atom_id}: {exc}")

    return created, skipped, errors


# ---------------------------------------------------------------------------
# Poetry ingest
# ---------------------------------------------------------------------------

def _ingest_poetry(
    mirror_conn, db_conn, dry_run: bool
) -> tuple[int, int, list[str]]:
    """Pull poetry topics from KASHKOLE fts_topics and write to knowledge.db.

    Returns (created, skipped, errors).
    """
    created = skipped = 0
    errors: list[str] = []

    rows = mirror_conn.execute(
        "SELECT topic_id, topic_type_id, name, description, binder, chapter, body_plain "
        "FROM fts_topics WHERE topic_type_id IN (31)"
    ).fetchall()

    for row in rows:
        topic_id = row["topic_id"]
        atom_id = f"poetry:kashkole:{topic_id}"
        body = {
            "topic_id":     topic_id,
            "topic_type_id": row["topic_type_id"],
            "title":        row["name"],
            "description":  row["description"] or "",
            "binder":       row["binder"] or "",
            "chapter":      row["chapter"] or "",
            "matn_ur":      row["body_plain"] or "",
            "genre":        "manqabat",
            "tradition":    "ismaili",
            "source":       "kashkole",
        }
        if dry_run:
            existing = db_conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE id = ?", (atom_id,)
            ).fetchone()[0]
            if existing:
                skipped += 1
            else:
                created += 1
        else:
            try:
                if _insert_atom(db_conn, atom_id, "poetry", body, "ismaili"):
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"poetry {atom_id}: {exc}")

    return created, skipped, errors


# ---------------------------------------------------------------------------
# Etymology ingest
# ---------------------------------------------------------------------------

def _ingest_etymology(
    mirror_conn, db_conn, dry_run: bool
) -> tuple[int, int, list[str]]:
    """Pull KQUR Roots + Derivatives from term_index and write to knowledge.db.

    Groups derivatives under each root so each atom captures the full
    root entry.  Atom ID: etymology:<transliteration>.

    Returns (created, skipped, errors).
    """
    created = skipped = 0
    errors: list[str] = []

    # Gather all KQUR terms (roots and their derivatives) from term_index
    rows = mirror_conn.execute(
        "SELECT term, arabic, root, grammar_tag, definition, etymology, tradition "
        "FROM term_index WHERE source = 'KQUR' ORDER BY root, term"
    ).fetchall()

    # Group by root: the root itself is a term where root == term (or similar)
    from collections import defaultdict
    by_root: dict[str, list] = defaultdict(list)
    for row in rows:
        by_root[row["root"] or row["term"]].append(row)

    for root_key, entries in by_root.items():
        if not root_key.strip():
            continue
        atom_id = f"etymology:{root_key.lower().replace(' ', '_')}"

        # Build derivatives list (all entries except the root entry itself)
        derivatives = [
            {
                "term":        e["term"],
                "arabic":      e["arabic"] or "",
                "grammar":     e["grammar_tag"] or "",
                "meaning_en":  e["definition"] or "",
            }
            for e in entries
            if e["term"] != root_key
        ]

        # Root entry — use the first entry with a matching root transliteration
        root_entry = next(
            (e for e in entries if e["root"] == root_key), entries[0]
        )

        body = {
            "root_transliteration": root_key,
            "root_arabic":          root_entry["arabic"] or "",
            "meaning_en":           root_entry["definition"] or "",
            "meaning_ar":           root_entry["etymology"] or "",
            "derivatives":          derivatives,
            "tradition":            "universal",
            "source":               "kqur",
        }

        if dry_run:
            existing = db_conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE id = ?", (atom_id,)
            ).fetchone()[0]
            if existing:
                skipped += 1
            else:
                created += 1
        else:
            try:
                if _insert_atom(db_conn, atom_id, "etymology", body, "universal"):
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"etymology {atom_id}: {exc}")

    return created, skipped, errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_all(
    dry_run: bool = False,
    types: list[str] | None = None,
) -> IngestSummary:
    """Pull all MCP corpus atoms into knowledge.db.

    `types` restricts to a subset: ['hadith'], ['poetry'], ['etymology'],
    or any combination.  None (default) runs all three.

    Idempotent — safe to re-run.  Returns a summary with created/skipped counts.
    """
    run_migrations()
    db_conn = get_connection()
    mirror_conn = open_mirror()

    summary = IngestSummary()

    if mirror_conn is None:
        summary.errors.append(
            f"mirror.db not found at {MIRROR_PATH} — "
            "run: python3 scripts/podcast/source_library_mirror.py"
        )
        return summary

    run_types = set(types) if types else {"hadith", "poetry", "etymology"}

    if not dry_run:
        db_conn.execute("BEGIN;")

    try:
        if "hadith" in run_types:
            c, s, errs = _ingest_hadith(mirror_conn, db_conn, dry_run)
            summary.hadith_created = c
            summary.hadith_skipped = s
            summary.errors.extend(errs)

        if "poetry" in run_types:
            c, s, errs = _ingest_poetry(mirror_conn, db_conn, dry_run)
            summary.poetry_created = c
            summary.poetry_skipped = s
            summary.errors.extend(errs)

        if "etymology" in run_types:
            c, s, errs = _ingest_etymology(mirror_conn, db_conn, dry_run)
            summary.etymology_created = c
            summary.etymology_skipped = s
            summary.errors.extend(errs)

        if not dry_run:
            db_conn.execute("COMMIT;")

    except Exception as exc:
        if not dry_run:
            db_conn.execute("ROLLBACK;")
        summary.errors.append(f"Fatal: {exc}")

    mirror_conn.close()
    return summary


def print_status() -> None:
    """Print current atom counts in knowledge.db by type."""
    run_migrations()
    conn = get_connection()
    rows = conn.execute(
        "SELECT type, COUNT(*) AS n FROM atoms GROUP BY type ORDER BY n DESC"
    ).fetchall()
    if not rows:
        print("knowledge.db is empty — no atoms ingested yet.")
        return
    print("knowledge.db atom counts:")
    for r in rows:
        print(f"  {r['type']:<15} {r['n']:>5}")
    total = sum(r["n"] for r in rows)
    print(f"  {'TOTAL':<15} {total:>5}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="B5: Ingest hadith, poetry, etymology atoms from MCP mirror into knowledge.db"
    )
    parser.add_argument("--status", action="store_true",
                        help="Print current atom counts and exit.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count what would be created without writing.")
    parser.add_argument("--type", choices=["hadith", "poetry", "etymology"],
                        action="append", dest="types",
                        help="Restrict to one or more atom types (repeatable).")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    label = "Dry-run" if args.dry_run else "Ingesting"
    types_label = ", ".join(args.types) if args.types else "hadith + poetry + etymology"
    print(f"{label} MCP corpus atoms ({types_label}) …")

    summary = ingest_all(dry_run=args.dry_run, types=args.types)

    if args.dry_run:
        print("Would create:")
    else:
        print("Created:")
    print(f"  hadith     {summary.hadith_created:>4} created, {summary.hadith_skipped:>4} skipped")
    print(f"  poetry     {summary.poetry_created:>4} created, {summary.poetry_skipped:>4} skipped")
    print(f"  etymology  {summary.etymology_created:>4} created, {summary.etymology_skipped:>4} skipped")
    print(f"  TOTAL      {summary.total_created:>4} created, {summary.total_skipped:>4} skipped")

    for err in summary.errors:
        print(f"  ! {err}")

    if not args.dry_run:
        print()
        print_status()


if __name__ == "__main__":
    _cli()
