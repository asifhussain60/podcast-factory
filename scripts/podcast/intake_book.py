#!/usr/bin/env python3
"""intake_book.py — automate the manual setup that precedes per-chapter authoring
for a new book in the podcast pipeline (Phase 7.5 of the intelligence-enhancements plan).

What it does:
  1. Copies the source PDF from raw/<pdf-name> → content/drafts/<slug>/_source/<pdf-name>.
  2. Creates the workspace skeleton:
       content/drafts/<slug>/
         _source/        — raw inputs (.pdf, .mp3, .docx, .txt)
         _system/        — orchestrator state + per-book references
         chapters/       — author-emitted chapter source texts
         episodes/       — NotebookLM-ready episode .txts
         episode-drafts/ — per-EP framings under draft (.md)
  3. Initializes _system/orchestrator-state.json with phase=preflight.
  4. Creates the book/<slug> git branch off origin/develop (if origin reachable).
  5. Prints the next-action (operator runs orchestrate_book.py --start to begin Phase 0a).

What it does NOT do:
  - Author chapters or framings (that's the orchestrator + Step D pattern).
  - Mutate develop or any other branch.
  - Push the new branch (operator decides when).

Usage:
  scripts/podcast/intake_book.py <pdf-path> <book-slug>

Examples:
  scripts/podcast/intake_book.py raw/Ayyuhal\\ Walad.pdf ayyuhal-walad
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
WORKSPACE_BOOKS = REPO_ROOT / "content" / "drafts"
RAW_DIR = REPO_ROOT.parent.parent / "raw"  # podcast-factory/raw/, outside the worktree

SKELETON_DIRS = ["_source", "_system", "chapters", "episodes", "episode-drafts"]

SLUG_RE_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _die(msg: str) -> None:
    print(f"intake_book: {msg}", file=sys.stderr)
    sys.exit(2)


def _info(msg: str) -> None:
    print(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_path", help="Source PDF/EPUB path (relative or absolute)")
    parser.add_argument("slug", help="Book slug (lowercase-with-hyphens, kebab-case)")
    parser.add_argument("--no-branch", action="store_true",
                        help="Skip git branch creation (workspace setup only)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing workspace skeleton")
    args = parser.parse_args()

    import re
    if not re.match(SLUG_RE_PATTERN, args.slug):
        _die(f"slug '{args.slug}' must be lowercase-kebab-case (a-z, 0-9, hyphens)")

    # Resolve source PDF
    src = Path(args.pdf_path).expanduser()
    if not src.is_absolute():
        # Try relative to REPO_ROOT/raw first, then cwd, then absolute
        for candidate in [RAW_DIR / src, Path.cwd() / src, REPO_ROOT / src]:
            if candidate.exists():
                src = candidate
                break
    if not src.exists():
        _die(f"source not found: {args.pdf_path} (looked under {RAW_DIR}, cwd, and repo root)")

    book_dir = WORKSPACE_BOOKS / args.slug
    if book_dir.exists() and not args.force:
        _die(f"book workspace already exists: {book_dir}\n  Use --force to overwrite or pick a different slug.")

    if args.force and book_dir.exists():
        _info(f"==> Removing existing workspace at {book_dir} (--force)")
        shutil.rmtree(book_dir)

    # Create skeleton
    _info(f"==> Creating workspace at {book_dir.relative_to(REPO_ROOT)}")
    for d in SKELETON_DIRS:
        (book_dir / d).mkdir(parents=True, exist_ok=True)
    _info(f"    Skeleton dirs: {', '.join(SKELETON_DIRS)}")

    # Copy source PDF
    dst_pdf = book_dir / "_source" / src.name
    shutil.copy2(src, dst_pdf)
    _info(f"    Copied source: raw/{src.name} → {dst_pdf.relative_to(REPO_ROOT)}")

    # Initialize orchestrator-state.json
    state = {
        "schema_version": 1,
        "book_slug": args.slug,
        "source_path": str(dst_pdf.relative_to(REPO_ROOT)),
        "phase": "preflight",
        "phase_status": "pending",
        "last_completed_phase": None,
        "last_error": None,
        "category": "books",
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phases": {},
        "intake_via": "scripts/podcast/intake_book.py",
    }
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    _info(f"    state.json: phase=preflight, phase_status=pending")

    # Create book branch
    if not args.no_branch:
        branch = f"book/{args.slug}"
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=REPO_ROOT, capture_output=True, text=True
        )
        if result.returncode == 0:
            _info(f"==> Branch already exists: {branch} (skipping)")
        else:
            _info(f"==> Creating branch {branch} from develop")
            r = subprocess.run(
                ["git", "branch", branch, "develop"],
                cwd=REPO_ROOT, capture_output=True, text=True
            )
            if r.returncode != 0:
                _info(f"    WARN: could not create branch — {r.stderr.strip()}")
            else:
                _info(f"    Created. Switch with: git checkout {branch}")

    _info("")
    _info(f"==> DONE. Next steps:")
    _info(f"    1. (optional) git checkout book/{args.slug}")
    _info(f"    2. python3 scripts/podcast/orchestrate_book.py --start {dst_pdf.relative_to(REPO_ROOT)} --slug {args.slug}")
    _info(f"    3. Watch Phase 0a (OCR) run; advance through 0b/0c/0d as gates clear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
