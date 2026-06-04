"""intelligence/ingest_kqur.py — KQUR (Quran + term index) mirror-primary importer.

WC1 mirror-primary. Reads the on-disk FTS mirror (content/knowledge-base/mirror.db)
and populates knowledge.db with the KQUR slice of the unified corpus:

  * Quran verses (fts_quran) -> external_corpora('quran') + one corpus_chapters
    row per surah + one ``quran`` atom per verse. Raw scripture -> tradition
    'universal' (D5). English is already present (Pickthall + Asad) so nothing is
    translated.
  * KQUR glossary terms (term_index WHERE source='KQUR') -> ``term`` atoms,
    tradition taken from the row (D5: terms carry their source tradition).

Additive + idempotent: verses/terms keyed by canonical id, INSERT OR IGNORE.
Re-running creates zero new rows.

CLI:
    python3 scripts/podcast/intelligence/ingest_kqur.py --dry-run
    python3 scripts/podcast/intelligence/ingest_kqur.py
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
    upsert_chapter,
    upsert_corpus,
)

QURAN_CORPUS_ID = "quran"
QURAN_TRADITION = "universal"   # D5: raw scripture is tradition-neutral


def ingest_all(*, dry_run: bool = False) -> MirrorSummary:
    summary = MirrorSummary(source="kqur")
    mirror = open_mirror_ro()
    if mirror is None:
        summary.errors.append("mirror.db absent — run source_library_mirror.py first")
        return summary

    conn = get_connection()
    if not dry_run:
        upsert_corpus(conn, QURAN_CORPUS_ID, "Quran (KQUR)", "quran")
        summary.corpora_registered += 1

    # ---- Quran verses -> corpus_chapters (per surah) + quran atoms (per verse) ----
    verses = mirror.execute(
        "SELECT surah, ayat, arabic, pickthall, asad, urdu, phonetic FROM fts_quran"
    ).fetchall()
    surahs_seen: set[int] = set()
    surah_verse_counts: dict[int, int] = {}
    for v in verses:
        surah = int(v["surah"])
        surah_verse_counts[surah] = surah_verse_counts.get(surah, 0) + 1

    for v in verses:
        surah, ayat = int(v["surah"]), int(v["ayat"])
        if dry_run:
            surahs_seen.add(surah)
            summary.total_atoms_created += 1
            continue
        if surah not in surahs_seen:
            if upsert_chapter(
                conn, f"quran:{surah}", QURAN_CORPUS_ID,
                number=surah, title_en=f"Surah {surah}",
                verse_count=surah_verse_counts[surah],
            ):
                summary.total_chapters += 1
            surahs_seen.add(surah)
        body = json.dumps({
            "surah": surah, "ayat": ayat,
            "arabic": v["arabic"], "pickthall": v["pickthall"], "asad": v["asad"],
            "urdu": v["urdu"], "phonetic": v["phonetic"],
            "tradition": QURAN_TRADITION,
        }, ensure_ascii=False)
        if insert_atom(
            conn, f"quran:{surah}:{ayat}", "quran", body, QURAN_TRADITION,
            first_seen_book=QURAN_CORPUS_ID,
        ):
            summary.total_atoms_created += 1
        else:
            summary.atoms_skipped_existing += 1

    # ---- KQUR glossary terms -> term atoms ----
    ingest_terms(mirror, conn, summary, source="KQUR", dry_run=dry_run)

    if not dry_run:
        refresh_corpus_count(conn, QURAN_CORPUS_ID, "quran")
        conn.commit()
    mirror.close()
    return summary


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="KQUR mirror-primary importer (WC1)")
    p.add_argument("--dry-run", action="store_true", help="Simulate; no DB writes")
    args = p.parse_args()
    run_migrations()
    s = ingest_all(dry_run=args.dry_run)
    flag = " (dry-run)" if args.dry_run else ""
    print(f"KQUR ingest{flag}: {s.total_atoms_created} atoms created, "
          f"{s.atoms_skipped_existing} already present, {s.total_chapters} surahs")
    for e in s.errors:
        print(f"  ! {e}")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(_main())
