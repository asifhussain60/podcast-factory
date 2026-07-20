"""_translation_text.py — deterministic text post-processing for the translation lane.

Extracted verbatim from ``_translation_edition.py`` (R3 DR-005 split, 2026-07-18).
Everything here is pure/deterministic — no LLM shellouts: monochrome SVG
normalization, source windowing, seam-overlap trimming and reworded-twin dedup,
prose normalization (salutations, heading demotion), output-integrity findings,
source/title drift detection, and the persisted source-crosswalk builder.
``_translation_edition`` re-exports every name so importers and tests are
untouched.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from _book_compose import (
    _PAGE_MARK,
    _load_arabic_pages,
    _pages_for_ranges,
    _slice_source,
)

_CHAPTER_WINDOW_WORDS = 2800
_MIN_ACCEPTABLE_RATIO = 0.24

_META_COMMENTARY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsince you (?:did not|didn't) pick\b", re.I), "mentions an option the user did not pick"),
    (re.compile(r"\bi (?:can(?:not|'t)|will not|won't) produce\b", re.I), "refuses to produce the requested chapter"),
    (re.compile(r"\b(?:the )?brief forbids\b", re.I), "mentions hidden prompt constraints"),
    (re.compile(r"\b(?:send|provide) the correct source\b", re.I), "asks for a different source"),
    (re.compile(r"\bswap the title back\b", re.I), "comments on changing the title"),
    (re.compile(r"\bsource passage (?:is|was) about\b", re.I), "comments on source/title mismatch"),
    (re.compile(r"\bhere is the faithful chapter\b", re.I), "adds process preamble"),
    (re.compile(r"\bas an ai\b", re.I), "mentions AI identity"),
)
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+\S")
_OPENING_HEADING_RE = re.compile(r"(?m)^#\s+\S")
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+")
_SOURCE_HEADING_RE = re.compile(r"(?m)^\s*(?:#{1,4}\s+|\*\*)?([A-Z][^\n:]{2,120}:?)\*?\*?\s*$")

_SALUTATION_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\bmay Allah(?:'s)? (?:peace and blessings|blessings and peace|peace|prayers)"
            r" be upon (?:him|her)(?: and (?:his|her) family)?\b",
            re.I,
        ),
        "(ع)",
    ),
    (
        re.compile(
            r"\bpeace and blessings(?: of Allah)? be upon (?:him|her)"
            r"(?: and (?:his|her) family)?\b",
            re.I,
        ),
        "(ع)",
    ),
    (re.compile(r"\bpeace be upon (?:him|her)\b", re.I), "(ع)"),
    (
        re.compile(
            r"\bmay Allah(?:'s)? (?:peace and blessings|blessings and peace|peace|prayers)"
            r" be upon them(?: all)?\b",
            re.I,
        ),
        "(عليهم السلام)",
    ),
    (re.compile(r"\bpeace be upon them(?: all)?\b", re.I), "(عليهم السلام)"),
    (re.compile(r"\bthe blessings of Allah be upon them(?: all)?\b", re.I), "(عليهم السلام)"),
    (re.compile(r"\bmay Allah be pleased with (?:him|her|them)\b", re.I), "(رض)"),
)

_TOPIC_CLUSTERS: dict[str, tuple[str, ...]] = {
    "sales": (
        "market",
        "trade",
        "merchant",
        "sale",
        "sell",
        "buy",
        "property",
        "rent",
        "loan",
        "deposit",
        "hawala",
        "sponsorship",
        "partnership",
        "pre-emption",
    ),
    "oaths": ("oath", "vow", "atonement", "expiation", "swear", "perjury"),
    "food": ("food", "drink", "healing", "medicine", "illness", "eat", "health"),
    "dress": ("wear", "dress", "clothing", "garment", "adornment", "ornament", "fragrance", "perfume", "ring", "silk"),
    "hunting": ("hunt", "hunting", "game", "slaughter", "sacrifice", "prey", "animal", "knife", "aqiqah"),
    "marriage": ("marriage", "marry", "spouse", "wife", "husband", "dowry", "wedding", "household"),
    "divorce": ("divorce", "separation", "iddah", "mourning", "mut'a", "khul", "li'an"),
    "inheritance": (
        "freedom",
        "generosity",
        "gift",
        "bequest",
        "inheritance",
        "estate",
        "shares",
        "heir",
        "slave",
        "manumission",
    ),
    "judiciary": (
        "wrong",
        "redress",
        "crime",
        "blood money",
        "offense",
        "hudud",
        "judge",
        "evidence",
        "testimony",
        "found property",
        "retaliation",
    ),
}

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_RE = re.compile(
    r"rgba?\(\s*([0-9.]+)%?\s*,\s*([0-9.]+)%?\s*,\s*([0-9.]+)%?"
    r"(?:\s*,\s*([0-9.]+)\s*)?\)",
    re.IGNORECASE,
)
_HSL_RE = re.compile(r"hsl\([^)]*\)", re.IGNORECASE)

_MONO_MAP = {
    "#f7f4ee": "#f7f7f7",
    "#fffdf8": "#ffffff",
    "#efeae0": "#eeeeee",
    "#1f1d18": "#111111",
    "#4d4a42": "#444444",
    "#87827a": "#777777",
    "#d9d3c4": "#d0d0d0",
    "#ebe6da": "#e8e8e8",
    "#8b4513": "#000000",
    "#d2b48c": "#d9d9d9",
    "#c8956c": "#b8b8b8",
    "#a0522d": "#555555",
}


def monochrome_svg(svg: str) -> str:
    """Normalize known SVG theme colors to black, white, and gray."""

    def _to_gray(r: float, g: float, b: float) -> int:
        return max(0, min(255, round((0.2126 * r) + (0.7152 * g) + (0.0722 * b))))

    def _hex_sub(match: re.Match[str]) -> str:
        raw = match.group(0)
        mapped = _MONO_MAP.get(raw.lower())
        if mapped:
            return mapped
        h = raw[1:]
        if len(h) == 3:
            vals = [int(ch * 2, 16) for ch in h]
        elif len(h) in (6, 8):
            vals = [int(h[i : i + 2], 16) for i in (0, 2, 4)]
        else:
            return raw
        gray = _to_gray(*vals)
        return f"#{gray:02x}{gray:02x}{gray:02x}"

    def _rgb_sub(match: re.Match[str]) -> str:
        r, g, b = (float(match.group(i)) for i in (1, 2, 3))
        gray = _to_gray(r, g, b)
        alpha = match.group(4)
        if alpha is not None:
            return f"rgba({gray}, {gray}, {gray}, {alpha})"
        return f"rgb({gray}, {gray}, {gray})"

    svg = _HEX_RE.sub(_hex_sub, svg)
    svg = _RGB_RE.sub(_rgb_sub, svg)
    svg = _HSL_RE.sub("#cccccc", svg)
    return svg


def _slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", slug)[:72] or fallback


def _compress_line_ranges(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    ranges: list[list[int]] = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        ranges.append([start, prev])
        start = prev = idx
    ranges.append([start, prev])
    return ranges


def _iter_source_windows(
    lines: list[str],
    ranges: list[list[int]],
    *,
    target_words: int = _CHAPTER_WINDOW_WORDS,
) -> list[tuple[str, list[list[int]]]]:
    pairs: list[tuple[int, str]] = []
    for raw_range in ranges:
        if len(raw_range) != 2:
            continue
        a, b = raw_range
        lo, hi = max(1, int(a)), min(len(lines), int(b))
        pairs.extend((idx, lines[idx - 1]) for idx in range(lo, hi + 1))
    if not pairs:
        return []

    windows: list[tuple[str, list[list[int]]]] = []
    cur: list[tuple[int, str]] = []
    cur_words = 0

    def flush() -> None:
        nonlocal cur, cur_words
        if not cur:
            return
        body = "\n".join(line for _, line in cur).strip()
        if body:
            windows.append((body, _compress_line_ranges([idx for idx, _ in cur])))
        cur = []
        cur_words = 0

    for idx, line in pairs:
        cur.append((idx, line))
        cur_words += len(line.split())
        if cur_words >= target_words and (not line.strip() or _PAGE_MARK.search(line)):
            flush()
    flush()
    return windows


_SEAM_LOOKBACK = 3
_SEAM_MIN_WORDS = 6
_SEAM_RATIO = 0.80
_SEAM_RUN = 12


def _overlap_tokens(text: str) -> list[str]:
    """Normalize a passage to comparable tokens: casefold, drop punctuation."""
    folded = re.sub(r"[^\w\s]", " ", (text or "").casefold())
    return re.sub(r"\s+", " ", folded).strip().split()


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def _para_is_echo(candidate: str, prior: str) -> bool:
    """True when ``candidate`` is a chunk-seam echo of ``prior``.

    Deliberately conservative — fires only on whole-paragraph near-identity or a
    long verbatim token run that covers most of the candidate — so genuinely
    distinct adjacent paragraphs (a real narrative continuation) are never
    trimmed. This catches the ``compose_book_v2`` seam double-render where a
    boundary passage is composed into two adjacent windows/chapters.
    """
    cand = _overlap_tokens(candidate)
    prev = _overlap_tokens(prior)
    if len(cand) < _SEAM_MIN_WORDS or not prev:
        return False
    matcher = SequenceMatcher(None, cand, prev, autojunk=False)
    if matcher.ratio() >= _SEAM_RATIO:
        return True
    block = matcher.find_longest_match(0, len(cand), 0, len(prev))
    return block.size >= _SEAM_RUN and block.size >= 0.6 * len(cand)


def _trim_seam_overlap(prev_prose: str, next_prose: str) -> str:
    """Drop leading paragraphs of ``next_prose`` that echo the tail of
    ``prev_prose``. Whole-paragraph drops only; the surviving text is never
    edited. Returns ``next_prose`` unchanged when nothing echoes."""
    if not (prev_prose or "").strip() or not (next_prose or "").strip():
        return next_prose
    prev_tail = _split_paragraphs(prev_prose)[-_SEAM_LOOKBACK:]
    if not prev_tail:
        return next_prose
    next_paras = _split_paragraphs(next_prose)
    drop = 0
    for para in next_paras[:_SEAM_LOOKBACK]:
        if any(_para_is_echo(para, tail) for tail in prev_tail):
            drop += 1
        else:
            break
    if not drop:
        return next_prose
    return "\n\n".join(next_paras[drop:]).strip()


# Similarity-based seam de-dup — catches reworded twin renders the verbatim
# _trim_seam_overlap cannot see (the fluency de-calque pass rewords each copy of a
# seam double-render differently, so exact-match trimming misses them). Two rules,
# each calibrated on real content with a wide safety margin to the nearest
# legitimate pair (within-chapter next-legit ~0.56 ratio; boundary next-legit ~0.26
# containment):
_ADJ_DEDUP_RATIO = 0.62  # within a chapter: paragraph vs immediate predecessor
_BOUNDARY_DEDUP_CONTAINMENT = 0.42  # chapter open vs previous chapter's last paragraph
_BOUNDARY_DEDUP_MIN_RUN = 5
_NUMBERED_CHAPTER_RE = re.compile(r"^##\s+\d+\.")


def _adjacent_echo(cur: str, prev: str) -> bool:
    a, b = _overlap_tokens(cur), _overlap_tokens(prev)
    if len(a) < _SEAM_MIN_WORDS or len(b) < _SEAM_MIN_WORDS:
        return False
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= _ADJ_DEDUP_RATIO


def _boundary_echo(cur: str, prev: str) -> bool:
    a, b = _overlap_tokens(cur), _overlap_tokens(prev)
    if len(a) < _SEAM_MIN_WORDS or len(b) < _SEAM_MIN_WORDS:
        return False
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    containment = matched / min(len(a), len(b))
    if containment < _BOUNDARY_DEDUP_CONTAINMENT:
        return False
    return matcher.find_longest_match(0, len(a), 0, len(b)).size >= _BOUNDARY_DEDUP_MIN_RUN


def dedupe_seam_paragraphs(text: str) -> str:
    """Drop reworded seam double-renders that survive the verbatim trimmer.

    Runs LAST, on the fully-assembled (and, in v2, de-calqued) book text, because
    the rewording that hides these twins from exact matching happens after compose.
    Two conservative, whole-paragraph-only rules:
      - within a chapter, a paragraph that echoes its IMMEDIATE predecessor
        (token ratio >= 0.62) is a model/window self-repeat — drop the second copy;
      - a chapter's FIRST paragraph that echoes the previous chapter's LAST
        paragraph (containment >= 0.42, with a real shared run) is a boundary
        over-run — drop the echo so the chapter opens on its own content.
    Never edits surviving text; comparisons are immediate-neighbour only, so a
    distant legitimate refrain is untouched.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out: list[str] = []
    prev_para: str | None = None  # last kept paragraph (within-chapter adjacency)
    prev_chapter_last: str | None = None
    at_chapter_open = False  # first paragraph after a numbered chapter heading
    for block in blocks:
        if block.startswith("#"):
            if _NUMBERED_CHAPTER_RE.match(block):
                prev_chapter_last = prev_para
                at_chapter_open = True
            out.append(block)
            prev_para = None  # adjacency does not cross a heading
            continue
        if at_chapter_open and prev_chapter_last and _boundary_echo(block, prev_chapter_last):
            at_chapter_open = False
            continue  # drop the chapter-opening echo
        if not at_chapter_open and prev_para is not None and _adjacent_echo(block, prev_para):
            continue  # drop the adjacent within-chapter echo
        at_chapter_open = False
        out.append(block)
        prev_para = block
    return "\n\n".join(out).strip() + "\n"


