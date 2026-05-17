#!/usr/bin/env python3
"""
refresh_all_snapshots.py — Locks in the current state of ALL chapter files as the new delta baseline.

Usage:
    python refresh_all_snapshots.py <journal_folder>
    python refresh_all_snapshots.py  (defaults to folder containing this script's parent/Journal)

Run this any time you want to say "everything right now is correct — this is the new baseline."
After running, the next agent revision will detect only changes you make AFTER this point.

When to run manually:
  - After making a batch of your own edits across multiple chapters
  - After installing a new version of the journal skill (to re-baseline from current files)
  - Any time you're unsure whether snapshots are current

What it does:
  - Finds every ch*.txt and intro*.txt chapter file (skips *-snapshot.txt files)
  - Copies each one to its corresponding *-snapshot.txt baseline
  - Reports what was updated, with file sizes and timestamps

It does NOT modify the chapter files themselves — only the snapshot copies.
"""

import sys
import os
import shutil
import glob
from datetime import datetime
from pathlib import Path

# Reuse the canonical snapshot-path function so the two scripts cannot drift.
sys.path.insert(0, str(Path(__file__).parent))
from save_snapshot import get_snapshot_path


def is_snapshot_file(path):
    return os.path.basename(path).endswith('-snapshot.txt')


def find_chapter_files(journal_folder):
    """Find all chapter .txt files, excluding snapshot files."""
    patterns = [
        os.path.join(journal_folder, 'intro*.txt'),
        os.path.join(journal_folder, 'ch*.txt'),
    ]
    found = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if not is_snapshot_file(path):
                found.append(path)
    return found


def refresh_all(journal_folder):
    if not os.path.isdir(journal_folder):
        print(f"Error: folder not found: {journal_folder}", file=sys.stderr)
        sys.exit(1)

    chapters = find_chapter_files(journal_folder)
    if not chapters:
        print(f"No chapter files found in: {journal_folder}")
        sys.exit(0)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n--- SNAPSHOT REFRESH ---")
    print(f"Folder    : {journal_folder}")
    print(f"Timestamp : {timestamp}")
    print(f"Chapters  : {len(chapters)} found\n")

    updated = []
    for chapter_path in chapters:
        snapshot_path = get_snapshot_path(chapter_path)
        chapter_size = os.path.getsize(chapter_path)

        # Check if snapshot already exists and is identical
        if os.path.exists(snapshot_path):
            snap_size = os.path.getsize(snapshot_path)
            with open(chapter_path, 'r', encoding='utf-8') as f:
                current = f.read()
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                existing = f.read()
            if current.strip() == existing.strip():
                print(f"  [UNCHANGED] {os.path.basename(chapter_path)}  ({chapter_size} bytes) — snapshot already current")
                continue

        shutil.copy2(chapter_path, snapshot_path)
        print(f"  [UPDATED]   {os.path.basename(chapter_path)}  →  {os.path.basename(snapshot_path)}  ({chapter_size} bytes)")
        updated.append(chapter_path)

    print(f"\n{len(updated)} snapshot(s) updated. {len(chapters) - len(updated)} already current.")
    print(f"The next agent revision will protect only changes made after {timestamp}.")
    print("--- END SNAPSHOT REFRESH ---\n")


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        journal_folder = sys.argv[1]
    else:
        # Default: look for Journal folder relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # script is in journal-skill/scripts/ — Journal folder is typically mnt/Journal
        journal_folder = os.path.join(script_dir, '..', '..', '..', 'Journal')
        journal_folder = os.path.abspath(journal_folder)

    refresh_all(journal_folder)
