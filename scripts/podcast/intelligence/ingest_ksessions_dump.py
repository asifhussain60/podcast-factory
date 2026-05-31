"""intelligence/ingest_ksessions_dump.py — KSESSIONS transcripts importer (D17).

WC1 mirror-primary. KSESSIONS is the live authoring system-of-record (D3): Asif
drops a refreshed dump, source_library_mirror.py rebuilds the FTS mirror, and this
importer re-syncs the corpus from content/knowledge-base/mirror.db. The path is
idempotent (D17) — re-ingesting the same dump creates zero new rows.

What it does:
  * Registers external_corpora('ksessions', scholarly).
  * One corpus_chapters row per session (id ``ksessions:<session_id>``,
    title = session_name) so transcripts are referenceable + counted.

What it deliberately does NOT do (yet):
  * It does NOT mint atoms from raw transcripts. Atomising a 606-transcript corpus
    is the WC3 knowledge-phase job (one LLM read per chapter), and the topic/session
    ~40% overlap collapse is the cross-source dedup deferred until that lands. This
    keeps WC1 deterministic and LLM-free while making the sessions corpus present.

CLI:
    python3 scripts/podcast/intelligence/ingest_ksessions_dump.py --dry-run
    python3 scripts/podcast/intelligence/ingest_ksessions_dump.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations

from intelligence._mirror_corpus import (
    MirrorSummary,
    open_mirror_ro,
    upsert_chapter,
    upsert_corpus,
)

SESSIONS_CORPUS_ID = "ksessions"


def ingest_all(*, dry_run: bool = False) -> MirrorSummary:
    summary = MirrorSummary(source="ksessions")
    mirror = open_mirror_ro()
    if mirror is None:
        summary.errors.append("mirror.db absent — run source_library_mirror.py first")
        return summary

    conn = get_connection()
    if not dry_run:
        upsert_corpus(conn, SESSIONS_CORPUS_ID, "KSESSIONS Transcripts", "scholarly")
        summary.corpora_registered += 1

    sessions = mirror.execute(
        "SELECT session_id, session_name, group_id FROM fts_sessions"
    ).fetchall()
    for s in sessions:
        if dry_run:
            summary.total_chapters += 1
            continue
        title = (s["session_name"] or f"Session {s['session_id']}").strip()
        if upsert_chapter(
            conn, f"ksessions:{s['session_id']}", SESSIONS_CORPUS_ID,
            number=int(s["group_id"]) if s["group_id"] is not None else None,
            title_en=title,
        ):
            summary.total_chapters += 1

    summary.notes.append(
        "sessions registered as corpus_chapters only; atomisation + topic/session "
        "40% dedup deferred to WC3 knowledge-phase (one LLM read per transcript)"
    )

    if not dry_run:
        conn.commit()
    mirror.close()
    return summary


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="KSESSIONS dump-sync importer (WC1, D17)")
    p.add_argument("--dry-run", action="store_true", help="Simulate; no DB writes")
    args = p.parse_args()
    run_migrations()
    s = ingest_all(dry_run=args.dry_run)
    flag = " (dry-run)" if args.dry_run else ""
    print(f"KSESSIONS ingest{flag}: {s.total_chapters} session chapters registered")
    for n in s.notes:
        print(f"  · {n}")
    for e in s.errors:
        print(f"  ! {e}")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(_main())
