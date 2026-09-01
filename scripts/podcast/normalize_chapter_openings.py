#!/usr/bin/env python3
"""normalize_chapter_openings.py — backfill: every chapter begins with a capital.

New books get this inside `compose_book_v2` (apparatus step `5a-opening`); this
is the one-time sweep for everything already composed, and the tool to re-run if
a hand edit reintroduces a lowercase opening.

SCOPE. `<book>/book/book.md` only. That is the one file whose `## ` headings mark
chapters and the one a reader opens; the NotebookLM sources under `chapters/` are
an upload lane with no chapter headings of this shape, and nothing under
`_system/source/` is ever eligible — those are evidence, not prose the pipeline
authored.

It also REPORTS any chapter that opens on a fragment. A capital letter makes a
truncated chapter look deliberate, so the loss is named rather than smoothed over;
repairing it needs the source and a person, and this script never attempts it.

Usage:
    python3 scripts/podcast/normalize_chapter_openings.py            # dry run, all
    python3 scripts/podcast/normalize_chapter_openings.py <slug>     # dry run, one
    python3 scripts/podcast/normalize_chapter_openings.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _chapter_opening import capitalize_openings, openings  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "content"


def books(slug: str | None) -> list[Path]:
    found = sorted(CONTENT.glob("*/*/book/book.md"))
    if slug:
        found = [p for p in found if p.parent.parent.name == slug]
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", help="one book (default: every book)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    args = ap.parse_args()

    targets = books(args.slug)
    if not targets:
        print(f"no book.md found{f' for {args.slug}' if args.slug else ''}")
        return 1

    changed, fragments = [], []
    for md in targets:
        slug = md.parent.parent.name
        before = md.read_text(encoding="utf-8")
        after = capitalize_openings(before)
        # Read fragments off `before`: the lowercase is the signal, and `after`
        # has just removed it.
        for row in openings(before):
            if row["fragment"]:
                fragments.append((slug, row["chapter"], row["line"][:70]))
        if after == before:
            continue
        was = [r["chapter"] for r in openings(before) if r["lowercase"]]
        changed.append((slug, was))
        if args.apply:
            md.write_text(after, encoding="utf-8")

    if changed:
        verb = "capitalized" if args.apply else "would capitalize"
        print(f"{verb} the opening of {sum(len(c) for _, c in changed)} chapter(s):\n")
        for slug, chapters in changed:
            for ch in chapters:
                print(f"  {slug:34} {ch}")
    else:
        print("every chapter already opens with a capital.")

    if fragments:
        print(f"\n{len(fragments)} chapter(s) open mid-sentence — a capital hides this, it does not fix it:\n")
        for slug, ch, line in fragments:
            print(f"  {slug:34} {ch}")
            print(f"  {'':34}   {line}")
        print("\n  Text was probably lost at the chapter boundary. Check the source.")

    if not args.apply and changed:
        print("\ndry run — nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
