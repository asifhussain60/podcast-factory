#!/usr/bin/env python3
"""Remove a chapter that is a modern editor's apparatus, not the author's book.

WHY
---
`asaas-al-taveel/vol-01` printed 5,552 words of Arif Tamer's 1960 editorial
matter as its chapter 1 — why he withheld the manuscript, his own essay on what
inner interpretation is, which two copies he worked from, and which spelling
errors he silently corrected, signed "Aref Tamer, Beirut, Lebanon, 1960". Al-
Nu'man, who died in 363 AH, does not speak until chapter 2. The editor says so
himself in the last sentence of the chapter: "What follows now is the author's
own introduction."

Asif's rule (2026-08-03): the edition begins with the book, not with its
publisher. That is the same rule that retired the machine preface, applied to a
human editor's front matter — which no denoise pass would ever strip, because it
is clean authorial prose about the book.

WHAT IT DOES
------------
1. Removes the chapter's `## N. Title` section from `book/book.md`.
2. Removes its entry from `book/book-toc.json` and RENUMBERS every later
   chapter's `bk_index`, so chapter 2 becomes chapter 1.
3. Renumbers the surviving `## N.` headings in book.md to match.
4. Follows the renumbering through `book/source-crosswalk.json` and
   `_system/translation-edition-manifest.json` when a book has them.
5. Drops the chapter from the pass reports, which otherwise go on describing a
   book with one more chapter than exists.

REFUSES, rather than guessing, when the chapter carries a Composer edit. That is
a chapter a human authored, and deleting one on a script's say-so is not a trade
this pipeline makes — the operator can remove the edit deliberately first.

``--dry-run`` prints what would change and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key, edited_chapter_keys  # noqa: E402

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
_NUMBERED_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$")


def renumber_headings(book_md: str) -> str:
    """Make the surviving `## N.` headings count 1, 2, 3 … in document order."""
    n = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal n
        numbered = _NUMBERED_RE.match(m.group(1).strip())
        if not numbered:
            return m.group(0)
        n += 1
        return f"## {n}. {numbered.group(2)}"

    return _HEADING_RE.sub(repl, book_md)


def drop_section(book_md: str, title: str) -> tuple[str, int]:
    """Remove the `## …` section whose heading matches ``title``. Returns words."""
    key = anchor_key(title)
    parts = _HEADING_RE.split(book_md)
    out = [parts[0]]
    dropped = 0
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if anchor_key(parts[i]) == key:
            dropped = len(body.split())
            continue
        out.append(parts[i] + body)
    if not dropped:
        return book_md, 0
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n", dropped


def plan(book_dir: Path, title: str) -> dict[str, Any]:
    book_dir = Path(book_dir).resolve()
    key = anchor_key(title)
    if key in edited_chapter_keys(book_dir):
        raise SystemExit(
            f"{key!r} carries a Composer edit — a chapter a human authored. Remove the edit "
            "deliberately first; this script will not delete one on its own say-so."
        )
    toc_path = book_dir / "book" / "book-toc.json"
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    chapters = toc.get("chapters") or []
    match = next((c for c in chapters if anchor_key(str(c.get("title") or "")) == key), None)
    if match is None:
        raise SystemExit(f"no chapter titled {title!r} in {toc_path}")

    book_md = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    _, words = drop_section(book_md, title)
    return {
        "book_dir": str(book_dir),
        "title": str(match.get("title")),
        "key": key,
        "index": match.get("bk_index"),
        "source_line_ranges": match.get("source_line_ranges"),
        "words": words,
        "remaining": [str(c.get("title")) for c in chapters if c is not match],
    }


def apply(plan_: dict[str, Any], *, log=print) -> None:
    book_dir = Path(plan_["book_dir"])
    key = plan_["key"]

    book_md_path = book_dir / "book" / "book.md"
    text, words = drop_section(book_md_path.read_text(encoding="utf-8"), plan_["title"])
    book_md_path.write_text(renumber_headings(text), encoding="utf-8")
    log(f"    book.md: dropped {plan_['title']!r} ({words} words) and renumbered the chapters that follow")

    toc_path = book_dir / "book" / "book-toc.json"
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    kept = [c for c in (toc.get("chapters") or []) if anchor_key(str(c.get("title") or "")) != key]
    for n, chapter in enumerate(kept, start=1):
        chapter["bk_index"] = n
    toc["chapters"] = kept
    toc_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"    book-toc.json: {len(kept)} chapters, renumbered 1..{len(kept)}")

    # Only when the book has them — a book composed before these existed has not.
    for rel, id_field in (
        ("book/source-crosswalk.json", "index"),
        ("_system/translation-edition-manifest.json", "index"),
    ):
        path = book_dir / rel
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = [c for c in (data.get("chapters") or []) if anchor_key(str(c.get("title") or "")) != key]
        for n, row in enumerate(rows, start=1):
            row[id_field] = n
        data["chapters"] = rows
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log(f"    {rel}: {len(rows)} chapters, renumbered")

    from _book_pass_reports import drop_section_from_reports

    drop_section_from_reports(book_dir, plan_["title"], log=log)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--title", required=True, help="the chapter's title, without its number")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    p = plan(args.book_dir, args.title)
    print(f"drop chapter {p['index']}: {p['title']!r} — {p['words']} words, source lines {p['source_line_ranges']}")
    for n, t in enumerate(p["remaining"], start=1):
        print(f"  becomes chapter {n}: {t}")
    if args.dry_run:
        print("--- dry run: nothing written ---")
        return 0
    apply(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
