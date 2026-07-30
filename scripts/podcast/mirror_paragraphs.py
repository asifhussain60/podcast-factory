#!/usr/bin/env python3
"""mirror_paragraphs.py — make the English paragraphing the Arabic's.

Asif, 2026-07-30: "I want the English paragraphs to mirror the Arabic." The
articulation pass splits a long Arabic paragraph into several readable English ones
and splits a speech tag off from the speech it introduces, so the edition printed
"The boy said:" on a line of its own where the source prints
`قال الغلام: قلة العذر روعتني…` as one paragraph. This merges them back: one Arabic
paragraph, one English paragraph, everywhere.

A translation edition's paragraphing is the source's, not the translator's, and a
reader holding the two side by side should never have to work out which English
answers which Arabic. After this pass every alignment group is 1:1.

The merge itself, and every refusal that protects it, is in `_book_mirror`. This
file is the driver: it walks a book's chapters, skips the ones the human has
authored through the Composer, rewrites `book/book.md`, and rewrites
`_system/arabic-alignment.json` to match — merging changes what a paragraph IS, so
every fingerprint in that file downstream of a merge would otherwise miss.

    python3 scripts/podcast/mirror_paragraphs.py the-master-and-the-disciple
    python3 scripts/podcast/mirror_paragraphs.py the-master-and-the-disciple --apply
    python3 scripts/podcast/mirror_paragraphs.py --all --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_mirror import load_alignment, mirror_chapter  # noqa: E402
from _paths import REPO_ROOT, content_dir  # noqa: E402


def _split(text: str) -> list[tuple[str | None, str]]:
    """book.md as (heading, body) parts, front matter first with a None heading.

    Same split as `align_arabic_paragraphs._chapter_bodies`, but ORDERED and keeping
    the headings, because this rewrites the file rather than reading it.
    """
    parts = re.split(r"(?m)^(##\s+.+)$", text)
    out: list[tuple[str | None, str]] = [(None, parts[0])]
    for i in range(1, len(parts), 2):
        out.append((parts[i], parts[i + 1]))
    return out


def mirror_book(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    apply: bool = False,
) -> dict:
    """Mirror every chapter of a book. Returns a summary."""
    from _book_edits import anchor_key, edited_chapter_keys

    book_md = book_dir / "book" / "book.md"
    alignment = load_alignment(book_dir)
    if not book_md.exists() or not alignment:
        log("    no composed book or no Arabic alignment — nothing to mirror")
        return {"skipped": "no alignment"}

    by_key = {c.get("chapter_key"): c for c in alignment.get("chapters", [])}
    edited = edited_chapter_keys(book_dir)
    text = book_md.read_text(encoding="utf-8")

    out: list[str] = []
    stats = {"chapters": 0, "merged": 0, "before": 0, "after": 0, "skipped": []}
    for heading, body in _split(text):
        if heading is None:
            out.append(body)
            continue
        key = anchor_key(heading)
        chapter = by_key.get(key)
        if not chapter or not chapter.get("pairs"):
            out.append(heading + body)
            continue
        if key in edited:
            # The author's chapter. Its paragraphing is a choice, not an artefact.
            stats["skipped"].append(f"{key} (Composer edit)")
            out.append(heading + body)
            continue
        result = mirror_chapter(body, chapter["pairs"])
        if result is None:
            # The alignment does not describe this text. Merging on a stale pairing
            # is how two unrelated passages get joined, so nothing is touched.
            stats["skipped"].append(f"{key} (alignment does not match the prose)")
            out.append(heading + body)
            continue
        merged_body, new_pairs = result
        before, after = len(chapter["pairs"]), len(new_pairs)
        stats["chapters"] += 1
        stats["before"] += before
        stats["after"] += after
        stats["merged"] += before - after
        chapter["pairs"] = new_pairs
        out.append(heading + "\n\n" + merged_body)

    for line in stats["skipped"]:
        log(f"    skipped {line}")
    log(
        f"    {stats['chapters']} chapter(s): {stats['before']} English paragraph(s) "
        f"-> {stats['after']}, {stats['merged']} merged into the paragraph above"
    )
    if not apply:
        return stats

    book_md.write_text("".join(out), encoding="utf-8")
    (book_dir / "_system" / "arabic-alignment.json").write_text(
        json.dumps(alignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log("    book.md and arabic-alignment.json rewritten")
    return stats


def _books_with_an_alignment() -> list[Path]:
    out = []
    for hit in (REPO_ROOT / "content").glob("*/**/_system/arabic-alignment.json"):
        out.append(hit.parent.parent)
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Merge consecutive English paragraphs that share one Arabic source paragraph.",
        epilog="Dry run by default. No model is ever called — the pairing is already known.",
    )
    ap.add_argument("slug", nargs="?", help="one book; omit and pass --all to sweep")
    ap.add_argument("--all", action="store_true", help="every book with an Arabic alignment")
    ap.add_argument("--apply", action="store_true", help="write book.md and the alignment")
    a = ap.parse_args()

    if bool(a.slug) == bool(a.all):
        print("Pass exactly one of <slug> or --all.", file=sys.stderr)
        return 2

    if a.all:
        targets = _books_with_an_alignment()
    else:
        book_dir = content_dir(a.slug)
        if not book_dir or not book_dir.exists():
            print(f"Book not found: {a.slug}", file=sys.stderr)
            return 1
        targets = [book_dir]
    if not targets:
        print("No books with an Arabic alignment found.", file=sys.stderr)
        return 1

    if not a.apply:
        print("DRY RUN — nothing is written. Pass --apply to rewrite.\n")
    for book_dir in targets:
        try:
            label = book_dir.relative_to(REPO_ROOT / "content")
        except ValueError:  # pragma: no cover
            label = book_dir
        print(f"==> {label}")
        mirror_book(book_dir, apply=a.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
