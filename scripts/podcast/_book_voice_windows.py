"""Window/cache helpers for ``_book_voice``.

Split from ``_book_voice.py`` under DR-005 after the Sessions articulation path
added Arabic placeholder protection, structural-artifact protection, and
per-window caching. The seam is the window machinery itself: this module decides
what a model sees and what can be reused; ``_book_voice`` decides when to run a
book pass and how to record the result.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

from _arabic_coverage import ARABIC_BODY
from _book_compose import _arabic_run_count
from _translation_text import _split_paragraphs

_ARABIC_PROTECT_RE = re.compile(f"[{ARABIC_BODY}]{{2,}}")

# `_WINDOW_WORDS` sits under `_LONG_CHAPTER_WORDS` so a split chapter always
# yields at least two substantive windows. 4,500 -> 4,000 on 2026-08-11,
# DELIBERATELY un-matched from `_translation_edition._LONG_CHAPTER_WORDS` (that
# path windows a SOURCE span; this one owns its own seams). Full account in
# framework.md — a 4,479-word chapter went to the model whole and came back an
# 840-word summary, twenty-one words under the old line.
_WINDOW_WORDS = 2500
_WINDOW_ARABIC_RUNS = 24
# A trailing window smaller than this fraction of the target is folded back into
# its predecessor rather than shipped as a runt.
_RUNT_WINDOW_FRACTION = 0.4
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WINDOW_CACHE_NAME = "book-voice-window-cache.json"
_ARABIC_PLACEHOLDER_RE = re.compile(r"\[\[ARABIC_\d{3}\]\]")
_ARTIFACT_PLACEHOLDER_RE = re.compile(r"\[\[ARTIFACT_\d{3}\]\]")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")


def _norm_for_ratio(text: str) -> str:
    return " ".join((text or "").split())


def _similarity(base_text: str, candidate: str) -> float:
    """Whitespace-normalised similarity, 0..1. Computed per window, never per
    whole chapter — SequenceMatcher degrades badly on very long inputs."""
    return SequenceMatcher(None, _norm_for_ratio(base_text), _norm_for_ratio(candidate)).ratio()


def _protect_arabic_runs(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        placeholder = f"[[ARABIC_{len(replacements) + 1:03d}]]"
        replacements[placeholder] = match.group(0)
        return placeholder

    return _ARABIC_PROTECT_RE.sub(repl, text), replacements


def _restore_arabic_runs(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for placeholder, arabic in replacements.items():
        restored = restored.replace(placeholder, arabic)
    return restored


def _arabic_placeholder_findings(replacements: dict[str, str], candidate: str) -> list[str]:
    if not replacements:
        return []
    found = _ARABIC_PLACEHOLDER_RE.findall(candidate or "")
    expected = list(replacements)
    findings: list[str] = []
    missing = [placeholder for placeholder in expected if placeholder not in found]
    unexpected = sorted({placeholder for placeholder in found if placeholder not in replacements})
    if missing:
        findings.append("protected Arabic placeholders missing: " + ", ".join(missing))
    if unexpected:
        findings.append("unknown Arabic placeholders introduced: " + ", ".join(unexpected))
    return findings


def _structural_artifact_findings(replacements: dict[str, str], candidate: str) -> list[str]:
    if not replacements:
        return []
    found = _ARTIFACT_PLACEHOLDER_RE.findall(candidate or "")
    expected = list(replacements)
    findings: list[str] = []
    missing = [placeholder for placeholder in expected if placeholder not in found]
    unexpected = sorted({placeholder for placeholder in found if placeholder not in replacements})
    if missing:
        findings.append("protected structural artifacts missing: " + ", ".join(missing))
    if unexpected:
        findings.append("unknown structural artifacts introduced: " + ", ".join(unexpected))
    return findings


def _window_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _window_cache_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / _WINDOW_CACHE_NAME


def _read_window_cache(book_dir: Path) -> dict:
    path = _window_cache_path(book_dir)
    if not path.exists():
        return {"schema": "podcast.book-voice-window-cache/v1", "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": "podcast.book-voice-window-cache/v1", "entries": {}}
    data.setdefault("entries", {})
    return data


def _write_window_cache(book_dir: Path, data: dict) -> None:
    path = _window_cache_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _window_cache_key(label: str, window: str) -> str:
    return f"{label}:{_window_fingerprint(window)}"


def _cache_window_part(book_dir: Path, label: str, window: str, part: str) -> None:
    cache = _read_window_cache(book_dir)
    cache["entries"][_window_cache_key(label, window)] = {
        "label": label,
        "base_sha256": _window_fingerprint(window),
        "part": part,
    }
    _write_window_cache(book_dir, cache)


def _cached_window_part(book_dir: Path, label: str, window: str) -> str | None:
    entry = _read_window_cache(book_dir).get("entries", {}).get(_window_cache_key(label, window))
    if not isinstance(entry, dict):
        return None
    part = entry.get("part")
    return part if isinstance(part, str) and part.strip() else None


def _drop_cached_window_part(book_dir: Path, label: str, window: str) -> None:
    cache = _read_window_cache(book_dir)
    key = _window_cache_key(label, window)
    if key in cache.get("entries", {}):
        del cache["entries"][key]
        _write_window_cache(book_dir, cache)


def _protected_artifact_paragraph(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if lines and all(line.startswith(">") for line in lines):
        return True
    if lines and all(line.startswith("#") for line in lines):
        return True
    if _MARKDOWN_IMAGE_RE.search(stripped):
        return True
    words = re.findall(r"[A-Za-z]+", stripped)
    if len(stripped) <= 80 and 1 <= len(words) <= 8 and not re.search(r"[.!?]\s*$", stripped):
        letters = [ch for ch in stripped if ch.isalpha()]
        upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters) if letters else 0
        if upper_ratio >= 0.65 or " vs " in stripped.lower():
            return True
    return False


def _protect_structural_artifacts(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    paragraphs: list[str] = []
    for paragraph in _split_paragraphs(text or ""):
        if _protected_artifact_paragraph(paragraph):
            placeholder = f"[[ARTIFACT_{len(replacements) + 1:03d}]]"
            replacements[placeholder] = paragraph
            paragraphs.append(placeholder)
        else:
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs), replacements


def _restore_structural_artifacts(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for placeholder, artifact in replacements.items():
        restored = restored.replace(placeholder, artifact)
    return restored


def _iter_prose_windows(text: str, *, target_words: int = _WINDOW_WORDS) -> list[str]:
    """Split chapter prose into paragraph-aligned windows of ~``target_words``.

    Paragraph-aligned so a window never opens or closes mid-thought, which is
    what makes the per-window fidelity gates meaningful.
    """
    paragraphs = []
    for para in _split_paragraphs(text):
        if len(para.split()) <= target_words and _arabic_run_count(para) <= _WINDOW_ARABIC_RUNS:
            paragraphs.append(para)
            continue
        pieces = [p.strip() for p in _SENTENCE_SPLIT_RE.split(para) if p.strip()]
        if len(pieces) <= 1:
            paragraphs.append(para)
            continue
        current: list[str] = []
        for sentence in pieces:
            candidate = " ".join([*current, sentence]).strip()
            if current and (
                len(candidate.split()) > target_words or _arabic_run_count(candidate) > _WINDOW_ARABIC_RUNS
            ):
                paragraphs.append(" ".join(current))
                current = [sentence]
            else:
                current.append(sentence)
        if current:
            paragraphs.append(" ".join(current))
    if not paragraphs:
        return []
    windows: list[str] = []
    current: list[str] = []
    current_words = 0
    current_arabic = 0

    for para in paragraphs:
        para_words = len(para.split())
        para_arabic = _arabic_run_count(para)
        if current and (
            current_words + para_words > target_words or current_arabic + para_arabic > _WINDOW_ARABIC_RUNS
        ):
            windows.append("\n\n".join(current))
            current, current_words, current_arabic = [], 0, 0
        current.append(para)
        current_words += para_words
        current_arabic += para_arabic
        if current_words >= target_words or current_arabic >= _WINDOW_ARABIC_RUNS:
            windows.append("\n\n".join(current))
            current, current_words, current_arabic = [], 0, 0
    if current:
        if (
            windows
            and current_words < target_words * _RUNT_WINDOW_FRACTION
            and _arabic_run_count(windows[-1]) + current_arabic <= _WINDOW_ARABIC_RUNS
        ):
            windows[-1] = windows[-1] + "\n\n" + "\n\n".join(current)
        else:
            windows.append("\n\n".join(current))
    return windows


def _protected_artifact_window(text: str) -> bool:
    """A quote-only window is already in its publishable form.

    Quran, hadith, poetry, and other source quotations are protected artifacts:
    the articulation pass may clean prose around them, but forcing the artifact
    itself through the model only creates opportunities to drop Arabic, add
    reader-address, or paraphrase a quotation. If every non-blank line is a
    Markdown blockquote, exact preservation is the quality outcome.
    """
    paragraphs = _split_paragraphs(text or "")
    return bool(paragraphs) and all(_protected_artifact_paragraph(paragraph) for paragraph in paragraphs)
