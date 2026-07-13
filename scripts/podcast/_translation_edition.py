"""Translation-edition helpers.

This module defines the contract for a faithful, visually enhanced translation
PDF path. It is deliberately separate from ``content_profile``: the profile says
what the source is about; ``deliverable_mode`` says what product we are making.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_compose import (
    _PAGE_MARK,
    _load_arabic_pages,
    _line_pages,
    _pages_for_ranges,
    _quran_anchor_block,
    _slice_source,
)
from _translit import simplify_transliteration

TRANSLATION_EDITION_MODE = "translation_edition"
DEFAULT_VISUAL_STYLE = "black_white"

_COMPOSE_TIMEOUT = 900
_RETRY_TIMEOUT = 1350
_LONG_CHAPTER_WORDS = 4500
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
    "sales": ("market", "trade", "merchant", "sale", "sell", "buy", "property", "rent", "loan", "deposit", "hawala", "sponsorship", "partnership", "pre-emption"),
    "oaths": ("oath", "vow", "atonement", "expiation", "swear", "perjury"),
    "food": ("food", "drink", "healing", "medicine", "illness", "eat", "health"),
    "dress": ("wear", "dress", "clothing", "garment", "adornment", "ornament", "fragrance", "perfume", "ring", "silk"),
    "hunting": ("hunt", "hunting", "game", "slaughter", "sacrifice", "prey", "animal", "knife", "aqiqah"),
    "marriage": ("marriage", "marry", "spouse", "wife", "husband", "dowry", "wedding", "household"),
    "divorce": ("divorce", "separation", "iddah", "mourning", "mut'a", "khul", "li'an"),
    "inheritance": ("freedom", "generosity", "gift", "bequest", "inheritance", "estate", "shares", "heir", "slave", "manumission"),
    "judiciary": ("wrong", "redress", "crime", "blood money", "offense", "hudud", "judge", "evidence", "testimony", "found property", "retaliation"),
}


def read_series_config(book_dir: Path) -> dict[str, Any]:
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def deliverable_mode(book_dir: Path) -> str:
    cfg = read_series_config(book_dir)
    return str(cfg.get("deliverable_mode") or "").strip()


def is_translation_edition(book_dir: Path) -> bool:
    return deliverable_mode(book_dir) == TRANSLATION_EDITION_MODE


def translation_policy(book_dir: Path) -> dict[str, Any]:
    cfg = read_series_config(book_dir)
    policy = cfg.get("translation_policy") or {}
    return policy if isinstance(policy, dict) else {}


def requires_monochrome_visuals(book_dir: Path) -> bool:
    cfg = read_series_config(book_dir)
    policy = translation_policy(book_dir)
    style = str(
        cfg.get("visual_style")
        or policy.get("visual_style")
        or ""
    ).strip().lower()
    if style in {"black_white", "black-and-white", "monochrome", "bw"}:
        return True
    return bool(policy.get("monochrome_visuals"))


def contract_findings(book_dir: Path) -> list[str]:
    """Return contract findings for translation-edition mode.

    Empty means the book is configured safely. The checks are deterministic and
    cheap, so callers can run them before any LLM spend.
    """
    findings: list[str] = []
    cfg = read_series_config(book_dir)
    policy = translation_policy(book_dir)

    if cfg.get("deliverable_mode") != TRANSLATION_EDITION_MODE:
        findings.append("deliverable_mode must be 'translation_edition'")

    augmentation = str(policy.get("augmentation") or "forbidden").strip().lower()
    if augmentation not in {"forbidden", "none", "source_only"}:
        findings.append("translation_policy.augmentation must forbid outside-source augmentation")

    denoise = str(policy.get("denoise") or "teaching_only").strip().lower()
    if denoise not in {"teaching_only", "none", "light"}:
        findings.append("translation_policy.denoise must be teaching_only, light, or none")

    if not bool(policy.get("preserve_arabic_terms", True)):
        findings.append("translation_policy.preserve_arabic_terms must stay true")

    if not requires_monochrome_visuals(book_dir):
        findings.append("visual_style must be black_white/monochrome for this path")

    return findings


def assert_translation_contract(book_dir: Path) -> None:
    findings = contract_findings(book_dir)
    if findings:
        raise AuthoringError(
            phase="translation-edition",
            message="translation-edition contract failed: " + "; ".join(findings),
            manual_fallback=(
                "Set _system/series-config.yaml deliverable_mode=translation_edition "
                "and translation_policy.augmentation=forbidden before running this path."
            ),
        )


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
            vals = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
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


def translation_output_findings(prose: str, *, expected_title: str = "") -> list[str]:
    """Deterministically reject process chatter and structural leakage.

    Chapter prose is inserted under pipeline-owned headings. If the model emits
    its own Markdown headings or explains why the source/title do not match, the
    safest action is to retry or fail before the bad text reaches book.md.
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
        return [
            "title/source topic drift: title "
            f"{sorted(title_topics)} vs source {sorted(source_topics)}"
        ]
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
        entries.append({
            "index": idx,
            "title": title,
            "source_line_ranges": ranges,
            "source_pages": pages,
            "source_page_range": f"pp. {pages[0]}-{pages[-1]}" if pages else "",
            "arabic_source_pages": arabic_nums,
            "arabic_source_page_range": (
                f"pp. {arabic_nums[0]}-{arabic_nums[-1]}" if arabic_nums else ""
            ),
            "source_headings": _source_headings(source),
            "source_excerpt": excerpt,
            "drift_findings": source_title_drift_findings(title, source),
        })
    return entries


