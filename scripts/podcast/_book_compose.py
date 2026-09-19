"""_book_compose.py — shared compose helpers for the book lane.

A HELPER MODULE ONLY. The pipeline's 0book-compose phase routes through the
unified ``_book_pipeline_v2.compose_book_v2``; what lives here is the shared
source-slicing / Arabic-page / Quran-anchor machinery that the v2 faithful base
(``_translation_edition``), ``_book_voice`` and ``validate_book_ready`` import.

It also held a second, superseded whole-book composer — ``author_phase_book_compose``
plus a ``main()`` that invoked it from the command line — deleted 2026-07-21. It was
not dead code in the harmless sense: it wrote ``book/book.md`` directly and
repopulated the stale first-person ``book/_chunks/book/`` cache, so running the
module as a script clobbered a good compose with prose from a route the pipeline
retired, in a narrative frame the repo's locked rule forbids. A file that can
destroy the deliverable by being run is worse than a missing feature.
"""

from __future__ import annotations

import re
from pathlib import Path

from _rules import COMPOSE_RETRY_TIMEOUT_S, COMPOSE_TIMEOUT_S

# Per-chapter wall budgets — see _rules.py for rationale.
_COMPOSE_TIMEOUT = COMPOSE_TIMEOUT_S
_RETRY_TIMEOUT = COMPOSE_RETRY_TIMEOUT_S

_PAGE_MARK = re.compile(r"<!--\s*page\s*(\d+)\s*-->", re.IGNORECASE)


def _slice_source(lines: list[str], ranges: list[list[int]]) -> str:
    out: list[str] = []
    for a, b in ranges:
        out.extend(lines[a - 1 : b])  # 1-based inclusive
    text = "\n".join(out)
    text = _PAGE_MARK.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _line_pages(lines: list[str]) -> list[int]:
    """Source page carried by each line of the line-numbered design input.

    Lines before the first ``<!-- page N -->`` marker belong to page 1."""
    pages: list[int] = []
    cur = 1
    for ln in lines:
        m = _PAGE_MARK.search(ln)
        if m:
            cur = int(m.group(1))
        pages.append(cur)
    return pages


def _pages_for_ranges(line_pages: list[int], ranges: list[list[int]]) -> list[int]:
    out: set[int] = set()
    for a, b in ranges:
        lo, hi = max(1, a), min(len(line_pages), b)
        out.update(line_pages[lo - 1 : hi])
    return sorted(out)


def _load_arabic_pages(book_dir: Path) -> dict[int, str] | None:
    """Per-page Arabic OCR ground truth from Phase 0a, when the source was Arabic script.

    Returns None for books without an Arabic OCR extract (fiction, technical, English
    sources) — composition then behaves exactly as before."""
    from _vowelled_source import resolve_arabic_source

    src = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    if not src.exists():
        return None
    # Prefer the vowelled copy of this exact OCR when `vowel_source` has made one:
    # the ground truth handed to the compose prompt then carries its marks, so a
    # quoted verse arrives vowelled instead of being re-derived at the end. Falls
    # back to the raw extract whenever no sibling exists or the OCR has since been
    # re-run — see `_vowelled_source` for why staleness is fingerprinted.
    src = resolve_arabic_source(src)
    text = src.read_text(encoding="utf-8")
    if _arabic_run_count(text) < 50:
        return None
    pages: dict[int, str] = {}
    cur: int | None = None
    buf: list[str] = []
    for ln in text.split("\n"):
        m = _PAGE_MARK.search(ln)
        if m:
            if cur is not None:
                pages[cur] = "\n".join(buf).strip()
            cur, buf = int(m.group(1)), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        pages[cur] = "\n".join(buf).strip()
    return pages or None


def _translit_quote_count(text: str) -> int:
    """How many italicized transliteration quotes the SOURCE carries (for reporting)."""
    return len(re.findall(r'\*"[^"]{8,}"\*', text) + re.findall(r"\*'[^']{8,}'\*", text))


