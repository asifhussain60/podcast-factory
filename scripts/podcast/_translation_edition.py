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
    if not _translation_long_enough(out, source_words):
        raise AuthoringError(
            phase="0book-compose",
            message=(
                f"{label}: translation edition output is too compressed "
                f"({len(out.split())}/{source_words} words)"
            ),
            manual_fallback="Re-run after reducing chapter/window size or inspect the source range.",
        )
    return out


def author_translation_edition_compose(book_dir: Path, *, log=print, force: bool = False) -> Path:
    """Compose ``book/book.md`` for the translation-edition lane.

    Uses the existing ``book/book-toc.json`` from 0book-design, but writes a
    faithful translation edition instead of the normal author-first-person
    companion book. It also mirrors each generated chapter into ``chapters/`` so
    existing slide-deck authoring can operate without a separate adapter.
    """
    book_dir = Path(book_dir).resolve()
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

    parts: list[str] = [f"# {toc.get('book_title', book_dir.name)}\n"]
    previous_tail = ""
    manifest: list[dict[str, Any]] = []

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
        if not force and _cache_fresh(out_path) and out_path.read_text(encoding="utf-8").strip():
            cached = out_path.read_text(encoding="utf-8").strip()
            if _translation_long_enough(cached, len(source.split())):
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
                if not force and _cache_fresh(part_path) and part_path.read_text(encoding="utf-8").strip():
                    cached_part = part_path.read_text(encoding="utf-8").strip()
                    if _translation_long_enough(cached_part, len(part_source.split())):
                        return part_idx, cached_part
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
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log(f"    translation-edition-compose: assembled book.md with {len(manifest)} chapters")
    return book_md
