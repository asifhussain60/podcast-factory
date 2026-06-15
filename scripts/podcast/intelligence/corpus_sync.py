"""corpus_sync.py — durable, machine-portable sync for the knowledge corpus.

The canonical store ``knowledge.db`` is gitignored local state. On its own that
means the hydrated corpus is NEVER committed and NEVER shared: a fresh clone or a
peer machine has no atoms, and a lost/reset DB loses everything. This module
closes that gap with the diff-friendly model the README always intended:

  export  — DB atoms (+ sources + variants) → per-type JSONL, one atom per line,
            sorted by id. Text, deterministic → git merges two machines' exports
            as a UNION with no binary conflict.
  rebuild — JSONL → DB via INSERT OR IGNORE (ADDITIVE-ONLY). It can only ADD
            atoms; it NEVER updates or deletes, so pulling a peer's atoms can
            never wipe this machine's local-only hydrated content.

Cross-machine protocol (never lose anything):
  1. Each machine runs ``export`` before committing  → its atoms land in git as text.
  2. ``git pull`` union-merges the JSONL (both machines' atoms survive in text).
  3. Each machine runs ``rebuild`` after pulling      → additive merge into its DB.

Timestamps (created_at/updated_at) are intentionally omitted from the JSONL so
exports stay stable across machines and don't churn diffs. rebuild stamps
created_at on insert.

CLI:
  python3 scripts/podcast/intelligence/corpus_sync.py export      # DB → JSONL
  python3 scripts/podcast/intelligence/corpus_sync.py rebuild     # JSONL → DB (additive)
  python3 scripts/podcast/intelligence/corpus_sync.py verify      # DB vs JSONL counts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

KB_DIR = REPO_ROOT / "content" / "knowledge-base"


def _type_to_file(atom_type: str) -> Path:
    return KB_DIR / f"{atom_type}.jsonl"


def _envelope(row, sources: list, variants: list) -> dict:
    """Build the stable, timestamp-free JSONL envelope for one atom."""
    try:
        body = json.loads(row["body"]) if row["body"] else {}
    except (json.JSONDecodeError, TypeError):
        body = {"_raw": row["body"]}
    return {
        "id": row["id"],
        "type": row["type"],
        "body": body,
        "first_seen": {
            "book": row["first_seen_book"],
            "chapter": row["first_seen_chapter"],
            "date": row["first_seen_date"],
        },
        "confidence": row["confidence"],
        "tradition": row["tradition"],
        "content_level": row["content_level"],
        "sources": [
            {"book": s["book_slug"], "chapter": s["chapter_id"], "locator": s["locator"]}
            for s in sources
        ],
        "variants": [
            {"book": v["book_slug"], "text_en": v["text_en"], "translator": v["translator"]}
            for v in variants
        ],
    }


class CorpusShrinkError(RuntimeError):
    """Raised when a safe export would REDUCE a committed JSONL's atom count.

    This is the guard against an under-hydrated machine (e.g. a fresh clone whose
    DB hasn't absorbed the committed atoms yet) silently clobbering the shared
    corpus backup. The fix is always: run ``rebuild`` first (additive — pulls the
    committed atoms into the local DB), THEN ``export``.
    """


def _jsonl_line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def export(*, safe: bool = False) -> dict[str, int]:
    """DB → per-type JSONL (sorted by id, deterministic). Returns per-type counts.

    With ``safe=True``, refuses to write if any type's DB count is LOWER than the
    already-committed JSONL line count (which would lose atoms). Raises
    CorpusShrinkError instead — the caller should ``rebuild`` first.
    """
    import sqlite3
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    if safe:
        db_counts = {r["type"]: r["n"] for r in conn.execute(
            "SELECT type, COUNT(*) n FROM atoms GROUP BY type")}
        shrinking = []
        for path in KB_DIR.glob("*.jsonl"):
            if path.name in {"pronunciations.jsonl", "pronunciation-patterns.jsonl"}:
                continue
            existing = _jsonl_line_count(path)
            if existing > db_counts.get(path.stem, 0):
                shrinking.append(f"{path.stem}: committed={existing} > db={db_counts.get(path.stem, 0)}")
        if shrinking:
            raise CorpusShrinkError(
                "export would SHRINK the committed corpus (run rebuild first): "
                + "; ".join(shrinking))

    # Pre-group sources/variants by atom_id (single pass each).
    src_by_atom: dict[str, list] = {}
    for s in conn.execute("SELECT atom_id, book_slug, chapter_id, locator FROM atoms_sources"):
        src_by_atom.setdefault(s["atom_id"], []).append(s)
    var_by_atom: dict[str, list] = {}
    for v in conn.execute("SELECT atom_id, book_slug, text_en, translator FROM atoms_variants"):
        var_by_atom.setdefault(v["atom_id"], []).append(v)

    by_type: dict[str, list[dict]] = {}
    for row in conn.execute("SELECT * FROM atoms ORDER BY id"):
        env = _envelope(row, src_by_atom.get(row["id"], []), var_by_atom.get(row["id"], []))
        # stable ordering of nested lists for clean diffs
        env["sources"].sort(key=lambda d: (d["book"] or "", d["chapter"] or "", d["locator"] or ""))
        env["variants"].sort(key=lambda d: (d["book"] or "", d["translator"] or ""))
        by_type.setdefault(row["type"], []).append(env)

    counts: dict[str, int] = {}
    for atom_type, envs in by_type.items():
        envs.sort(key=lambda e: e["id"])
        path = _type_to_file(atom_type)
        with path.open("w", encoding="utf-8") as fh:
            for e in envs:
                fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        counts[atom_type] = len(envs)
    return counts


def rebuild() -> dict[str, int]:
    """JSONL → DB, ADDITIVE-ONLY (INSERT OR IGNORE). Never updates/deletes.

    Returns per-type count of atoms newly inserted (already-present atoms are left
    untouched, so a peer's pull can never overwrite local hydrated content).
    """
    run_migrations()
    conn = get_connection()
    inserted: dict[str, int] = {}
    for path in sorted(KB_DIR.glob("*.jsonl")):
        # skip the conflicts/pending file and any non-atom jsonl
        if path.name in {"pronunciations.jsonl", "pronunciation-patterns.jsonl"}:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                a = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not a.get("id") or not a.get("type"):
                continue
            fs = a.get("first_seen") or {}
            cur = conn.execute(
                """INSERT OR IGNORE INTO atoms
                   (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
                    confidence, tradition, content_level, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?, datetime('now'), datetime('now'))""",
                (
                    a["id"], a["type"], json.dumps(a.get("body", {}), ensure_ascii=False),
                    fs.get("book"), fs.get("chapter"), fs.get("date"),
                    a.get("confidence"), a.get("tradition"), a.get("content_level"),
                ),
            )
            if cur.rowcount:
                inserted[a["type"]] = inserted.get(a["type"], 0) + 1
            for s in a.get("sources", []):
                conn.execute(
                    """INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id, locator)
                       VALUES (?,?,?,?)""",
                    (a["id"], s.get("book"), s.get("chapter"), s.get("locator")),
                )
            for v in a.get("variants", []):
                conn.execute(
                    """INSERT OR IGNORE INTO atoms_variants (atom_id, book_slug, text_en, translator)
                       VALUES (?,?,?,?)""",
                    (a["id"], v.get("book"), v.get("text_en"), v.get("translator")),
                )
    conn.commit()
    return inserted


def verify() -> None:
    conn = get_connection()
    import sqlite3
    conn.row_factory = sqlite3.Row
    db_counts = {r["type"]: r["n"] for r in conn.execute(
        "SELECT type, COUNT(*) n FROM atoms GROUP BY type")}
    jsonl_counts = {}
    for path in sorted(KB_DIR.glob("*.jsonl")):
        if path.name in {"pronunciations.jsonl", "pronunciation-patterns.jsonl"}:
            continue
        n = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
        if n:
            jsonl_counts[path.stem] = n
    print("type        DB    JSONL")
    for t in sorted(set(db_counts) | set(jsonl_counts)):
        print(f"  {t:<10} {db_counts.get(t,0):>4}   {jsonl_counts.get(t,0):>4}")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Durable corpus sync (DB <-> JSONL).")
    ap.add_argument("cmd", choices=["export", "rebuild", "verify"])
    ap.add_argument("--safe", action="store_true",
                    help="export: refuse to shrink the committed corpus (run rebuild first).")
    args = ap.parse_args()
    if args.cmd == "export":
        try:
            c = export(safe=args.safe)
        except CorpusShrinkError as e:
            print(f"corpus_sync: REFUSED — {e}", file=sys.stderr)
            return 3
        print("Exported (DB → JSONL):", {k: c[k] for k in sorted(c)})
    elif args.cmd == "rebuild":
        c = rebuild()
        print("Rebuilt (JSONL → DB, additive):",
              {k: c[k] for k in sorted(c)} if c else "0 new (DB already current)")
    else:
        verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