def _arabic_ground_truth_block(arabic_src: str) -> str:
    if not arabic_src:
        return ""
    return f"""
ORIGINAL-LANGUAGE SOURCE — GROUND TRUTH
The Arabic OCR for the source pages behind this chapter is reproduced below. Use it only to preserve
Arabic terms, Quran verses, hadith, poetry, and direct quotations that belong in the teaching. The OCR
may contain stray marks or broken letters, so correct obvious OCR artifacts. Do not add outside material.

{arabic_src}
"""


def _compose_prompt(
    title: str,
    body: str,
    previous_tail: str,
    *,
    arabic_src: str = "",
    quran_anchor: str = "",
) -> str:
    continuity = (
        "\nContinuity note: the previous chapter ended with this thought. "
        "Open naturally without repeating it:\n"
        f"{previous_tail}\n"
        if previous_tail else ""
    )
    return f"""You are preparing a faithful English translation edition of a non-English Islamic teaching text.

Write one polished chapter titled "{title}" from the source passage below.

Core rule: this is LLM-enriched translation, not augmentation. Enrichment here means clear articulation,
clean paragraphing, careful denoising, and readable English. It does not mean adding outside facts,
new examples, modern analogies, doctrine from other books, or explanatory material not present in the source.

Preserve meaning:
- Preserve every teaching, argument, example, named person, citation, Quran verse, hadith, quote, and Arabic term present in the source.
- Preserve Arabic script when it appears in the source. Do not romanize it away.
- If a Quran verse, hadith, poem, or quoted saying appears, keep it visibly quoted and keep the attribution present in the source.
- Do not invent canonical Arabic from memory. If the source gives Arabic, preserve it; if the source gives only a translation, translate/polish only that.
- Use the original-language source block only as preservation evidence, not as permission to add new side material.
- Keep salutations compact. Do not repeatedly spell out long English honorifics. Use only these compact forms in English prose: (عليهم السلام), (ع), and (رض).
{quran_anchor}{_arabic_ground_truth_block(arabic_src)}

Denoise:
- Remove or compress historical side information, bibliographic apparatus, editorial notes, damaged-manuscript notes, chain-of-publication details, translator/editor commentary, and background digressions unless they directly teach the point of the chapter.
- Keep the author's teaching as the spine.

Style:
- Clear, dignified English.
- No podcast language.
- No episode references.
- No bullet-list study guide unless the source itself is enumerating points.
- No em dashes.
{continuity}
Output only the chapter prose. No preamble, no code fences, no notes.

SOURCE PASSAGE
{body}"""


