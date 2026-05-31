"""intelligence/ingest_kashkole.py — KASHKOLE (terms + hadith + topics) importer.

WC1 mirror-primary. Reads content/knowledge-base/mirror.db and populates the
KASHKOLE slice of the unified corpus:

  * KASHKOLE glossary terms (term_index WHERE source='KASHKOLE') -> ``term`` atoms.
  * KASHKOLE hadith (fts_hadith) -> external_corpora('hadith') + ``hadith`` atoms,
    tradition 'universal' (D5: raw hadith is tradition-neutral). INSERT OR IGNORE:
    a hadith id already authored by the wisdom-binder pipeline (e.g.
    ``hadith:kashkole:9``) is left untouched — only genuinely new ids are added.
  * KASHKOLE topics (fts_topics) are Urdu with no polished English. Per D8 (HARD,
    never re-translate) they are NOT minted as atoms here — the polished-English
    subset already lives as the 628 ``doctrine`` atoms from the wisdom-binder
    pipeline. They are recorded as a deferred note, not silently dropped.

Additive + idempotent. Re-running creates zero new rows.

CLI:
    python3 scripts/podcast/intelligence/ingest_kashkole.py --dry-run
    python3 scripts/podcast/intelligence/ingest_kashkole.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations

from intelligence._mirror_corpus import (
    MirrorSummary,
    ingest_terms,
    insert_atom,
    open_mirror_ro,
    refresh_corpus_count,
    upsert_corpus,
)

HADITH_CORPUS_ID = "hadith"
HADITH_TRADITION = "universal"   # D5: raw hadith is tradition-neutral


def ingest_all(*, dry_run: bool = False) -> MirrorSummary:
    summary = MirrorSummary(source="kashkole")
    mirror = open_mirror_ro()
    if mirror is None:
        summary.errors.append("mirror.db absent — run source_library_mirror.py first")
        return summary

    conn = get_connection()
    if not dry_run:
        upsert_corpus(conn, HADITH_CORPUS_ID, "Hadith (KASHKOLE)", "hadith")
        summary.corpora_registered += 1

    # ---- KASHKOLE glossary terms -> term atoms ----
    ingest_terms(mirror, conn, summary, source="KASHKOLE", dry_run=dry_run)

    # ---- KASHKOLE hadith -> hadith atoms (additive; never overwrite existing) ----
    hadiths = mirror.execute(
        "SELECT hadith_id, collection, hadith_num, arabic, english FROM fts_hadith"
    ).fetchall()
    for h in hadiths:
        if dry_run:
            summary.total_atoms_created += 1
            continue
        atom_id = f"hadith:kashkole:{h['hadith_id']}"
        body = json.dumps({
            "hadith_id": h["hadith_id"], "collection": h["collection"],
            "hadith_num": h["hadith_num"], "arabic": h["arabic"],
            "english": h["english"], "tradition": HADITH_TRADITION,
        }, ensure_ascii=False)
        if insert_atom(
            conn, atom_id, "hadith", body, HADITH_TRADITION,
            first_seen_book="kashkole",
        ):
            summary.total_atoms_created += 1
        else:
            summary.atoms_skipped_existing += 1

    # ---- KASHKOLE topics: deferred (D8 no-retranslate) ----
    topic_count = mirror.execute("SELECT COUNT(*) FROM fts_topics").fetchone()[0]
    summary.notes.append(
        f"topics: {topic_count} KASHKOLE topics NOT minted as atoms (D8 no-retranslate; "
        f"polished-English subset already present as doctrine atoms)"
    )

    if not dry_run:
        refresh_corpus_count(conn, HADITH_CORPUS_ID, "hadith")
        conn.commit()
    mirror.close()
    return summary


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="KASHKOLE mirror-primary importer (WC1)")
    p.add_argument("--dry-run", action="store_true", help="Simulate; no DB writes")
    args = p.parse_args()
    run_migrations()
    s = ingest_all(dry_run=args.dry_run)
    flag = " (dry-run)" if args.dry_run else ""
    print(f"KASHKOLE ingest{flag}: {s.total_atoms_created} atoms created, "
          f"{s.atoms_skipped_existing} already present")
    for n in s.notes:
        print(f"  · {n}")
    for e in s.errors:
        print(f"  ! {e}")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(_main())
