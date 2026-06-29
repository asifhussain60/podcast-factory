"""corpus_sync.py — durable, machine-portable sync for the knowledge corpus.

The canonical store ``knowledge.db`` is gitignored local state. On its own that
means the hydrated corpus is NEVER committed and NEVER shared: a fresh clone or a
peer machine has no atoms, and a lost/reset DB loses everything. This module
closes that gap with the diff-friendly model the README always intended:

  export  — DB atoms (+ sources + variants) → per-type JSONL, one atom per line,
            sorted by id. Text, deterministic → git merges two machines' exports
            as a UNION with no binary conflict.
  rebuild — JSONL → DB via ADDITIVE-MERGE. Duplicate-id lines (from a git
            union-merge) are reconciled per id: same-text versions merge
            losslessly (field-union of body/sources/variants, richer value wins);
            genuine id-collisions (same id, different text) split into distinct
            ids and are logged to _conflicts/id-collisions.jsonl. The merge can
            only ADD information to an existing atom, never remove it, so pulling
            a peer's atoms enriches local content and never wipes it.

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


def _is_empty(v) -> bool:
    return v is None or v == "" or v == {} or v == []


def _merge_body(a: dict, b: dict) -> dict:
    """Field-union of two atom bodies. Lossless: fills missing/empty keys from
    the other side and, when both carry a non-empty value for the same key,
    keeps the richer (longer string) — never drops a field."""
    out = dict(a or {})
    for k, v in (b or {}).items():
        if _is_empty(out.get(k)):
            out[k] = v
        elif not _is_empty(v) and out[k] != v and isinstance(v, str) \
                and isinstance(out[k], str) and len(v) > len(out[k]):
            out[k] = v
    return out


def _dedup(items: list, key) -> list:
    seen = set()
    out = []
    for it in items:
        k = key(it)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _merge_envelopes(a: dict, b: dict) -> dict:
    """Combine two atom envelopes for the SAME logical atom, losslessly.

    Body is field-unioned; sources/variants are union-deduped; confidence takes
    the max; first_seen keeps the earliest date; tradition/content_level/type
    prefer the first non-empty. This can only ADD information, never remove —
    so it is safe as the cross-machine merge primitive.
    """
    out = dict(a)
    out["body"] = _merge_body(a.get("body") or {}, b.get("body") or {})
    fa, fb = a.get("first_seen") or {}, b.get("first_seen") or {}
    da, db_ = fa.get("date") or "", fb.get("date") or ""
    out["first_seen"] = fa if (da and (not db_ or da <= db_)) else (fb if db_ else fa)
    out["confidence"] = max(a.get("confidence") or 0, b.get("confidence") or 0) \
        or a.get("confidence")
    for k in ("tradition", "content_level", "type"):
        out[k] = a.get(k) if not _is_empty(a.get(k)) else b.get(k)
    out["sources"] = _dedup(
        (a.get("sources") or []) + (b.get("sources") or []),
        lambda s: (s.get("book"), s.get("chapter"), s.get("locator")))
    out["variants"] = _dedup(
        (a.get("variants") or []) + (b.get("variants") or []),
        lambda v: (v.get("book"), v.get("text_en"), v.get("translator")))
    return out


def _text_sig(env: dict) -> str:
    return ((env.get("body") or {}).get("text_en") or "").strip()


def _reconcile_group(atom_id: str, versions: list[dict]) -> tuple[list[tuple[str, dict]], list[dict]]:
    """Collapse all JSONL versions of one id into the correct atom(s).

    Versions sharing the same ``body.text_en`` are the same atom → merged
    losslessly. If two versions carry DIFFERENT non-empty ``text_en`` under one
    id, that is an ID COLLISION (two distinct atoms hashed to the same id): the
    earliest-first_seen one keeps the id, the rest are re-keyed ``<id>~N`` so no
    content is lost. Returns (kept_atoms, collision_records)."""
    clusters: dict[str, dict] = {}
    empties: list[dict] = []
    for v in versions:
        sig = _text_sig(v)
        if sig:
            clusters[sig] = _merge_envelopes(clusters[sig], v) if sig in clusters else dict(v)
        else:
            empties.append(v)
    if not clusters:
        merged = empties[0]
        for v in empties[1:]:
            merged = _merge_envelopes(merged, v)
        return [(atom_id, merged)], []
    sigs = sorted(clusters)
    for v in empties:  # fold text-less versions into the first cluster
        clusters[sigs[0]] = _merge_envelopes(clusters[sigs[0]], v)
    if len(sigs) == 1:
        return [(atom_id, clusters[sigs[0]])], []

    def _fs_date(env: dict) -> str:
        return (env.get("first_seen") or {}).get("date") or "9999"

    ordered = sorted((clusters[s] for s in sigs), key=lambda e: (_fs_date(e), _text_sig(e)))
    kept: list[tuple[str, dict]] = [(atom_id, ordered[0])]
    collisions: list[dict] = [{"original_id": atom_id, "status": "kept", **ordered[0]}]
    for n, env in enumerate(ordered[1:], start=1):
        new_id = f"{atom_id}~{n}"
        env = {**env, "id": new_id}
        kept.append((new_id, env))
        collisions.append({"original_id": atom_id, "status": "rekeyed", **env})
    return kept, collisions


class CorpusShrinkError(RuntimeError):
    """Raised when a safe export would REDUCE a committed JSONL's atom count.

    This is the guard against an under-hydrated machine (e.g. a fresh clone whose
    DB hasn't absorbed the committed atoms yet) silently clobbering the shared
    corpus backup. The fix is always: run ``rebuild`` first (additive — pulls the
    committed atoms into the local DB), THEN ``export``.
    """


def _jsonl_unique_id_count(path: Path) -> int:
    """Count DISTINCT atom ids in a JSONL — NOT raw lines. Duplicate-id lines
    (from cross-machine union-merges) must not inflate the count, or the shrink
    guard false-trips when the DB holds the correctly-deduplicated set."""
    if not path.is_file():
        return 0
    ids = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            ids.add(json.loads(ln).get("id"))
        except json.JSONDecodeError:
            continue
    ids.discard(None)
    return len(ids)


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
            existing = _jsonl_unique_id_count(path)
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
    """JSONL → DB, ADDITIVE-MERGE (never loses data).

    For each id, all duplicate-id JSONL lines are reconciled (``_reconcile_group``):
    same-text versions merge losslessly; genuine id-collisions split into distinct
    ids and are logged to ``_conflicts/id-collisions.jsonl``. Each resulting atom
    is then merged with any existing DB row and upserted — so a peer's pull can
    only ENRICH local content (add fields/sources/variants, pick the richer
    version), never wipe it. Returns per-type count of atoms touched.
    """
    run_migrations()
    import sqlite3
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    # 1) Group every JSONL line by id, then reconcile each id-group.
    raw_by_id: dict[str, list] = {}
    for path in sorted(KB_DIR.glob("*.jsonl")):
        if path.name in {"pronunciations.jsonl", "pronunciation-patterns.jsonl"}:
            continue
        if path.parent.name == "_conflicts":
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
            raw_by_id.setdefault(a["id"], []).append(a)

    reconciled: dict[str, dict] = {}
    collisions: list[dict] = []
    for atom_id, versions in raw_by_id.items():
        kept, coll = _reconcile_group(atom_id, versions)
        for new_id, env in kept:
            reconciled[new_id] = env
        collisions.extend(coll)

    # 2) Upsert each reconciled atom, merging with any existing DB row.
    touched: dict[str, int] = {}
    for atom_id, env in reconciled.items():
        existing = conn.execute("SELECT * FROM atoms WHERE id=?", (atom_id,)).fetchone()
        if existing is not None:
            ex_env = _envelope(
                existing,
                list(conn.execute("SELECT * FROM atoms_sources WHERE atom_id=?", (atom_id,))),
                list(conn.execute("SELECT * FROM atoms_variants WHERE atom_id=?", (atom_id,))),
            )
            env = _merge_envelopes(ex_env, env)
            fs = env.get("first_seen") or {}
            conn.execute(
                """UPDATE atoms SET body=?, first_seen_book=?, first_seen_chapter=?,
                   first_seen_date=?, confidence=?, tradition=?, content_level=?,
                   updated_at=datetime('now') WHERE id=?""",
                (json.dumps(env.get("body", {}), ensure_ascii=False),
                 fs.get("book"), fs.get("chapter"), fs.get("date"), env.get("confidence"),
                 env.get("tradition"), env.get("content_level"), atom_id),
            )
        else:
            fs = env.get("first_seen") or {}
            conn.execute(
                """INSERT INTO atoms
                   (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
                    confidence, tradition, content_level, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?, datetime('now'), datetime('now'))""",
                (atom_id, env["type"], json.dumps(env.get("body", {}), ensure_ascii=False),
                 fs.get("book"), fs.get("chapter"), fs.get("date"),
                 env.get("confidence"), env.get("tradition"), env.get("content_level")),
            )
        for s in env.get("sources", []):
            conn.execute(
                """INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id, locator)
                   VALUES (?,?,?,?)""",
                (atom_id, s.get("book"), s.get("chapter"), s.get("locator")),
            )
        for v in env.get("variants", []):
            conn.execute(
                """INSERT OR IGNORE INTO atoms_variants (atom_id, book_slug, text_en, translator)
                   VALUES (?,?,?,?)""",
                (atom_id, v.get("book"), v.get("text_en"), v.get("translator")),
            )
        touched[env["type"]] = touched.get(env["type"], 0) + 1

    conn.commit()

    # 3) Persist any id-collision records for human review (lossless: both kept).
    if collisions:
        cdir = KB_DIR / "_conflicts"
        cdir.mkdir(exist_ok=True)
        with (cdir / "id-collisions.jsonl").open("w", encoding="utf-8") as fh:
            for c in sorted(collisions, key=lambda r: (r.get("original_id") or "", r.get("id") or "")):
                fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")

    return touched


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
        print("Rebuilt (JSONL → DB, additive-merge):",
              {k: c[k] for k in sorted(c)} if c else "0 atoms")
    else:
        verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