def _compose_one(
    title: str,
    body: str,
    previous_tail: str,
    book_dir: Path,
    label: str,
    log,
    *,
    arabic_src: str = "",
    quran_anchor: str = "",
) -> str:
    prompt = _compose_prompt(
        title,
        body,
        previous_tail,
        arabic_src=arabic_src,
        quran_anchor=quran_anchor,
    )
    rc, out, err = _run_claude_p_with_retry(
        prompt, timeout=_COMPOSE_TIMEOUT, book_dir=book_dir,
        phase="0book-compose", step=f"translation-{label}", log=log,
    )
    out = (out or "").strip()
    if rc != 0:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition compose failed rc={rc}: {err[:300]}",
            manual_fallback="Re-run the translation edition path; completed chunks are skipped.",
        )
    source_words = len(body.split())
    if source_words >= 200 and len(out.split()) < 0.55 * source_words:
        log(f"      {label}: short ({len(out.split())}/{source_words}w) - retry")
        rc2, out2, _ = _run_claude_p_with_retry(
            prompt
            + "\n\nYour previous attempt was too compressed. Rewrite faithfully, preserving the full teaching.",
            timeout=_RETRY_TIMEOUT, book_dir=book_dir,
            phase="0book-compose", step=f"translation-{label}-retry", log=log,
        )
        if rc2 == 0 and len((out2 or "").split()) > len(out.split()):
            out = (out2 or "").strip()
    findings = translation_output_findings(out, expected_title=title)
    if findings:
        log(f"      {label}: invalid translation output ({'; '.join(findings[:3])}) - retry")
        retry_prompt = (
            prompt
            + "\n\nYour previous answer included process commentary or model-owned headings. "
            "Rewrite now as clean chapter prose only. Do not mention instructions, options, "
            "source mismatch, inability, the title selection, or the prompt. Do not emit Markdown headings."
        )
        rc2, out2, err2 = _run_claude_p_with_retry(
            retry_prompt,
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-integrity-retry",
            log=log,
        )
        if rc2 == 0:
            candidate = (out2 or "").strip()
            if not translation_output_findings(candidate, expected_title=title):
                out = candidate
            else:
                out = candidate or out
        else:
            log(f"      {label}: integrity retry failed rc={rc2}: {err2[:160]}")
        findings = translation_output_findings(out, expected_title=title)
    if findings:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition output failed integrity gate: "
                    + "; ".join(findings),
            manual_fallback=(
                "Re-run 0book-design/0book-compose after inspecting the source range; "
                "the pipeline refused to persist model commentary or generated headings."
            ),
        )
    if not _translation_long_enough(out, source_words):
        raise AuthoringError(
            phase="0book-compose",
            message=(
                f"{label}: translation edition output is too compressed "
                f"({len(out.split())}/{source_words} words)"
            ),
            manual_fallback="Re-run after reducing chapter/window size or inspect the source range.",
        )
    return normalize_translation_prose(out, title=title)


