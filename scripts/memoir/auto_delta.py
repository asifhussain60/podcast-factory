#!/usr/bin/env python3
"""
auto_delta.py — Automated delta management for all memoir chapters.

Two modes:

  CHECK (default):
    Scans every chapter file in the journal folder, runs delta detection on each,
    and prints a unified report. Run this at the START of every journal session.

    python auto_delta.py <journal_folder>

  SAVE:
    Saves snapshots for every chapter in the journal folder.
    Run this at the END of every journal session, after all files are saved.

    python auto_delta.py <journal_folder> --save

The agent calls one of these two commands automatically — you never need to manage
snapshots or delta checks manually.
"""

import sys
import os
import glob
import json
import shutil
from datetime import datetime

# Resolve the scripts directory and import sibling modules
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from detect_user_delta import detect_delta, print_readable_report
from save_snapshot import save_snapshot


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_chapter_files(journal_folder):
    """Return all chapter .txt files, excluding snapshot files."""
    patterns = [
        os.path.join(journal_folder, 'intro*.txt'),
        os.path.join(journal_folder, 'ch*.txt'),
    ]
    found = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if not path.endswith('-snapshot.txt'):
                found.append(path)
    return found


# ---------------------------------------------------------------------------
# CHECK mode
# ---------------------------------------------------------------------------

def check_all(journal_folder):
    """Run delta detection on all chapters and print a unified report."""
    chapters = find_chapter_files(journal_folder)
    if not chapters:
        print(f"No chapter files found in: {journal_folder}")
        return {}

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*60}")
    print(f"  AUTO DELTA CHECK — {timestamp}")
    print(f"  {len(chapters)} chapter(s) scanned")
    print(f"{'='*60}\n")

    all_results = {}
    total_protected = 0
    total_splits = 0
    total_punct = 0
    total_translations = 0
    chapters_with_changes = []

    for chapter_path in chapters:
        name = os.path.basename(chapter_path)
        result = detect_delta(chapter_path)
        all_results[chapter_path] = result

        protected = result['protected_count']
        splits    = result['paragraph_split_count']
        punct     = result['punctuation_change_count']
        trans     = len(result['translation_changes'])

        total_protected    += protected
        total_splits       += splits
        total_punct        += punct
        total_translations += trans

        if protected > 0 or trans > 0:
            chapters_with_changes.append(name)

        # Per-chapter summary line
        if not result['has_snapshot']:
            status = "NO SNAPSHOT (first run — all content available)"
        elif protected == 0 and trans == 0:
            status = "no user changes"
        else:
            parts = []
            if protected:
                parts.append(f"{protected} protected para(s)")
            if splits:
                parts.append(f"{splits} split(s)")
            if punct:
                parts.append(f"{punct} punctuation change(s)")
            if trans:
                parts.append(f"{trans} translation change(s) — SYNC REQUIRED")
            status = ", ".join(parts)

        print(f"  {name:<45} {status}")

    print(f"\n{'─'*60}")
    print(f"  TOTALS: {total_protected} protected para(s) | "
          f"{total_splits} split(s) | "
          f"{total_punct} punctuation | "
          f"{total_translations} translation update(s)")

    if total_translations > 0:
        print(f"\n  *** TRANSLATION SYNC REQUIRED ***")
        print(f"  Update translations-glossary.md and apply across all chapters")
        print(f"  before writing any revised content.\n")
        for chapter_path, result in all_results.items():
            if result['translation_changes']:
                print(f"  {os.path.basename(chapter_path)}:")
                for tc in result['translation_changes']:
                    if tc['kind'] == 'changed':
                        print(f"    '{tc['word']}': ({tc['old_translation']}) → ({tc['new_translation']})")
                    else:
                        print(f"    '{tc['word']}': [new] → ({tc['new_translation']})")

    if chapters_with_changes:
        print(f"\n  CHAPTERS WITH USER EDITS (protected):")
        for name in chapters_with_changes:
            print(f"    {name}")
        print(f"\n  Run individual chapter detail with:")
        print(f"    python detect_user_delta.py <chapter_file>")

    print(f"\n{'='*60}\n")

    # Full JSON to stderr for programmatic use
    print(json.dumps(
        {os.path.basename(k): v for k, v in all_results.items()},
        indent=2
    ), file=sys.stderr)

    return all_results


# ---------------------------------------------------------------------------
# SAVE mode
# ---------------------------------------------------------------------------

def save_all(journal_folder):
    """Save snapshots for all chapters. Run after all files are written for the session."""
    chapters = find_chapter_files(journal_folder)
    if not chapters:
        print(f"No chapter files found in: {journal_folder}")
        return

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*60}")
    print(f"  AUTO SNAPSHOT SAVE — {timestamp}")
    print(f"  {len(chapters)} chapter(s) found")
    print(f"{'='*60}\n")

    updated = 0
    skipped = 0

    for chapter_path in chapters:
        name     = os.path.basename(chapter_path)
        snap_dir = os.path.join(os.path.dirname(os.path.abspath(chapter_path)), 'snapshots')
        os.makedirs(snap_dir, exist_ok=True)
        snap     = os.path.join(snap_dir, os.path.splitext(os.path.basename(chapter_path))[0] + '-snapshot' + os.path.splitext(chapter_path)[1])
        size     = os.path.getsize(chapter_path)

        # Skip if already identical
        if os.path.exists(snap):
            with open(chapter_path, 'r', encoding='utf-8') as f:
                current = f.read()
            with open(snap, 'r', encoding='utf-8') as f:
                existing = f.read()
            if current.strip() == existing.strip():
                print(f"  [UNCHANGED] {name}  ({size} bytes)")
                skipped += 1
                continue

        shutil.copy2(chapter_path, snap)
        print(f"  [SAVED]     {name}  →  {os.path.basename(snap)}  ({size} bytes)")
        updated += 1

    print(f"\n  {updated} snapshot(s) saved. {skipped} already current.")
    print(f"  User edits after {timestamp} will be detected in the next session.")
    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python auto_delta.py <journal_folder>          # check all deltas")
        print("  python auto_delta.py <journal_folder> --save   # save all snapshots")
        sys.exit(1)

    # Parse args — folder can be first or second, --save flag optional
    journal_folder = None
    save_mode = False

    for arg in args:
        if arg == '--save':
            save_mode = True
        else:
            journal_folder = arg

    if not journal_folder:
        print("Error: journal folder path required.", file=sys.stderr)
        sys.exit(1)

    if save_mode:
        save_all(journal_folder)
    else:
        check_all(journal_folder)