def _arabic_run_count(text: str) -> int:
    return len(re.findall(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}", text))


# Quran citation in the source/transliteration, e.g. "(Qur'an 2:255)", "Quran 7:56",
# "Sura 18:110", "Q 53:39", "(5:13)". Surah 1-114, ayah up to 286 (longest sura).
# Three forms, captured consistently:
#   - spelled prefix (Qur'an/Quran/Sura/Surah) accepts colon OR dot separator
#     (groups 1,2). Word-boundary anchored so it won't match mid-word.
#   - bare "Q" prefix requires a COLON separator (groups 3,4) — this excludes
#     financial-quarter notation like "Q1.20" / "Q3.2025" that the dot form would
#     otherwise misread as a verse and pollute the anchor-coverage metric.
#   - a WORDLESS reference in parentheses (groups 5,6), added 2026-08-01. Five of
#     `degrees-of-excellence`'s 23 citations are written this way, and because
#     none of them matched, the verses they name were never anchored into the
#     compose prompt and reached the page with no Arabic at all. Safe for the same
#     reason the `Q` form is: the enclosing parentheses AND a colon are both
#     required, so neither a fiscal quarter nor a bare ratio in running prose can
#     reach it.
_QURAN_CITE_RE = re.compile(
    r"\b(?:Qur(?:['’ʾ]?)?an|Qur['’]ān|S[uū]rah?|Sura)\.?\s*(\d{1,3})\s*[:.]\s*(\d{1,3})"
    r"|\bQ\.?\s*(\d{1,3})\s*:\s*(\d{1,3})"
    r"|\(\s*(\d{1,3})\s*:\s*(\d{1,3})\s*\)",
    re.IGNORECASE,
)


def _detect_quran_refs(text: str) -> list[tuple[int, int]]:
    """Distinct (surah, ayat) citations in order of first appearance, range-validated."""
    refs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for m in _QURAN_CITE_RE.finditer(text or ""):
        s = int(m.group(1) or m.group(3) or m.group(5))
        a = int(m.group(2) or m.group(4) or m.group(6))
        if 1 <= s <= 114 and 1 <= a <= 286 and (s, a) not in seen:
            seen.add((s, a))
            refs.append((s, a))
    return refs


def _quran_anchor_block(text: str) -> tuple[str, dict]:
    """Build an authoritative CANONICAL QURAN block from mirror.db for every verse
    cited in the chapter, so the composer reproduces the exact mushaf text instead
    of reconstructing it from memory. Deterministic: a stored DB lookup keyed by
    surah:ayat (no LLM, no fuzzy match). Returns (block, stats). Empty block when
    nothing is cited or the mirror is unavailable — composition degrades to the
    prior best-attempt behavior, never worse."""
    refs = _detect_quran_refs(text)
    stats = {"cited": len(refs), "anchored": 0}
    if not refs:
        return "", stats
    try:
        from source_library_mirror import quran_ayat_lookup
    except Exception:
        return "", stats
    entries: list[str] = []
    for s, a in refs:
        try:
            row = quran_ayat_lookup(s, a)
        except Exception:
            row = None
        arabic = ((row or {}).get("arabic") or "").strip()
        if arabic:
            stats["anchored"] += 1
            entries.append(f"Qur'an {s}:{a} — reproduce this EXACT canonical text:\n{arabic}")
    if not entries:
        return "", stats
    block = (
        "\nCANONICAL QURAN — VERBATIM (authoritative; overrides memory)\n"
        "For each Quranic verse cited in this chapter, the EXACT canonical mushaf "
        "Arabic is given below, drawn from the verified Quran database. When you "
        "render one of these verses in Arabic script, you MUST reproduce its text "
        "below CHARACTER-FOR-CHARACTER — do not re-spell, re-vowel, paraphrase, or "
        "rely on memory. Place the English translation beneath as usual.\n\n" + "\n\n".join(entries) + "\n"
    )
    return block, stats