def _translation_long_enough(prose: str, source_words: int) -> bool:
    if source_words < 500:
        return bool(prose.strip())
    return len(prose.split()) >= _MIN_ACCEPTABLE_RATIO * source_words


def normalize_translation_prose(prose: str, *, title: str = "") -> str:
    """Apply deterministic book-level cleanup before prose is persisted.

    This is intentionally scoped to translation-edition output so the podcast
    chapter/audio routes keep their existing honorific rules.
    """
    text = (prose or "").strip()
    if not text:
        return ""
    for pattern, replacement in _SALUTATION_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    cleaned: list[str] = []
    expected = re.sub(r"\s+", " ", title or "").strip().casefold()
    for line in text.splitlines():
        m = re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if m:
            heading = re.sub(r"\s+", " ", m.group(2)).strip()
            if expected and heading.casefold() == expected:
                continue
            line = f"### {heading}"
        cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"(?m)^\s*-{3,}\s*$\n?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def translation_output_findings(
    prose: str,
    *,
    expected_title: str = "",
    frame: str = "",
    narrator_subject: str = "",
    source: str = "",
) -> list[str]:
    """Deterministically reject process chatter and structural leakage.

    Chapter prose is inserted under pipeline-owned headings. If the model emits
    its own Markdown headings or explains why the source/title do not match, the
    safest action is to retry or fail before the bad text reaches book.md.

    ``frame`` adds the narrative-person guard, and ``source`` (when the caller has
    the assigned source span in hand) adds the full ``_narrative`` battery —
    speech-tag integrity, Arabic retention, supplied diacritics, enumeration
    survival. The translation route carries the same guards as the re-voice route
    because the defects belong to the source being mishandled, not to the product.
    """
    findings: list[str] = []
    text = prose.strip()
    if not text:
        findings.append("output is empty")
        return findings
    for pattern, label in _META_COMMENTARY_PATTERNS:
        if pattern.search(text):
            findings.append(label)
    heading = _OPENING_HEADING_RE.search(text)
    if heading:
        sample = heading.group(0).strip()[:120]
        findings.append(f"contains model-owned opening heading: {sample!r}")
    if expected_title:
        quoted_title = re.escape(expected_title.strip())
        if re.search(rf"\b(?:cannot|can't|will not|won't)\s+produce\s+\"?{quoted_title}\"?", text, re.I):
            findings.append("explicitly says it cannot produce the requested chapter")
    if frame:
        from _narrative import frame_findings, narrative_person_findings

        if source:
            findings.extend(frame_findings(source, text, frame=frame, narrator_subject=narrator_subject))
        else:
            findings.extend(narrative_person_findings(text, frame, narrator_subject=narrator_subject))
    return findings


