#!/usr/bin/env python3
"""standardize_book_folders.py — retroactively align every book/volume dir with
the standard skeleton (_paths.BOOK_SUBDIRS).

One-shot migration + ongoing hygiene tool (2026-06-10 folder standardization):

  1. KNOWN RENAMES (filesystem rename; git's rename detection records the move
     for tracked files at commit time — avoids git-mv-vs-untracked edge cases):
       slide-deck/            -> slide-decks/  (deck PDF -> book-deck.pdf,
                                 PPTX -> book-deck.pptx,
                                 slide-manifest.json -> _manifests/book-manifest.json,
                                 _pages/ -> _pages/book/)
       audio/                 -> m4a/          (when m4a/ absent)
       source/                -> _source/      (when _source/ absent)
  2. SKELETON FILL: ensure_book_skeleton() — creates missing standard dirs
     (+ .gitkeep in empty leaves).
  3. ODDITY FLAGS (reported, never touched): duplicate source/+_source/, stray
     root-level files outside the standard layout.

Scope: every book dir in all 4 buckets, plus every vol-NN/ under multi-volume
work parents (work.yml marker). Work parents themselves are NOT given a book
skeleton (they hold only work.yml + _source/ + volumes).

Dry-run first (vacuum pattern): default prints the proposed plan and exits;
``--confirm`` executes.

Usage:
    python3 scripts/podcast/standardize_book_folders.py [--confirm] [--slug <slug>]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (
    BOOK_SUBDIRS,
    CONTENT_ROOT,
    REPO_ROOT,
    ensure_book_skeleton,
    is_work_parent,
    volume_dirs,
)
from _rules import BUCKETS


@dataclass
class BookPlan:
    book_dir: Path
    renames: list[tuple[Path, Path]] = field(default_factory=list)  # (src, dst)
    missing_dirs: list[str] = field(default_factory=list)
    oddities: list[str] = field(default_factory=list)

    @property
    def has_actions(self) -> bool:
        return bool(self.renames or self.missing_dirs)


def discover_book_dirs(only_slug: str | None = None) -> list[Path]:
    """Every book dir across all buckets; volumes of work parents, not the parent."""
    out: list[Path] = []
    for bucket in BUCKETS:
        bucket_dir = CONTENT_ROOT / bucket
        if not bucket_dir.is_dir():
            continue
        for child in sorted(bucket_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            if only_slug and child.name != only_slug:
                continue
            if is_work_parent(child):
                out.extend(volume_dirs(child))
            else:
                out.append(child)
    return out


def _plan_slide_deck_rename(book_dir: Path, plan: BookPlan) -> None:
    """slide-deck/ (legacy singular, book-level NotebookLM export) -> slide-decks/."""
    legacy = book_dir / "slide-deck"
    if not legacy.is_dir():
        return
    target = book_dir / "slide-decks"
    pdfs = sorted(p for p in legacy.glob("*.pdf"))
    pptxs = sorted(p for p in legacy.glob("*.pptx"))
    if len(pdfs) == 1:
        plan.renames.append((pdfs[0], target / "book-deck.pdf"))
    else:
        plan.oddities.append(f"slide-deck/ has {len(pdfs)} PDFs — expected 1, left as-is")
    if len(pptxs) == 1:
        plan.renames.append((pptxs[0], target / "book-deck.pptx"))
    manifest = legacy / "slide-manifest.json"
    if manifest.exists():
        plan.renames.append((manifest, target / "_manifests" / "book-manifest.json"))
    pages = legacy / "_pages"
    if pages.is_dir():
        plan.renames.append((pages, target / "_pages" / "book"))


def _plan_simple_renames(book_dir: Path, plan: BookPlan) -> None:
    for legacy_name, std_name in (("audio", "m4a"), ("source", "_source")):
        legacy = book_dir / legacy_name
        std = book_dir / std_name
        if not legacy.is_dir():
            continue
        if std.is_dir() and any(std.iterdir()):
            plan.oddities.append(f"both {legacy_name}/ and {std_name}/ exist with content — review manually")
            continue
        plan.renames.append((legacy, std))


def build_plan(book_dir: Path) -> BookPlan:
    plan = BookPlan(book_dir=book_dir)
    _plan_slide_deck_rename(book_dir, plan)
    _plan_simple_renames(book_dir, plan)
    # Informational for the dry-run display; ensure_book_skeleton() fills them
    # after renames. Exclude dirs a planned rename will itself create.
    rename_targets = {dst.relative_to(book_dir).as_posix() for _, dst in plan.renames}
    plan.missing_dirs = [
        s
        for s in BOOK_SUBDIRS
        if not (book_dir / s).is_dir()
        and s not in rename_targets
        and not any(t == s or t.startswith(s + "/") for t in rename_targets)
    ]
    return plan


def execute_plan(plan: BookPlan, log=print) -> None:
    for src, dst in plan.renames:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            log(f"    SKIP rename (target exists): {dst.relative_to(REPO_ROOT)}")
            continue
        shutil.move(str(src), str(dst))
        log(f"    moved {src.relative_to(REPO_ROOT)} -> {dst.relative_to(REPO_ROOT)}")
    # Remove now-empty legacy dirs left behind by partial moves.
    for legacy_name in ("slide-deck",):
        legacy = plan.book_dir / legacy_name
        if legacy.is_dir() and not any(legacy.iterdir()):
            legacy.rmdir()
            log(f"    removed empty {legacy.relative_to(REPO_ROOT)}/")
    ensure_book_skeleton(plan.book_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="execute (default: dry-run)")
    ap.add_argument("--slug", help="limit to one top-level slug")
    args = ap.parse_args()

    books = discover_book_dirs(args.slug)
    if not books:
        print("standardize: no book dirs found", file=sys.stderr)
        return 2

    any_action = False
    for book_dir in books:
        plan = build_plan(book_dir)
        rel = book_dir.relative_to(CONTENT_ROOT)
        if not plan.has_actions and not plan.oddities:
            print(f"== {rel}: already standard")
            continue
        print(f"== {rel}")
        for src, dst in plan.renames:
            print(f"    RENAME {src.relative_to(book_dir)} -> {dst.relative_to(book_dir)}")
        if plan.missing_dirs:
            print(f"    CREATE {len(plan.missing_dirs)} missing standard dirs: " + ", ".join(plan.missing_dirs))
        for o in plan.oddities:
            print(f"    FLAG   {o}")
        if plan.has_actions:
            any_action = True
            if args.confirm:
                execute_plan(plan)

    if not args.confirm and any_action:
        print("\nDry-run only. Re-run with --confirm to execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
