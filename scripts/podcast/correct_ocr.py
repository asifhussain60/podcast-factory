#!/usr/bin/env python3
"""correct_ocr.py — a recorded, reversible correction to a scan.

THE SCAN IS GROUND TRUTH, which is exactly why editing it needs a paper trail. The
Arabic source under `_system/source/ocr/` is what every later phase quotes, aligns
and vowels against; a silent character change there would propagate into the
edition with nothing anywhere to say it had happened, and no way to tell a genuine
manuscript reading from a fixed typo six months later.

So a correction is DECLARED first, in a tracked ledger beside the scan
(`corrections.json`), with the reading the scan carries, the reading it should
carry, and the evidence for saying so. This applies what the ledger declares and
stamps each entry with when it was applied and to what.

FIRST USE (Asif approved, 2026-07-30). Two entries, both single-dot scanner errors
that the vowelling gate surfaced by refusing to mark the passages around them:

    دعوثكم -> دعوتكم   "I called you". Root د-ع-و, 212 occurrences in the Quranic
                       corpus; دعوث is not a word. ت and ث differ by one dot.
    الجأهم -> ألجأهم   "drove them to". An initial hamza read as the article.

THE VOWELLED SIBLING IS KEPT IN STEP, and this is the part that is easy to get
wrong. `_vowelled_source.is_current` compares the scan's sha256 against the one
recorded when the sibling was written, so editing the scan alone would mark a
perfectly good vowelling stale and send every reader back to the bare text — the
whole book's marks lost to a two-character fix. The same correction is applied to
both files and the recorded hash is re-stamped, after which
`vowel_source.py --retry-refused` marks the two runs that were being refused.

    python3 scripts/podcast/correct_ocr.py the-master-and-the-disciple
    python3 scripts/podcast/correct_ocr.py the-master-and-the-disciple --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import REPO_ROOT, content_dir  # noqa: E402
from _vowelled_source import sibling_for, write_atomic  # noqa: E402

LEDGER = Path("_system/source/ocr/corrections.json")
SCAN = Path("_system/source/ocr/raw-extract.md")
VOWELLING_REPORT = Path("_system/source-vowelling.json")


def load_ledger(book_dir: Path) -> dict:
    path = book_dir / LEDGER
    if not path.exists():
        return {"schema": "ocr.corrections/v1", "corrections": []}
    return json.loads(path.read_text(encoding="utf-8"))


def apply_corrections(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    apply: bool = False,
    stamp: str = "",
) -> dict:
    """Apply every unapplied correction the ledger declares. Returns a summary."""
    ledger = load_ledger(book_dir)
    pending = [c for c in ledger.get("corrections", []) if not c.get("applied_at")]
    if not pending:
        log("    no unapplied corrections declared")
        return {"applied": 0}

    scan = book_dir / SCAN
    sibling = sibling_for(scan)
    if not scan.exists():
        log("    no scan to correct")
        return {"applied": 0}

    scan_text = scan.read_text(encoding="utf-8")
    sib_text = sibling.read_text(encoding="utf-8") if sibling.exists() else None

    done = 0
    for c in pending:
        wrong, right = c.get("wrong", ""), c.get("right", "")
        want = int(c.get("occurrences", 1))
        found = scan_text.count(wrong)
        if not wrong or not right or found != want:
            # Refuse the whole entry rather than guess which occurrence was meant.
            log(f"    REFUSED {wrong!r}: expected {want} occurrence(s) in the scan, found {found}")
            continue
        scan_text = scan_text.replace(wrong, right)
        if sib_text is not None:
            in_sib = sib_text.count(wrong)
            if in_sib == want:
                sib_text = sib_text.replace(wrong, right)
            else:
                # The sibling carries this run vowelled, so the bare string does not
                # occur there. Say so — that run needs re-vowelling, not patching.
                log(f"    note: {wrong!r} not found bare in the sibling ({in_sib}) — re-vowel that run")
        log(f"    {wrong} -> {right}   ({c.get('evidence', 'no evidence recorded')})")
        c["applied_at"] = stamp
        done += 1

    if not apply or not done:
        log(f"    {done} correction(s) would be applied")
        return {"applied": done}

    write_atomic(scan, scan_text)
    if sib_text is not None:
        write_atomic(sibling, sib_text)
    # Re-stamp the hash the staleness check reads, or the sibling we just kept in
    # step would be declared stale and every mark in the book would go unread.
    report_path = book_dir / VOWELLING_REPORT
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        entry = (report.get("streams") or {}).get(SCAN.as_posix())
        if entry:
            entry["source_sha256"] = hashlib.sha256(scan_text.encode("utf-8")).hexdigest()
            write_atomic(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            log("    re-stamped the vowelling report's source hash")
    write_atomic(book_dir / LEDGER, json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    log(f"    {done} correction(s) applied to the scan and its vowelled sibling")
    return {"applied": done}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply the OCR corrections a book's ledger declares.",
        epilog="Dry run by default. Declare corrections in _system/source/ocr/corrections.json first.",
    )
    ap.add_argument("slug")
    ap.add_argument("--apply", action="store_true", help="write the scan, the sibling and the ledger")
    ap.add_argument("--stamp", default="", help="value recorded as applied_at (an ISO date)")
    a = ap.parse_args()

    book_dir = content_dir(a.slug)
    if not book_dir or not book_dir.exists():
        print(f"Book not found: {a.slug}", file=sys.stderr)
        return 1
    if not a.apply:
        print("DRY RUN — nothing is written. Pass --apply.\n")
    try:
        label = book_dir.relative_to(REPO_ROOT / "content")
    except ValueError:  # pragma: no cover
        label = book_dir
    print(f"==> {label}")
    apply_corrections(book_dir, apply=a.apply, stamp=a.stamp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