def author_translation_edition_compose(
    book_dir: Path, *, log=print, force: bool = False, enforce_contract: bool = True
) -> Path:
    """Compose ``book/book.md`` for the translation-edition lane.

    Uses the existing ``book/book-toc.json`` from 0book-design, but writes a
    faithful translation edition instead of the normal author-first-person
    companion book. It also mirrors each generated chapter into ``chapters/`` so
    existing slide-deck authoring can operate without a separate adapter.

    ``enforce_contract`` gates the ``deliverable_mode == translation_edition`` +
    monochrome-visual contract. The legacy lane keeps it True. Book Pipeline v2
    drives route selection through the two knobs (``book_augmentation`` /
    ``book_voice``), NOT through ``deliverable_mode``, so it reuses this function
    as the shared *faithful base* with ``enforce_contract=False``.
    """
    book_dir = Path(book_dir).resolve()
    if enforce_contract:
        assert_translation_contract(book_dir)

    toc_path = book_dir / "book" / "book-toc.json"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not toc_path.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {toc_path} - run 0book-design first.",
            manual_fallback="Run the translation edition driver from the beginning.",
        )
    if not refined_path.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {refined_path} - run 0b first.",
            manual_fallback="Run Phase 0a/0b before translation edition compose.",
        )

    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    lines = refined_path.read_text(encoding="utf-8").split("\n")
    chunks_dir = book_dir / "book" / "_chunks" / "translation"
    chapters_dir = book_dir / "chapters"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    arabic_pages = _load_arabic_pages(book_dir)
    line_pages = _line_pages(lines) if arabic_pages else []
    crosswalk = build_source_crosswalk(book_dir, toc, lines, line_pages or _line_pages(lines))
    drift = [
        f"chapter {entry['index']} ({entry['title']}): {'; '.join(entry['drift_findings'])}"
        for entry in crosswalk
        if entry.get("drift_findings")
    ]
    if drift:
        raise AuthoringError(
            phase="0book-compose",
            message="source crosswalk failed title/source alignment: " + "; ".join(drift[:4]),
            manual_fallback=(
                "Fix book/book-toc.json source_line_ranges or chapter titles, then rerun "
                "translation edition compose. OCR/refinement/audio do not need to rerun."
            ),
        )
    (book_dir / "book" / "source-crosswalk.json").write_text(
        json.dumps({
            "schema": "podcast.translation-edition.source-crosswalk/v1",
            "book": book_dir.name,
            "chapters": crosswalk,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    parts: list[str] = [f"# {toc.get('book_title', book_dir.name)}\n"]
    previous_tail = ""
    manifest: list[dict[str, Any]] = []
    prior_manifest: dict[int, dict[str, Any]] = {}
    prior_manifest_path = book_dir / "_system" / "translation-edition-manifest.json"
    if prior_manifest_path.exists():
        try:
            prior_data = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            prior_manifest = {
                int(item.get("index")): item
                for item in (prior_data.get("chapters") or [])
                if item.get("index") is not None
            }
        except Exception:
            prior_manifest = {}

    def _arabic_for(ranges: list[list[int]]) -> tuple[str, str]:
        if not arabic_pages or not ranges:
            return "", ""
        nums = [n for n in _pages_for_ranges(line_pages, ranges) if n in arabic_pages]
        if not nums:
            return "", ""
        return "\n\n".join(arabic_pages[n] for n in nums), f"pp.{nums[0]}-{nums[-1]}"

    if arabic_pages:
        log(f"    translation-edition-compose: Arabic ground truth loaded ({len(arabic_pages)} OCR pages)")
    max_workers = max(1, int(os.environ.get("TRANSLATION_EDITION_MAX_WORKERS", "3")))

    def _cache_fresh(path: Path) -> bool:
        try:
            return path.stat().st_mtime >= refined_path.stat().st_mtime
        except OSError:
            return False

    for ch in toc.get("chapters", []):
        idx = int(ch.get("bk_index") or len(manifest) + 1)
        title = str(ch.get("title") or f"Chapter {idx}")
        label = f"bk-{idx:02d}"
        ch_ranges = ch.get("source_line_ranges", [])
        source = _slice_source(lines, ch_ranges)
        out_path = chunks_dir / f"{label}.md"
        prior = prior_manifest.get(idx) or {}
        cache_matches_source = (
            prior.get("title") == title
            and prior.get("source_line_ranges") == ch_ranges
        )
        if (
            not force
            and cache_matches_source
            and _cache_fresh(out_path)
            and out_path.read_text(encoding="utf-8").strip()
        ):
            cached = out_path.read_text(encoding="utf-8").strip()
            cached = normalize_translation_prose(cached, title=title)
            cached_findings = translation_output_findings(cached, expected_title=title)
            if cached_findings:
                log(
                    f"      {label}: cached translation failed integrity gate "
                    f"({'; '.join(cached_findings[:3])}) - recompute"
                )
                prose = ""
            elif _translation_long_enough(cached, len(source.split())):
                prose = cached
            else:
                log(
                    f"      {label}: cached translation is too compressed "
                    f"({len(cached.split())}/{len(source.split())} words) - recompute"
                )
                prose = ""
        else:
            prose = ""
        if not prose:
            windows = (
                _iter_source_windows(lines, ch_ranges)
                if len(source.split()) > _LONG_CHAPTER_WORDS else []
            )
            if not windows:
                windows = [(source, ch_ranges)]
            log(
                f"      {label}: {title} ({len(source.split())} source words"
                + (f", {len(windows)} windows" if len(windows) > 1 else "")
                + ") -> translation edition"
            )
            prose_parts: list[str] = []

            def compose_part(part_idx: int, part_source: str, part_ranges: list[list[int]]) -> tuple[int, str]:
                part_label = label if len(windows) == 1 else f"{label}-part-{part_idx:02d}"
                part_path = chunks_dir / f"{part_label}.md"
                if (
                    not force
                    and cache_matches_source
                    and _cache_fresh(part_path)
                    and part_path.read_text(encoding="utf-8").strip()
                ):
                    cached_part = part_path.read_text(encoding="utf-8").strip()
                    cached_part = normalize_translation_prose(cached_part, title=title)
                    cached_findings = translation_output_findings(cached_part, expected_title=title)
                    if cached_findings:
                        log(
                            f"        {part_label}: cached translation failed integrity gate "
                            f"({'; '.join(cached_findings[:3])}) - recompute"
                        )
                    elif _translation_long_enough(cached_part, len(part_source.split())):
                        return part_idx, cached_part
                    else:
                        log(
                            f"        {part_label}: cached translation is too compressed "
                            f"({len(cached_part.split())}/{len(part_source.split())} words) - recompute"
                        )
                qa_block, qa_stats = _quran_anchor_block(part_source)
                arabic_src, arabic_span = _arabic_for(part_ranges)
                if qa_stats["cited"]:
                    log(
                        f"        {part_label}: Quran anchoring - {qa_stats['anchored']}/"
                        f"{qa_stats['cited']} cited verses anchored"
                    )
                log(
                    f"        {part_label}: {len(part_source.split())} source words"
                    + (f", Arabic {arabic_span}" if arabic_span else "")
                )
                part_prose = _compose_one(
                    title,
                    part_source,
                    previous_tail,
                    book_dir,
                    part_label,
                    log,
                    arabic_src=arabic_src,
                    quran_anchor=qa_block,
                )
                part_path.write_text(part_prose.rstrip() + "\n", encoding="utf-8")
                return part_idx, part_prose

            if len(windows) > 1 and max_workers > 1:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                log(f"        {label}: composing windows in parallel (max_workers={max_workers})")
                results: list[tuple[int, str]] = []
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futures = [
                        ex.submit(compose_part, part_idx, part_source, part_ranges)
                        for part_idx, (part_source, part_ranges) in enumerate(windows, start=1)
                    ]
                    for fut in as_completed(futures):
                        results.append(fut.result())
                prose_parts = [prose for _, prose in sorted(results)]
            else:
                for part_idx, (part_source, part_ranges) in enumerate(windows, start=1):
                    _, part_prose = compose_part(part_idx, part_source, part_ranges)
                    prose_parts.append(part_prose)
            prose = "\n\n".join(prose_parts).strip()
            prose = normalize_translation_prose(prose, title=title)
            out_path.write_text(prose.rstrip() + "\n", encoding="utf-8")

        chapter_slug = f"ch{idx:02d}-{_slugify(title, label)}"
        chapter_path = chapters_dir / f"{chapter_slug}.txt"
        chapter_path.write_text(f"# {title}\n\n{prose.rstrip()}\n", encoding="utf-8")
        parts.append(f"## {idx}. {title}\n\n{prose}\n")
        previous_tail = " ".join(prose.split()[-80:])
        manifest.append({
            "index": idx,
            "title": title,
            "chapter_file": str(chapter_path.relative_to(book_dir)),
            "source_line_ranges": ch.get("source_line_ranges", []),
            "source_words": len(source.split()),
            "output_words": len(prose.split()),
        })

    book_md = book_dir / "book" / "book.md"
    book_md.write_text(simplify_transliteration("\n".join(parts).rstrip() + "\n"), encoding="utf-8")
    (book_dir / "_system" / "translation-edition-manifest.json").write_text(
        json.dumps({
            "schema": "podcast.translation-edition/v1",
            "mode": TRANSLATION_EDITION_MODE,
            "augmentation": "forbidden",
            "visual_style": DEFAULT_VISUAL_STYLE,
            "chapters": manifest,
            "source_crosswalk": "book/source-crosswalk.json",
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log(f"    translation-edition-compose: assembled book.md with {len(manifest)} chapters")
    return book_md
