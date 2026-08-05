#!/usr/bin/env python3
"""inject_chapter_arabic.py — persist glossary Arabic in Islamic chapter prose.

Islamic scholarly chapters must carry the Arabic script visibly in the chapter
source, while pronunciation guidance remains in the glossary / Customize prompt.
This pass deterministically injects ``romanized term (Arabic script)`` from the
book glossary into ``chapters/ch*.txt``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _content_profile import is_islamic_scholarly
from pronunciation_compiler import load_glossary_entries, resolve_curation

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_FENCE_RE = re.compile(r"^\s*```")


def _has_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text or ""))


def _term_subs(book_dir: Path) -> list[tuple[str, str, str]]:
    """Return visible chapter substitutions, longest-first."""
    seen: set[str] = set()
    subs: list[tuple[str, str, str]] = []
    for entry in load_glossary_entries(book_dir):
        cur = resolve_curation(entry)
        if cur.get("drop_arabic"):
            continue
        phonetic = str(cur.get("phonetic") or "").strip()
        arabic = str(cur.get("arabic") or "").strip()
        english = str(entry.get("english_override") or "").strip()
        key = phonetic.casefold()
        if not phonetic or not _has_arabic(arabic) or key in seen:
            continue
        seen.add(key)
        subs.append((phonetic, arabic, english))
    subs.sort(key=lambda kv: len(kv[0]), reverse=True)
    return subs


def _compile_pattern(subs: list[tuple[str, str, str]]) -> re.Pattern[str] | None:
    if not subs:
        return None
    alternation = "|".join(re.escape(term) for term, _script, _english in subs)
    return re.compile(rf"(?<![\w-])({alternation})(?![\w'’-])", re.IGNORECASE)


def inject_text(text: str, subs: list[tuple[str, str, str]]) -> tuple[str, int]:
    """Inject Arabic script into chapter text. Idempotent."""
    pattern = _compile_pattern(subs)
    if pattern is None:
        return text, 0
    scripts = {term.casefold(): script for term, script, _english in subs}
    english_overrides = {term.casefold(): english for term, _script, english in subs if english}
    introduced: set[str] = set()
    changed = 0
    in_fence = False
    out_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            term = match.group(1)
            script = scripts.get(term.casefold())
            if not script:
                return term
            after = line[match.end() :]
            paren = re.match(r"\s*\(([^)]*)\)", after)
            if paren and _has_arabic(paren.group(1)):
                introduced.add(term.casefold())
                return term
            english = english_overrides.get(term.casefold())
            if english and term.casefold() in introduced:
                changed += 1
                return english
            changed += 1
            introduced.add(term.casefold())
            if english:
                return f"{term} ({script}, {english})"
            return f"{term} ({script})"

        out_lines.append(pattern.sub(repl, line))

    return "".join(out_lines), changed


def inject_book(book_dir: Path, *, dry_run: bool = False, require_islamic: bool = True) -> dict[str, int]:
    """Inject Arabic into every chapter. Returns deterministic counts."""
    book_dir = Path(book_dir)
    if require_islamic and not is_islamic_scholarly(book_dir):
        return {"skipped_non_islamic": 1, "chapters": 0, "injections": 0, "changed_files": 0}

    chapters = sorted((book_dir / "chapters").glob("ch*.txt"))
    subs = _term_subs(book_dir)
    changed_files = 0
    injections = 0
    for chapter in chapters:
        before = chapter.read_text(encoding="utf-8")
        after, count = inject_text(before, subs)
        if count:
            changed_files += 1
            injections += count
            if not dry_run:
                chapter.write_text(after, encoding="utf-8")
    return {
        "chapters": len(chapters),
        "terms": len(subs),
        "injections": injections,
        "changed_files": changed_files,
    }


def chapter_arabic_status(book_dir: Path, *, require_islamic: bool = True) -> dict[str, object]:
    """Return the hard-gate status for persisted chapter Arabic."""
    book_dir = Path(book_dir)
    if require_islamic and not is_islamic_scholarly(book_dir):
        return {"ok": True, "skipped_non_islamic": True, "note": "n/a (not islamic_scholarly)"}
    chapters = sorted((book_dir / "chapters").glob("ch*.txt"))
    subs = _term_subs(book_dir)
    missing = [
        chapter.name for chapter in chapters if not _has_arabic(chapter.read_text(encoding="utf-8", errors="replace"))
    ]
    if not chapters:
        return {"ok": False, "chapters": 0, "terms": len(subs), "missing": [], "note": "no chapters found"}
    if not subs:
        return {
            "ok": False,
            "chapters": len(chapters),
            "terms": 0,
            "missing": [],
            "note": "no glossary entries with Arabic script",
        }
    if missing:
        preview = ", ".join(missing[:5])
        suffix = "" if len(missing) <= 5 else f", +{len(missing) - 5} more"
        return {
            "ok": False,
            "chapters": len(chapters),
            "terms": len(subs),
            "missing": missing,
            "note": f"{len(missing)}/{len(chapters)} chapters have no Arabic script: {preview}{suffix}",
        }
    return {
        "ok": True,
        "chapters": len(chapters),
        "terms": len(subs),
        "missing": [],
        "note": f"Arabic script present in all {len(chapters)} chapters from {len(subs)} glossary terms",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-non-islamic", action="store_true")
    args = ap.parse_args()

    result = inject_book(
        args.book_dir.resolve(),
        dry_run=args.dry_run,
        require_islamic=not args.allow_non_islamic,
    )
    print(
        "inject_chapter_arabic: "
        f"{result.get('injections', 0)} injections across "
        f"{result.get('changed_files', 0)} files "
        f"({result.get('terms', 0)} glossary terms, {result.get('chapters', 0)} chapters)"
    )
    if result.get("skipped_non_islamic"):
        print("inject_chapter_arabic: skipped (content_profile is not islamic_scholarly)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