def _topic_hits(text: str) -> set[str]:
    scan = (text or "").casefold()
    hits: set[str] = set()
    for topic, words in _TOPIC_CLUSTERS.items():
        if any(re.search(rf"\b{re.escape(word.casefold())}\b", scan) for word in words):
            hits.add(topic)
    return hits


def source_title_drift_findings(title: str, source: str) -> list[str]:
    """Cheap source/title drift detector for final-PDF acceptance.

    It is intentionally deterministic and conservative: it only blocks when a
    title has a recognizable legal/teaching topic and the assigned source has no
    overlap but does have a different recognizable topic.
    """
    title_topics = _topic_hits(title)
    source_topics = _topic_hits(source[:5000])
    if title_topics and source_topics and not (title_topics & source_topics):
        return [f"title/source topic drift: title {sorted(title_topics)} vs source {sorted(source_topics)}"]
    return []


def _source_headings(source: str) -> list[str]:
    headings: list[str] = []
    for match in _SOURCE_HEADING_RE.finditer(source):
        raw = match.group(1).strip(" *:")
        if 3 <= len(raw) <= 120 and not raw.startswith("<!--"):
            headings.append(raw)
    return headings[:8]


def build_source_crosswalk(
    book_dir: Path,
    toc: dict[str, Any],
    lines: list[str],
    line_pages: list[int],
) -> list[dict[str, Any]]:
    """Build the persisted Arabic/refined source crosswalk for the book."""
    arabic_pages = _load_arabic_pages(book_dir) or {}
    entries: list[dict[str, Any]] = []
    for ch in toc.get("chapters", []):
        idx = int(ch.get("bk_index") or len(entries) + 1)
        title = str(ch.get("title") or f"Chapter {idx}")
        ranges = ch.get("source_line_ranges", [])
        source = _slice_source(lines, ranges)
        pages = _pages_for_ranges(line_pages, ranges) if line_pages else []
        arabic_nums = [n for n in pages if n in arabic_pages]
        excerpt = re.sub(r"\s+", " ", _PAGE_MARK.sub("", source)).strip()[:420]
        entries.append(
            {
                "index": idx,
                "title": title,
                "source_line_ranges": ranges,
                "source_pages": pages,
                "source_page_range": f"pp. {pages[0]}-{pages[-1]}" if pages else "",
                "arabic_source_pages": arabic_nums,
                "arabic_source_page_range": (f"pp. {arabic_nums[0]}-{arabic_nums[-1]}" if arabic_nums else ""),
                "source_headings": _source_headings(source),
                "source_excerpt": excerpt,
                "drift_findings": source_title_drift_findings(title, source),
            }
        )
    return entries
