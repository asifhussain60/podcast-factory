"""intelligence/populate_corpus.py — WC1 corpus-population runner.

The single entry point for "populate the wisdom corpus": run migrations, ingest
every on-disk source, run the tiered dedup engine, then print and verify the WC1
acceptance criteria.

Today it drives the ONE source on disk (wisdom/teaching material). The Quran,
scholarly, and teaching-sessions importers register here as they are built; each
just adds a line to SOURCES below, then dedup + acceptance run unchanged.

CLI:
    python3 scripts/podcast/intelligence/populate_corpus.py
    python3 scripts/podcast/intelligence/populate_corpus.py --verify-idempotent
    python3 scripts/podcast/intelligence/populate_corpus.py --dry-run
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations

from intelligence import (
    dedup_corpus,
    ingest_kashkole,
    ingest_kqur,
    ingest_ksessions_dump,
    wisdom_ingest_knowledge,
)

# Source importers, in run order. Each is (label, callable -> ingest summary).
# WC1 update_2026_05_31_mirror_primary: the KQUR/KASHKOLE/KSESSIONS importers are
# now wired — they read content/knowledge-base/mirror.db (no Docker). Dedup +
# acceptance run unchanged over the combined corpus.
SOURCES = [
    ("wisdom (teaching material)", lambda dry: wisdom_ingest_knowledge.ingest_all(dry_run=dry)),
    ("KQUR (Quran + terms)",       lambda dry: ingest_kqur.ingest_all(dry_run=dry)),
    ("KASHKOLE (terms + hadith)",  lambda dry: ingest_kashkole.ingest_all(dry_run=dry)),
    ("KSESSIONS (transcripts)",    lambda dry: ingest_ksessions_dump.ingest_all(dry_run=dry)),
]


def _counts(conn) -> dict[str, int]:
    out = {}
    for t in ("external_corpora", "corpus_chapters", "atoms",
              "atoms_sources", "atoms_variants", "manual_review_queue"):
        out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return out


def _tradition_coverage(conn) -> tuple[int, int]:
    total = conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]
    stamped = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE tradition IS NOT NULL AND tradition != ''"
    ).fetchone()[0]
    return stamped, total


def populate(*, dry_run: bool = False) -> dict:
    run_migrations()
    conn = get_connection()

    print("== Ingesting sources ==")
    for label, fn in SOURCES:
        summary = fn(dry_run)
        created = getattr(summary, "total_atoms_created", "?")
        scanned = getattr(summary, "total_chapters", "?")
        print(f"  {label}: {scanned} chapters scanned, {created} atoms created"
              f"{' (dry-run)' if dry_run else ''}")
        for err in getattr(summary, "errors", []) or []:
            print(f"    ! {err}")

    print("\n== Tiered dedup (D7) ==")
    ds = dedup_corpus.dedup(dry_run=dry_run)
    print(f"  {ds.atoms_scanned} atoms, {ds.blocks} blocks, {ds.pairs_compared} pairs")
    print(f"  HIGH clusters: {ds.clusters} -> {ds.variants_written} variants, {ds.review_high} auto-merge candidates")
    print(f"  BORDERLINE for human review: {ds.review_borderline}")
    if ds.skipped_blocks:
        print(f"  skipped large blocks: {'; '.join(ds.skipped_blocks)}")

    counts = _counts(conn)
    stamped, total = _tradition_coverage(conn)

    print("\n== Acceptance (WC1) ==")
    populated = counts["external_corpora"] > 0 and counts["corpus_chapters"] > 0 and counts["atoms"] > 0
    tradition_ok = total > 0 and stamped == total
    print(f"  [{'PASS' if populated else 'FAIL'}] populated: "
          f"external_corpora={counts['external_corpora']} corpus_chapters={counts['corpus_chapters']} atoms={counts['atoms']}")
    print(f"  [{'PASS' if tradition_ok else 'FAIL'}] tradition set on every atom: {stamped}/{total}")
    print(f"  (dedup links: atoms_variants={counts['atoms_variants']}, review_queue={counts['manual_review_queue']})")

    return {"counts": counts, "tradition": (stamped, total),
            "dedup": ds, "populated": populated, "tradition_ok": tradition_ok}


def verify_idempotent() -> bool:
    """Run the full populate twice; assert row counts are identical the 2nd time."""
    print("### Pass 1 ###")
    r1 = populate()
    print("\n### Pass 2 (idempotency check) ###")
    r2 = populate()
    same = r1["counts"] == r2["counts"]
    print("\n== Idempotency ==")
    if same:
        print("  [PASS] row counts identical across re-run.")
    else:
        print("  [FAIL] counts drifted across re-run:")
        for k in r1["counts"]:
            if r1["counts"][k] != r2["counts"][k]:
                print(f"    {k}: {r1['counts'][k]} -> {r2['counts'][k]}")
    return same


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="WC1 corpus-population runner")
    p.add_argument("--dry-run", action="store_true", help="Simulate; no DB writes")
    p.add_argument("--verify-idempotent", action="store_true",
                   help="Run twice and assert identical row counts")
    args = p.parse_args()

    if args.verify_idempotent:
        ok = verify_idempotent()
        return 0 if ok else 1

    r = populate(dry_run=args.dry_run)
    if args.dry_run:
        return 0
    return 0 if (r["populated"] and r["tradition_ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
