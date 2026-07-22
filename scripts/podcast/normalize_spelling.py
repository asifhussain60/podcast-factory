#!/usr/bin/env python3
"""normalize_spelling.py — sweep existing deliverables to American spelling.

New books get this inside `compose_book_v2`; this is the one-time backfill for
everything already produced, and the tool to re-run if a hand edit reintroduces
a British form.

SCOPE IS THE POINT. Only files the pipeline AUTHORS are eligible:

    <book>/book/book.md          the reading edition
    <book>/chapters/*.txt        the NotebookLM sources
    <book>/episodes/*.txt        the episode framings
    <book>/slide-decks/*         the deck bundles

Everything else is excluded by construction — OCR extracts and anything under
`_system/source/`, the shared source library, third-party material under
`research/`, and the `_chunks/` compose caches. Those are evidence. Respelling a
source record would break the verbatim guarantee the pipeline rests on, and a
quoted scholar does not get their prose Americanized.

Usage:
    python3 scripts/podcast/normalize_spelling.py                 # dry run, all books
    python3 scripts/podcast/normalize_spelling.py <slug>          # dry run, one book
    python3 scripts/podcast/normalize_spelling.py --apply         # write
    python3 scripts/podcast/normalize_spelling.py --apply --no-usage
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _american_spelling import findings, to_american  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "content"

# A path segment here disqualifies the file no matter what else matches.
#
# `augmentation` earns its place the hard way: those directories hold TRANSCRIBED
# LECTURES — a real person's recorded speech, used as grounding input — and they
# sit under a `chapters/` subdirectory, so the "is it a chapter?" test below
# happily claimed 78 of them on the first run (caught before commit, 2026-07-21).
# Nobody's spoken words get Americanized.
EXCLUDE_PARTS = {
    "_chunks",
    "_curator-archive",
    "_preview-cache",
    "augmentation",
    "research",
    "source-library",
    "knowledge-base",
}


def in_scope(path: Path) -> bool:
    """Does this PATH name prose the pipeline authored? Pure — touches no disk.

    Separated from `eligible` so the boundary can be tested against paths that
    do not exist, which is the only way to assert what must NEVER be swept
    without first creating a decoy transcript on disk.
    """
    if path.suffix not in {".md", ".txt"}:
        return False
    if set(path.parts) & EXCLUDE_PARTS:
        return False
    s = path.as_posix()
    if "/_system/source/" in s:
        return False
    return s.endswith("/book/book.md") or "/chapters/" in s or "/episodes/" in s or "/slide-decks/" in s


def eligible(path: Path) -> bool:
    """`in_scope` plus "and it is a real file" — what the sweep actually uses."""
    return in_scope(path) and path.is_file()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="?", help="limit to one book slug")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument(
        "--no-usage",
        action="store_true",
        help="orthography only — leave toward/towards and among/amongst alone",
    )
    args = ap.parse_args()

    roots = sorted(CONTENT.glob(f"*/{args.slug}")) if args.slug else [CONTENT]
    if args.slug and not roots:
        print(f"no book found for slug {args.slug!r}", file=sys.stderr)
        return 1

    total_files = 0
    total_subs = 0
    per_form: dict[str, int] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not eligible(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits = findings(text, usage=not args.no_usage)
            if not hits:
                continue
            new = to_american(text, usage=not args.no_usage)
            if new == text:
                continue
            total_files += 1
            total_subs += sum(hits.values())
            for k, v in hits.items():
                per_form[k] = per_form.get(k, 0) + v
            rel = path.relative_to(REPO)
            print(f"  {sum(hits.values()):4d}  {rel}")
            if args.apply:
                path.write_text(new, encoding="utf-8")

    verb = "rewrote" if args.apply else "would rewrite"
    print(f"\n{verb} {total_subs} occurrence(s) across {total_files} file(s)")
    if per_form:
        print("by form:")
        for form, n in sorted(per_form.items(), key=lambda kv: -kv[1])[:25]:
            print(f"  {form:22s} {n}")
    if not args.apply and total_files:
        print("\ndry run — pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
