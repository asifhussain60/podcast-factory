#!/usr/bin/env python3
"""reconcile_articulation.py — retrofit / repo-wide sweep for chapters left
stuck partial or reverted by the articulation (fluency/rearticulate) pass.

WHY
---
Until 2026-08-15, a window that failed `_book_voice_gates.revoice_gates` was
reverted to its base prose and never revisited — the reason lived only in
that one run's stdout, and nothing gated on the result (see
`_articulation_reconcile.py` and `validate_book_ready.py`'s new B9 gate for
the full story). This script is the tool that actually DOES the
reconciling: for a book with any open reconcile debt, it gives every stuck
chapter one more bounded attempt (via `_articulation_reconcile.reconcile_records`
/ `_book_voice.apply_fluency_adapt`), with every prior attempt's specific gate
findings folded into the retry's repair prompt.

Two uses:
  - Retrofit a specific book that predates gate B9 (like the two Mukhtasar
    volumes discovered on 2026-08-15).
  - `--all`: sweep every book in the repo (via `_paths.iter_content`, the
    canonical every-book enumerator), so "process ALL chapters, not rely on
    someone noticing" is an actual repeatable command, not a promise. Runs
    gate B9 first (cheap, read-only) and only spends a model call on books
    that actually have something to reconcile.

USAGE
    python3 scripts/podcast/reconcile_articulation.py <slug> [<slug> ...]
    python3 scripts/podcast/reconcile_articulation.py --all [--dry-run] [--json]

EXIT CODES
    0  — every targeted book ended clean (or was already clean)
    1  — at least one book still has open reconcile debt after the attempt
    2  — bad input (no slugs and no --all)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _articulation_reconcile import _chapter_numbers_by_title, gate_articulation_complete
from _paths import iter_content, slug_of


def _resolve_book_dir(slug: str) -> Path | None:
    from validate_book_ready import _resolve_book_dir as _resolve

    return _resolve(slug)


def _stuck_chapters(book_dir: Path) -> list[tuple[int, str]]:
    """[(section_number, title), ...] for chapters not fully articulated,
    numbered the same way `_run_pass` numbers them (see
    `_articulation_reconcile._chapter_numbers_by_title` for why this can't be
    a plain enumerate)."""
    report_path = book_dir / "_system" / "book-fluency-report.json"
    if not report_path.is_file():
        return []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    numbers = _chapter_numbers_by_title(book_dir / "book" / "book.md")
    stuck = []
    for chapter in report.get("chapters", []):
        status = chapter.get("superseded_status") or chapter.get("status")
        title = chapter.get("title", "")
        if status in ("partial", "reverted", "skipped") and title in numbers:
            stuck.append((numbers[title], title))
    return stuck


def reconcile_one(slug: str, book_dir: Path, *, dry_run: bool, log=print) -> dict:
    ok, why = gate_articulation_complete(book_dir)
    if ok:
        return {"slug": slug, "status": "clean", "note": why}

    stuck = _stuck_chapters(book_dir)
    if not stuck:
        # B9 failed but no fluency report chapter matched — a report/book.md
        # mismatch (stale report from a re-compose). Report, don't guess.
        return {"slug": slug, "status": "unresolvable", "note": why}

    if dry_run:
        return {"slug": slug, "status": "needs-reconcile", "chapters": [t for _, t in stuck], "note": why}

    from _book_voice import apply_fluency_adapt

    log(f"==> reconcile_articulation: {slug} — {len(stuck)} chapter(s): {[t for _, t in stuck]}")
    apply_fluency_adapt(book_dir, log=log, force=True, only=[n for n, _ in stuck])

    ok2, why2 = gate_articulation_complete(book_dir)
    return {"slug": slug, "status": "resolved" if ok2 else "still-open", "note": why2}


def _every_book_slug() -> list[tuple[str, Path]]:
    """(slug, book_dir) for every book with a reading edition. Uses `slug_of`,
    NOT `book_dir.name` — two different multi-volume series can both contain
    a literal `vol-01` subfolder, and the bare dir name collides across them.
    """
    out = []
    for _status, _bucket, book_dir in iter_content():
        if (book_dir / "book" / "book.md").is_file():
            out.append((slug_of(book_dir), book_dir))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("slugs", nargs="*", help="book slug(s); omit when using --all")
    ap.add_argument("--all", action="store_true", help="sweep every book with a reading edition")
    ap.add_argument("--dry-run", action="store_true", help="report only; spends no model calls")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.all:
        pairs = _every_book_slug()
    else:
        if not args.slugs:
            print("reconcile_articulation: give a slug or --all", file=sys.stderr)
            return 2
        pairs = []
        for slug in args.slugs:
            book_dir = _resolve_book_dir(slug)
            pairs.append((slug, book_dir))

    results = []
    log = (lambda *a: None) if args.json else print
    for slug, book_dir in pairs:
        if book_dir is None or not book_dir.is_dir():
            results.append({"slug": slug, "status": "not-found"})
            continue
        result = reconcile_one(slug, book_dir, dry_run=args.dry_run, log=log)
        results.append(result)
        if not args.json:
            print(f"  {slug}: {result['status']} — {result.get('note', '')}")

    ok_statuses = {"clean", "resolved", "needs-reconcile"} if args.dry_run else {"clean", "resolved"}
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        clean = sum(1 for r in results if r["status"] in ("clean", "resolved"))
        print(f"\n{clean}/{len(results)} clean" + (" (dry run — nothing changed)" if args.dry_run else ""))

    return 0 if all(r["status"] in ok_statuses for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
