#!/usr/bin/env python3
"""intake_book.py — automate the manual setup that precedes per-chapter authoring
for a new book in the podcast pipeline (Phase 7.5 of the intelligence-enhancements plan).

What it does:
  1. Creates a typed content worktree via scripts/start-content-worktree.sh, so the
     new branch (e.g. book/<slug>) lives at <projects-root>/git-worktrees/<slug>/.
  2. Copies the source PDF from raw/<pdf-name> → <worktree>/content/drafts/<slug>/_source/.
  3. Creates the workspace skeleton inside the worktree:
       content/drafts/<slug>/
         _source/        — raw inputs (.pdf, .mp3, .docx, .txt)
         _system/        — orchestrator state + per-book references
         chapters/       — author-emitted chapter source texts
         episodes/       — NotebookLM-ready episode .txts
         episode-drafts/ — per-EP framings under draft (.md)
  4. Initializes _system/orchestrator-state.json with phase=preflight inside the worktree.
  5. Prints the next-action: cd to the worktree, then orchestrate_book.py --start.

What it does NOT do:
  - Author chapters or framings (that's the orchestrator + Step D pattern).
  - Mutate develop or any other branch.
  - Push the new branch (operator decides when).

Usage:
  scripts/podcast/intake_book.py <pdf-path> <book-slug> [--category books]

Examples:
  scripts/podcast/intake_book.py raw/Ayyuhal\\ Walad.pdf ayyuhal-walad --category letters
  scripts/podcast/intake_book.py raw/asaas-al-taveel.pdf asaas-al-taveel
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT.parent.parent / "raw"  # podcast-factory/raw/, outside the worktree

SKELETON_DIRS = ["_source", "_system", "chapters", "episodes", "episode-drafts"]

SLUG_RE_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _die(msg: str) -> None:
    print(f"intake_book: {msg}", file=sys.stderr)
    sys.exit(2)


def _info(msg: str) -> None:
    print(msg)


def _primary_repo_root() -> Path:
    """The PRIMARY clone's working tree (not the current worktree, if invoked from one).

    `git rev-parse --git-common-dir` always points at the shared .git/; its parent
    IS the primary clone. Lets the script run correctly whether invoked from the
    primary checkout or from any sibling worktree.
    """
    out = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    common = Path(out)
    if not common.is_absolute():
        common = (REPO_ROOT / common).resolve()
    return common.parent


def _worktree_path_for(slug: str) -> Path:
    """Where the content worktree lives: <projects-root>/git-worktrees/<slug>/."""
    return _primary_repo_root().parent / "git-worktrees" / slug


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_path", help="Source PDF/EPUB path (relative or absolute)")
    parser.add_argument("slug", help="Book slug (lowercase-with-hyphens, kebab-case)")
    parser.add_argument("--category", default="books",
                        choices=["books", "documents", "lectures", "articles",
                                 "letters", "interviews"],
                        help="Content category (drives branch prefix; default: books)")
    parser.add_argument("--no-worktree", action="store_true",
                        help="Skip worktree creation (skeleton-only; assumes you're already "
                             "in the right worktree)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing workspace skeleton inside the worktree")
    args = parser.parse_args()

    import re
    if not re.match(SLUG_RE_PATTERN, args.slug):
        _die(f"slug '{args.slug}' must be lowercase-kebab-case (a-z, 0-9, hyphens)")

    # Resolve source PDF (from primary clone's raw/ dir, or absolute, or cwd)
    src = Path(args.pdf_path).expanduser()
    if not src.is_absolute():
        for candidate in [RAW_DIR / src, Path.cwd() / src, REPO_ROOT / src]:
            if candidate.exists():
                src = candidate
                break
    if not src.exists():
        _die(f"source not found: {args.pdf_path} (looked under {RAW_DIR}, cwd, and repo root)")

    # Create the typed content worktree via the helper script (unless explicitly skipped).
    # Helper handles: fetch origin/develop, create branch, unset upstream foot-gun,
    # and is idempotent if the branch/worktree already exists.
    primary = _primary_repo_root()
    helper = primary / "scripts" / "start-content-worktree.sh"
    if not args.no_worktree:
        if not helper.exists():
            _die(f"helper not found: {helper}\n  "
                 f"Expected scripts/start-content-worktree.sh on the primary clone.")
        _info(f"==> Provisioning content worktree via {helper.name}")
        r = subprocess.run(
            ["bash", str(helper), args.category, args.slug],
            cwd=primary, capture_output=False,
        )
        if r.returncode != 0:
            _die(f"worktree helper failed (exit {r.returncode})")

    # All workspace files land in the worktree (NOT the primary checkout) — that way
    # they appear on the new branch directly, no manual checkout step.
    worktree_root = _worktree_path_for(args.slug) if not args.no_worktree else REPO_ROOT
    book_dir = worktree_root / "content" / "drafts" / args.slug

    if book_dir.exists() and not args.force:
        _die(f"book workspace already exists: {book_dir}\n  "
             f"Use --force to overwrite or pick a different slug.")

    if args.force and book_dir.exists():
        _info(f"==> Removing existing workspace at {book_dir} (--force)")
        shutil.rmtree(book_dir)

    # Create skeleton inside the worktree
    rel_book_dir = book_dir.relative_to(worktree_root)
    _info(f"==> Creating workspace at {rel_book_dir} (in worktree {worktree_root.name})")
    for d in SKELETON_DIRS:
        (book_dir / d).mkdir(parents=True, exist_ok=True)
    _info(f"    Skeleton dirs: {', '.join(SKELETON_DIRS)}")

    # Copy source PDF into the worktree
    dst_pdf = book_dir / "_source" / src.name
    shutil.copy2(src, dst_pdf)
    _info(f"    Copied source: {src.name} → {dst_pdf.relative_to(worktree_root)}")

    # Initialize orchestrator-state.json inside the worktree
    state = {
        "schema_version": 1,
        "book_slug": args.slug,
        "source_path": str(dst_pdf.relative_to(worktree_root)),
        "phase": "preflight",
        "phase_status": "pending",
        "last_completed_phase": None,
        "last_error": None,
        "category": args.category,
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phases": {},
        "intake_via": "scripts/podcast/intake_book.py",
    }
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    _info(f"    state.json: phase=preflight, phase_status=pending, category={args.category}")

    _info("")
    _info(f"==> DONE. Next steps:")
    if not args.no_worktree:
        _info(f"    1. cd {worktree_root}")
        _info(f"    2. python3 scripts/podcast/orchestrate_book.py --start "
              f"{dst_pdf.relative_to(worktree_root)} --slug {args.slug}")
        _info(f"    3. Watch Phase 0a (OCR) run; advance through 0b/0c/0d as gates clear.")
    else:
        _info(f"    1. python3 scripts/podcast/orchestrate_book.py --start "
              f"{dst_pdf.relative_to(worktree_root)} --slug {args.slug}")
        _info(f"    2. Watch Phase 0a (OCR) run; advance through 0b/0c/0d as gates clear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
