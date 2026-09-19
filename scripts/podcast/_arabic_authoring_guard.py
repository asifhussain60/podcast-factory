"""_arabic_authoring_guard.py — chapter authoring may not invent Arabic (R-ARABIC-INTEGRITY).

Arabic script may enter a chapter only if it was in the SOURCE, or is sanctioned canon (verified
atoms, the curated glossary) — never because the model wrote it from memory, however accurate. On
isaf-al-talib the phase-0d prompt said to *preserve* script the source supplies but never forbade
inventing it, and the model added Qur'anic phrases as `⟪ar:…⟫` (ch20: three spans). Finalize gate
G14 caught them; a person removed them by hand (b593cf34).

The prompt now forbids it. This is the deterministic backstop for when the model does it anyway: right
after a chapter is written, any span that is not sanctioned is removed and the English around it is
kept — exactly what the hand-fix did — and the removal is RECORDED in
`_system/arabic-authoring-scrub.json`, so nothing is silently rewritten. Spans are extracted and
normalised by `arabic_integrity`, the same definition the gate uses, so the two cannot disagree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import arabic_integrity as ai

REPORT_NAME = "arabic-authoring-scrub.json"

# `⟪ar:…⟫`, with the leading whitespace, an optional comma/semicolon that glued it to its English
# rendering, and the spaces after it, so removing it leaves a single clean seam.
_MARKER = re.compile(r"(?P<lead>[ \t]*)⟪ar:(?P<body>[^⟫]*)⟫(?:[ \t]*[,;،])?[ \t]*")
_EMPTY_BRACKETS = re.compile(r"[ \t]*[(\[][ \t]*[)\]]")


def _hash(span: str) -> str:
    return ai._hash(ai.normalize_arabic_span(span))


def _all_sanctioned(spans: list[str], sanctioned: set[str]) -> bool:
    return all(_hash(s) in sanctioned for s in spans)


def scrub_chapter_text(text: str, sanctioned: set[str]) -> tuple[str, list[str]]:
    """Remove unsanctioned Arabic from `text`. Returns (new_text, removed_span_texts). Pure."""
    removed: list[str] = []

    def _marker(m: re.Match[str]) -> str:
        spans = ai.extract_spans(m.group("body"))
        if not spans or _all_sanctioned(spans, sanctioned):
            return m.group(0)
        removed.extend(spans)
        return m.group("lead") if m.start() > 0 and m.group("lead") else ""

    out = _MARKER.sub(_marker, text)

    # Bare Arabic that never had a marker. Longest span first, so one that is a substring of another
    # cannot leave a fragment behind. Between two words it leaves ONE space; at a line edge, none.
    for span in sorted(set(ai.extract_spans(out)), key=len, reverse=True):
        if _hash(span) in sanctioned or span not in out:
            continue
        removed.append(span)
        pattern = re.escape(span)
        out = re.sub(rf"(?<=\S)[ \t]*{pattern}[ \t]*(?=\S)", " ", out)
        out = re.sub(rf"[ \t]*{pattern}[ \t]*", "", out)

    if removed:
        out = _EMPTY_BRACKETS.sub("", out)
    return out, removed


def _sanctioned(book_dir: Path, source_text: str) -> set[str]:
    canon = ai.build_allowlist(book_dir)["added"]
    return set(canon) | {_hash(s) for s in ai.extract_spans(source_text)}


def scrub_authored_chapters(
    book_dir: Path, chapter_files: list[Path], source_text: str, log: Callable[..., None] = print
) -> int:
    """Scrub each chapter file in place. Returns the number of spans removed; rewrites only changed files."""
    sanctioned = _sanctioned(book_dir, source_text)
    per_file: dict[str, list[str]] = {}
    for path in chapter_files:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        cleaned, removed = scrub_chapter_text(original, sanctioned)
        if removed and cleaned != original:
            path.write_text(cleaned, encoding="utf-8")
            per_file[path.name] = removed
    if not per_file:
        return 0
    report_path = book_dir / "_system" / REPORT_NAME
    report: dict = {"rule": "R-ARABIC-INTEGRITY", "chapters": {}}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except ValueError:
            log(f"    arabic guard: {REPORT_NAME} was unreadable; starting a fresh report")
    report.setdefault("chapters", {}).update(per_file)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(v) for v in per_file.values())
    log(
        f"    arabic guard: removed {total} unsanctioned Arabic span(s) the model wrote from memory — see _system/{REPORT_NAME}"
    )
    return total
