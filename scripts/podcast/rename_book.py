#!/usr/bin/env python3
"""rename_book.py — atomically rename a standalone book's slug.

A slug is an identity key duplicated across the system; this renames ALL of it
as one guarded operation:
  1. the content folder            content/<Bucket>/<old> -> <new>   (git mv)
  2. the git branch                <Bucket>/<old> -> <Bucket>/<new>   (git branch -m)
  3. meta.yml                      slug:
  4. orchestrator-state.json       book_slug
  5. the site card-meta            plan-dashboard/src/lib/book-card-meta.ts  '<old>': -> '<new>':
  6. knowledge.db                  atoms.first_seen_book, atoms_sources.book_slug, atoms_variants.book_slug
  7. cross-book usage ledger       content/knowledge-base/cross-book-usage-ledger.json  by_book key

Pre-flight guards (refuses rather than half-renames):
  - new slug is kebab-case and differs from the old
  - the working tree is clean (no unrelated uncommitted changes to entangle)
  - no folder OR branch collision on the new slug
  - VOLUME slugs (<work>-vol-NN, inside a work parent) are refused — series-structural.

--dry-run prints the full plan and touches nothing. On a mid-run failure after the
folder move, the move is rolled back so the book is never left split.

Usage:
  python3 scripts/podcast/rename_book.py <old-slug> <new-slug> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _branching import branch_name
from _paths import REPO_ROOT, find_content, is_work_parent

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CARD_META = REPO_ROOT / "plan-dashboard" / "src" / "lib" / "book-card-meta.ts"
KNOWLEDGE_DB = REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"
XBOOK_LEDGER = REPO_ROOT / "content" / "knowledge-base" / "cross-book-usage-ledger.json"


def _die(msg: str) -> int:
    print(f"rename_book: ERROR — {msg}", file=sys.stderr)
    return 2


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=check)


def _read_profile(meta_path: Path) -> str | None:
    if not meta_path.exists():
        return None
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("content_profile:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def rename_book(old: str, new: str, *, dry_run: bool = False) -> int:
    if not SLUG_RE.match(new):
        return _die(f"new slug {new!r} must be lowercase-kebab-case")
    if new == old:
        return _die("new slug equals old slug — nothing to do")

    hit = find_content(old)
    if not hit:
        return _die(f"book {old!r} not found")
    _status, bucket, old_dir = hit
    old_dir = Path(old_dir)

    # Refuse volume / work-parent renames (series-structural).
    if is_work_parent(old_dir) or re.match(r"^vol-\d+$", old_dir.name) or re.search(r"-vol-\d+$", old):
        return _die(
            f"{old!r} is a multi-volume series volume/parent — series-structural renames "
            f"are out of scope (would desync work.yml ordering)."
        )

    new_dir = old_dir.parent / new
    old_branch = branch_name(None, old, profile=_read_profile(old_dir / "meta.yml"), bucket=bucket)
    new_branch = branch_name(None, new, profile=_read_profile(old_dir / "meta.yml"), bucket=bucket)

    # ── Pre-flight guards ────────────────────────────────────────────────────
    if new_dir.exists():
        return _die(f"target folder already exists: {new_dir.relative_to(REPO_ROOT)}")
    if _git("rev-parse", "--verify", new_branch, check=False).returncode == 0:
        return _die(f"target branch already exists: {new_branch}")
    porcelain = _git("status", "--porcelain").stdout
    tracked_changes = [ln for ln in porcelain.splitlines() if ln and not ln.startswith("??")]
    if tracked_changes:
        return _die(
            "working tree has uncommitted tracked changes — commit or stash first so the "
            "rename can't entangle them:\n" + "\n".join(tracked_changes[:20])
        )

    branch_exists = _git("rev-parse", "--verify", old_branch, check=False).returncode == 0

    plan = [
        f"folder    : content/{bucket}/{old}  ->  content/{bucket}/{new}",
        f"branch    : {old_branch}  ->  {new_branch}" + ("" if branch_exists else "  (branch absent — skip)"),
        f"meta.yml  : slug: {old}  ->  slug: {new}",
        f"state.json: book_slug {old}  ->  {new}",
        f"card-meta : '{old}':  ->  '{new}':" + ("" if CARD_META.exists() else "  (file absent — skip)"),
        f"knowledge.db: atoms/atoms_sources/atoms_variants book refs {old} -> {new}",
        f"x-book ledger: by_book['{old}'] -> by_book['{new}']" + ("" if XBOOK_LEDGER.exists() else "  (absent — skip)"),
    ]
    print(f"==> Rename plan for {old!r} -> {new!r}:")
    for p in plan:
        print(f"    {p}")
    if dry_run:
        print("==> --dry-run: nothing changed.")
        return 0

    # ── Execute (folder move last-but-one; rollback the move on later failure) ─
    moved = False
    try:
        # 1. card-meta (outside the book dir) — rename the key.
        if CARD_META.exists():
            txt = CARD_META.read_text(encoding="utf-8")
            key_re = re.compile(rf"(^\s*['\"]){re.escape(old)}(['\"]\s*:\s*\{{)", re.M)
            if key_re.search(txt):
                CARD_META.write_text(key_re.sub(rf"\g<1>{new}\g<2>", txt, count=1), encoding="utf-8")
                print("    ok card-meta key")

        # 2. knowledge.db
        if KNOWLEDGE_DB.exists():
            import sqlite3

            conn = sqlite3.connect(str(KNOWLEDGE_DB))
            try:
                conn.execute("UPDATE atoms SET first_seen_book=? WHERE first_seen_book=?", (new, old))
                conn.execute("UPDATE atoms_sources SET book_slug=? WHERE book_slug=?", (new, old))
                conn.execute("UPDATE atoms_variants SET book_slug=? WHERE book_slug=?", (new, old))
                conn.commit()
            finally:
                conn.close()
            print("    ok knowledge.db atom refs")

        # 3. cross-book ledger key
        if XBOOK_LEDGER.exists():
            led = json.loads(XBOOK_LEDGER.read_text(encoding="utf-8"))
            bb = led.get("by_book") or {}
            if old in bb:
                bb[new] = bb.pop(old)
                led["by_book"] = bb
                XBOOK_LEDGER.write_text(json.dumps(led, indent=2) + "\n", encoding="utf-8")
                print("    ok cross-book ledger key")

        # 4. folder move — shutil so gitignored audio + untracked artifacts move too
        #    (plain `git mv` would leave them orphaned). Git rename-detects the
        #    tracked files when the move is staged.
        shutil.move(str(old_dir), str(new_dir))
        moved = True
        _git("add", "-A", str(old_dir.relative_to(REPO_ROOT)), check=False)
        _git("add", str(new_dir.relative_to(REPO_ROOT)), check=False)
        print("    ok moved folder (+ staged)")

        # 5. meta.yml slug + orchestrator-state book_slug (now in the new dir)
        meta_path = new_dir / "meta.yml"
        if meta_path.exists():
            mtxt = meta_path.read_text(encoding="utf-8")
            mtxt = re.sub(r"^slug:\s*.*$", f"slug: {new}", mtxt, count=1, flags=re.M)
            meta_path.write_text(mtxt, encoding="utf-8")
            print("    ok meta.yml slug")
        state_path = new_dir / "_system" / "orchestrator-state.json"
        if state_path.exists():
            st = json.loads(state_path.read_text(encoding="utf-8"))
            st["book_slug"] = new
            state_path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
            print("    ok orchestrator-state book_slug")

        # 6. git branch rename
        if branch_exists:
            _git("branch", "-m", old_branch, new_branch)
            print("    ok git branch -m")

    except Exception as e:
        if moved and new_dir.exists():
            shutil.move(str(new_dir), str(old_dir))
            _git("add", "-A", str(old_dir.relative_to(REPO_ROOT)), check=False)
            _git("add", "-A", str(new_dir.relative_to(REPO_ROOT)), check=False)
            print("    ⚠ rolled back the folder move after failure", file=sys.stderr)
        return _die(f"rename failed mid-run: {e}\n   review `git status` before retrying.")

    print(f"==> DONE. {old!r} -> {new!r}. Review `git status` / `git diff` and commit when satisfied.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("old_slug")
    ap.add_argument("new_slug")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return rename_book(a.old_slug, a.new_slug, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
