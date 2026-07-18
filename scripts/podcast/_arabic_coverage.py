"""_arabic_coverage.py — Arabic-script preservation for the translation lane.

The v2 compose route grounds its Arabic in the OCR of the source pages, but the
model applies the "preserve Arabic" instruction unevenly: a cluster of adjacent
Quran citations can be rendered English-only while standalone sayings keep their
script. This module is the deterministic safety net around that — it identifies
the quoted verse/hadith/saying spans in the ground truth, measures how much Arabic
actually reached the composed output, and (when a window falls short) builds the
targeted retry instruction that names the specific spans the model must restore.

Split out of ``_translation_edition`` (2026-07-18) to keep that module under the
DR-005 line cap; the compose orchestration imports the two entry points it needs
(``arabic_ground_truth_block`` for the prompt, ``arabic_coverage_shortfall`` for
the gate). Everything here is pure/deterministic — no LLM, no I/O — so it is unit
-tested directly.
"""

from __future__ import annotations

import re

# Arabic-script Unicode coverage: main block + supplement + extended-A + the two
# presentation-forms ranges. Defined once so the ground-truth prompt, the source
# quote counter, and the output run counter all agree on what "Arabic" means.
_ARABIC_CLASS = r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
_ARABIC_SCRIPT_RE = re.compile(_ARABIC_CLASS)
# A verse/hadith/saying fenced by the printed edition's quotation delimiters. OCR
# mangles individual marks, so openers and closers are matched loosely and the span
# length filter (below) is what removes short apparatus like variant-reading notes.
# This one pattern feeds both the source counter and the retry hint, so the count
# and the named evidence can never diverge.
_ARABIC_QUOTE_SPAN_RE = re.compile(r"(?:«|\(\(|\(«|﴿)\s*(" + _ARABIC_CLASS + r"[^«»()\[\]﴿﴾]{6,}?)\s*(?:»|\)\)|\)|﴾)")
# Minimum Arabic letters for a run/quote to count — filters stray inline terms,
# variant-reading notes, and OCR speckle from the verse/hadith spans this is about.
_ARABIC_RUN_MIN_CHARS = 8
_ARABIC_QUOTE_MIN_CHARS = 12
# Only gate a window that carries a real quotation cluster, and retry when the
# surviving Arabic falls below this fraction of the source's quotation count. The
# OCR pages are denser than the faithful edition, so this floor is deliberately
# below 1.0; keep-best + non-fatal (in the caller) make an occasional needless
# retry cost nothing but time. This is the safety net — the strengthened
# ground-truth prompt is what actually lifts first-pass coverage.
_ARABIC_COVERAGE_MIN_QUOTES = 5
_ARABIC_COVERAGE_FLOOR = 0.5


def arabic_ground_truth_block(arabic_src: str) -> str:
    """The ground-truth prompt block: Arabic OCR + the mandate to preserve script."""
    if not arabic_src:
        return ""
    return f"""
ORIGINAL-LANGUAGE SOURCE — GROUND TRUTH
The Arabic OCR for the source pages behind this chapter is reproduced below. Every Quran verse, hadith,
and directly-quoted saying that belongs in the teaching MUST be rendered in its Arabic script drawn from
this block — presented as a visibly quoted block with the English translation beneath it — never in English
alone and never romanized. Use this block only to preserve that Arabic (terms, verses, hadith, poetry,
quotations); it may contain stray marks or broken letters, so correct obvious OCR artifacts. Do not add
outside material.

{arabic_src}
"""


def arabic_quote_spans(arabic_src: str) -> list[str]:
    """Distinct quoted verse/hadith/saying spans in the Arabic OCR ground truth.

    Delimiter-fenced, deduped, and length-filtered so short apparatus (variant
    readings, footnote refs) is excluded. This is the one place quotations are
    identified — both the count and the retry evidence derive from it."""
    if not arabic_src:
        return []
    seen: list[str] = []
    for m in _ARABIC_QUOTE_SPAN_RE.finditer(arabic_src):
        span = re.sub(r"\s+", " ", m.group(1)).strip()
        if len(_ARABIC_SCRIPT_RE.findall(span)) < _ARABIC_QUOTE_MIN_CHARS:
            continue
        if span not in seen:
            seen.append(span)
    return seen


def arabic_quote_count(arabic_src: str) -> int:
    """Expected number of Arabic quotation blocks for the pages behind this window."""
    return len(arabic_quote_spans(arabic_src))


def arabic_run_spans(text: str, min_chars: int = _ARABIC_RUN_MIN_CHARS) -> list[str]:
    """Distinct Arabic-script runs of at least ``min_chars`` Arabic letters.

    Only whitespace continues a run — a multi-word verse stays ONE span because
    Arabic-native punctuation (comma ،, diacritics, ayah marks) already lives in
    the Arabic block. Any non-Arabic, non-space character (a Latin word, a paren, a
    guillemet) breaks the run, so two adjacent parenthetical verses count as two. In
    an English chapter each surviving Arabic quotation is one such run — the natural
    measure of how much Arabic script actually reached the output."""
    spans: list[str] = []
    cur: list[str] = []
    cur_ar = 0
    for ch in text:
        if _ARABIC_SCRIPT_RE.match(ch):
            cur.append(ch)
            cur_ar += 1
        elif ch.isspace():
            cur.append(ch)
        else:
            if cur_ar >= min_chars:
                spans.append("".join(cur).strip())
            cur = []
            cur_ar = 0
    if cur_ar >= min_chars:
        spans.append("".join(cur).strip())
    return spans


def arabic_coverage_hint(arabic_src: str, limit: int = 24) -> str:
    """The Arabic quotation spans from the OCR, as targeted retry evidence."""
    return "\n".join(f"- {s}" for s in arabic_quote_spans(arabic_src)[:limit])


def arabic_coverage_shortfall(out: str, arabic_src: str) -> str:
    """Retry-prompt suffix when the output dropped too much Arabic, else ``""``.

    Returns a targeted instruction (naming the specific Arabic spans) only when the
    source carries a real quotation cluster AND the surviving Arabic runs fall below
    the coverage floor. An empty string means coverage is adequate — no retry."""
    if not arabic_src:
        return ""
    src_quotes = arabic_quote_count(arabic_src)
    out_runs = len(arabic_run_spans(out))
    if src_quotes < _ARABIC_COVERAGE_MIN_QUOTES or out_runs >= _ARABIC_COVERAGE_FLOOR * src_quotes:
        return ""
    return (
        "\n\nYour previous answer dropped the Arabic script for quoted verses, hadith, or sayings, "
        "rendering them in English only. EVERY Quran verse, hadith, and directly-quoted saying in the "
        "teaching MUST appear in its Arabic script from the ground-truth block, as a visibly quoted block "
        "with the English beneath. Do not romanize or drop any of them. The Arabic quotations you must "
        "include are:\n" + arabic_coverage_hint(arabic_src)
    )
