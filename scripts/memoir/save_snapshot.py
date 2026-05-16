#!/usr/bin/env python3
"""
save_snapshot.py — Saves the current state of a chapter file as the agent's revision baseline.

Usage:
    python save_snapshot.py <chapter_file>
    python save_snapshot.py <chapter_file> <snapshot_file>

Call this immediately after the agent saves a revised chapter.
The snapshot becomes the new baseline for the next revision's delta detection.
Any changes the user makes after this point will be detected as user deltas
and protected from agent overwriting.

Snapshot naming convention:
    chapter_file = ch02-love.txt  →  snapshot = ch02-love-snapshot.txt
    Both files live in the same directory.
"""

import sys
import os
import shutil
from datetime import datetime


def get_snapshot_path(chapter_path):
    """Snapshots live under the sibling _system/snapshots/ folder of the chapter dir.

    Layout: content/babu-memoir/chapters/ch01-man.txt
            → content/babu-memoir/_system/snapshots/ch01-man-snapshot.txt
    """
    chapter_dir = os.path.dirname(os.path.abspath(chapter_path))
    base = os.path.splitext(os.path.basename(chapter_path))[0]
    ext  = os.path.splitext(chapter_path)[1]
    # Walk up one level (chapters/) then into _system/snapshots/
    book_dir = os.path.dirname(chapter_dir)
    snapshots_dir = os.path.join(book_dir, '_system', 'snapshots')
    os.makedirs(snapshots_dir, exist_ok=True)
    return os.path.join(snapshots_dir, f"{base}-snapshot{ext}")


def save_snapshot(chapter_path, snapshot_path=None):
    if not os.path.exists(chapter_path):
        print(f"Error: chapter file not found: {chapter_path}", file=sys.stderr)
        sys.exit(1)

    if snapshot_path is None:
        snapshot_path = get_snapshot_path(chapter_path)

    shutil.copy2(chapter_path, snapshot_path)

    # Confirm
    chapter_size = os.path.getsize(chapter_path)
    print(f"Snapshot saved: {snapshot_path} ({chapter_size} bytes)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Next revision will protect any user edits made after this point.")
    return snapshot_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python save_snapshot.py <chapter_file> [snapshot_file]")
        sys.exit(1)

    chapter_path = sys.argv[1]
    snapshot_path = sys.argv[2] if len(sys.argv) > 2 else None
    save_snapshot(chapter_path, snapshot_path)
