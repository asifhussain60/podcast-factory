#!/usr/bin/env python3
"""compose_fix.py — check and repair one book's chapters WITHOUT re-running the pipeline.

The engine behind the `pf-compose-fix` skill. It answers two questions about the reading
edition and nothing else:

    check   which of the five reading-edition defects do these chapters carry
    fix     repair the ones that have a deterministic repair, through the Composer

WHY IT EXISTS. The agent that runs the final checks after articulation — `book-challenger`
— states its remediation policy in one line: it never mutates the book, and the only safe
repair is a Worker re-compose. That is exactly the cost Asif does not want to pay to
delete a bracket. This keeps the challenger's RULES and swaps its CURE: the checks come
from `_book_defects`, the same module the compose apparatus and the recorded-defect tests
read, and the repair is written the way a human Composer save is written.

CHAPTERS ARE ADDRESSED BY THEIR PRINTED NUMBER, which the rest of the pipeline forbids —
`rearticulate_chapter` says so in its own docstring, because the introduction is an
unnumbered section and counting sections makes "chapter 3" land on section 4. The ban is
on COUNTING. This reads the number off the heading instead, which is a different
operation: every book in the corpus numbers its chapter headings and leaves exactly one
section unnumbered, so `## 3. Intellect, Not Reason` is chapter 3 unambiguously. A book
that numbers inconsistently gets the chapter list printed and no write.

SCOPE IS THE COMPOSE TAB. It reads and writes `book/book.md` and the Composer's edit
sidecar. It never touches `chapters/*.txt` (the podcast upload lane), the episode
framings, or the slide decks — those are other deliverables with other gates.

Usage:
    python3 scripts/podcast/compose_fix.py <slug>                    # check every chapter
    python3 scripts/podcast/compose_fix.py <slug> --chapters 1,3,9   # check three
    python3 scripts/podcast/compose_fix.py <slug> --chapters 1 --fix
    python3 scripts/podcast/compose_fix.py <slug> --json

Exit codes:
    0  — ran; the report says what was found (a defect is not an error)
    1  — could not resolve the book, the chapters, or the write was refused
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_defect_fixes import FIXES, ligature_is_printable, proposed_romanization_deletions
from _book_defects import DETECTORS, chapters
from _book_edits import anchor_key, base_fingerprint_for, record_edit

#: A `## ` heading that opens with a printed chapter number.
_NUMBERED_HEADING_RE = re.compile(r"^\s*(\d+)\s*[.):]\s*(.+)$")


class ChapterError(ValueError):
    """The selection could not be resolved. Carries a message worth printing."""


def resolve_book(slug_or_dir: str) -> Path:
    """Same resolution the ship gate uses — bucket-aware, slug or path."""
    path = Path(slug_or_dir)
    if path.is_dir() and (path / "book").exists():
        return path.resolve()
    import publish_to_library as P

    workspace = P.resolve_workspace(slug_or_dir)
    if not workspace.is_dir():
        raise ChapterError(f"could not resolve a book directory for {slug_or_dir!r}")
    return workspace.resolve()


def chapter_index(md: str) -> list[dict]:
    """Every `##` section with its printed number, heading and Composer key.

    ``number`` is None for a section the edition does not number — the introduction in
    every book here. That section is addressable by name, never by an ordinal, which is
    the whole point: an ordinal would silently shift every chapter after it.
    """
    index: list[dict] = []
    for heading, body in chapters(md):
        match = _NUMBERED_HEADING_RE.match(heading)
        index.append(
            {
                "number": int(match.group(1)) if match else None,
                "heading": heading,
                "title": match.group(2).strip() if match else heading,
                "key": anchor_key(heading),
                "words": len(body.split()),
            }
        )
    return index


def select_chapters(index: list[dict], spec: str | None) -> list[dict]:
    """Resolve `--chapters` against the printed numbers. Refuses rather than guesses.

    Accepts `all` (the default), a comma-separated list of numbers, inclusive ranges
    (`3-5`), and a case-insensitive title fragment for a section that has no number.
    """
    if not spec or spec.strip().lower() == "all":
        return list(index)

    numbered = {c["number"]: c for c in index if c["number"] is not None}
    duplicates = len([c for c in index if c["number"] is not None]) - len(numbered)
    if duplicates:
        raise ChapterError(
            f"this book numbers two chapters the same, so a number does not identify one "
            f"({duplicates} duplicate(s)) — address them by title instead"
        )

    picked: dict[str, dict] = {}
    for token in (t.strip() for t in spec.split(",") if t.strip()):
        span = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
        wanted: list[int] = []
        if span:
            wanted = list(range(int(span.group(1)), int(span.group(2)) + 1))
        elif token.isdigit():
            wanted = [int(token)]
        else:
            matches = [c for c in index if token.lower() in c["title"].lower()]
            if len(matches) != 1:
                raise ChapterError(f"{token!r} matches {len(matches)} chapters — name one exactly, or use its number")
            picked[matches[0]["key"]] = matches[0]
            continue
        for number in wanted:
            if number not in numbered:
                raise ChapterError(f"this book has no chapter {number}")
            picked[numbered[number]["key"]] = numbered[number]
    if not picked:
        raise ChapterError(f"nothing selected by {spec!r}")
    return [c for c in index if c["key"] in picked]


def _section_text(md: str, heading: str) -> tuple[int, int]:
    """(start, end) offsets of one `##` section, heading included."""
    pattern = re.compile(r"^## " + re.escape(heading) + r"\s*$", re.M)
    match = pattern.search(md)
    if not match:
        raise ChapterError(f"no ## section matches {heading!r}")
    following = re.compile(r"^## ", re.M).search(md, match.end())
    return match.start(), (following.start() if following else len(md))


def check(book_dir: Path, selection: list[dict]) -> dict:
    """What the selected chapters carry. Reads only."""
    md = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    wanted = {c["heading"] for c in selection}
    report: dict = {"book": book_dir.name, "chapters": [], "totals": {}}
    totals: dict[str, int] = {name: 0 for name in DETECTORS}
    per_chapter: dict[str, dict[str, list]] = {h: {name: [] for name in DETECTORS} for h in wanted}

    for name, detector in DETECTORS.items():
        for finding in detector(md):
            heading = finding[0]
            if heading in wanted:
                per_chapter[heading][name].append(list(finding[1:]))
                totals[name] += 1

    for chapter in selection:
        found = per_chapter[chapter["heading"]]
        report["chapters"].append(
            {
                "number": chapter["number"],
                "heading": chapter["heading"],
                "key": chapter["key"],
                "words": chapter["words"],
                "defects": {name: hits for name, hits in found.items() if hits},
            }
        )
    report["totals"] = {name: n for name, n in totals.items() if n}
    report["repairable"] = sorted(set(report["totals"]) & set(FIXES))
    report["needs_judgment"] = sorted(set(report["totals"]) - set(FIXES))
    return report


def composer_is_open() -> str | None:
    """The Astro dev server, if it is up. It autosaves, and it has clobbered a verse.

    On 2026-08-09 a running Composer wrote a truncated Arabic quotation into a shipped
    book while a script was working on the same file. A write here refuses while it is
    running rather than racing it.
    """
    try:
        out = subprocess.run(["pgrep", "-f", "astro.*dev"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001 - no pgrep is not a reason to block a repair
        return None
    return out.splitlines()[0] if out else None


def fix(book_dir: Path, selection: list[dict], *, kinds: list[str], log=print) -> dict:
    """Apply the deterministic repairs to the selected chapters. Returns what changed.

    Each chapter is repaired IN ISOLATION and recorded through the Composer's own save
    path, so the result survives a re-compose and marks the chapter as authored — the
    two things a direct write to book.md would silently lose.
    """
    book_md = book_dir / "book" / "book.md"
    md = book_md.read_text(encoding="utf-8")
    applied: list[dict] = []

    for chapter in selection:
        start, end = _section_text(md, chapter["heading"])
        section = md[start:end]
        changes: dict[str, int] = {}
        repaired = section
        for kind in kinds:
            repaired, count = FIXES[kind](repaired)
            if count:
                changes[kind] = count
        if not changes:
            continue
        md = md[:start] + repaired + md[end:]
        body = repaired.split("\n", 1)[1].strip() if "\n" in repaired else ""
        record_edit(
            book_dir,
            chapter_key=chapter["key"],
            body_md=body,
            base_fingerprint=base_fingerprint_for(book_dir, chapter["key"]),
            saved_at=datetime.now(timezone.utc).isoformat(),
        )
        applied.append({"number": chapter["number"], "heading": chapter["heading"], "changes": changes})
        log(f"    {chapter['heading']}: " + ", ".join(f"{k} ×{n}" for k, n in changes.items()))

    if applied:
        tmp = book_md.with_suffix(".md.tmp")
        tmp.write_text(md, encoding="utf-8")
        os.replace(tmp, book_md)
    return {"applied": applied, "chapters_changed": len(applied)}


def _print_report(report: dict, proposals: list[tuple[str, str]]) -> None:
    print(f"\n{report['book']} — {len(report['chapters'])} chapter(s) checked")
    any_found = False
    for chapter in report["chapters"]:
        if not chapter["defects"]:
            continue
        any_found = True
        print(f"\n  {chapter['heading']}  ({chapter['words']} words)")
        for name, hits in chapter["defects"].items():
            mark = "repairable" if name in FIXES else "needs your judgment"
            print(f"      {name:26} {len(hits):>4}   {mark}")
            for hit in hits[:3]:
                print(f"          {str(hit[0])[:88]}")
    if not any_found:
        print("\n  clean — none of the five defects in these chapters")
        return
    if report["repairable"]:
        print(f"\n  --fix would repair: {', '.join(report['repairable'])}")
    if proposals:
        print(
            f"\n  {len(proposals)} Arabic saying(s) print in the English character set. Nothing here "
            "applies a repair:\n  the honest fix is the Arabic, and where it exists nowhere on disk "
            "supplying it would mean\n  a model recalling scripture. Deleting the romanization is "
            "yours to approve — the English\n  translation always sits beside it."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("slug", help="book slug or BOOK_DIR")
    parser.add_argument("--chapters", default="all", help="printed numbers (1,3,9 or 3-5), a title, or 'all'")
    parser.add_argument("--fix", action="store_true", help="apply the deterministic repairs")
    parser.add_argument("--only", help="comma-separated defect names to repair (default: all repairable)")
    parser.add_argument("--list", action="store_true", help="print the chapter list and exit")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument(
        "--allow-composer-open",
        action="store_true",
        help="write even though the Book Composer is running (it autosaves; it has clobbered a verse)",
    )
    args = parser.parse_args()

    try:
        book_dir = resolve_book(args.slug)
        book_md = book_dir / "book" / "book.md"
        if not book_md.is_file():
            raise ChapterError(f"{book_dir.name} has no reading edition")
        index = chapter_index(book_md.read_text(encoding="utf-8"))
    except ChapterError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        selection = select_chapters(index, args.chapters)
    except ChapterError as e:
        # A refused selection always prints the list, so the answer is on screen rather
        # than one command away. Guessing which chapter was meant is the one thing this
        # must never do: it would rewrite the wrong one.
        print(f"ERROR: {e}\n\nChapters in {book_dir.name}:", file=sys.stderr)
        for chapter in index:
            number = str(chapter["number"]) if chapter["number"] else "—"
            print(f"  {number:>3}  {chapter['heading']}", file=sys.stderr)
        return 1

    if args.list:
        for chapter in index:
            number = str(chapter["number"]) if chapter["number"] else "—"
            print(f"  {number:>3}  {chapter['heading']}  ({chapter['words']} words)")
        return 0

    report = check(book_dir, selection)
    proposals = [
        p
        for p in proposed_romanization_deletions(book_md.read_text(encoding="utf-8"))
        if p[0] in {c["heading"] for c in selection}
    ]

    if args.fix:
        kinds = [k.strip() for k in args.only.split(",")] if args.only else report["repairable"]
        unknown = [k for k in kinds if k not in FIXES]
        if unknown:
            print(f"ERROR: no automatic repair for {', '.join(unknown)}", file=sys.stderr)
            return 1
        if not kinds:
            print("nothing to repair in the selected chapters")
            return 0
        if "prophet-wrong-honorific" in kinds:
            printable, why = ligature_is_printable(book_dir)
            if not printable:
                print(f"REFUSED: {why}", file=sys.stderr)
                return 1
        pid = composer_is_open()
        if pid and not args.allow_composer_open:
            print(
                f"REFUSED: the Book Composer is running (pid {pid}) and autosaves the file this would "
                "write.\nClose the tab, or pass --allow-composer-open if you know it is not on this book.",
                file=sys.stderr,
            )
            return 1
        result = fix(book_dir, selection, kinds=kinds, log=print)
        report["fixed"] = result
        report["after"] = check(book_dir, selection)["totals"]

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_report(report, proposals)
        if args.fix:
            print(
                f"\n  repaired {report['fixed']['chapters_changed']} chapter(s); remaining: {report['after'] or 'none'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
