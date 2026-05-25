"""EnglishReviewAdapter — typos-only reviewer for KSESSIONS bundles.

Scope per spec: only `type: "typo"` annotations. Skip glossary, skip
sentence-completion, skip quran-uncited (English prose doesn't have the same
'سورۃ <name>' pattern, and English KSESSIONS bundles are rare anyway).
"""
from __future__ import annotations
import re

from .base import ReviewAdapter, Annotation


_EN_TYPO_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("triple-period",        re.compile(r"\.{4,}"),     "Four or more periods in a row (likely OCR)"),
    ("doubled-comma",        re.compile(r",,{1,}"),     "Doubled comma (likely OCR)"),
    ("space-before-punct",   re.compile(r"\s+[,.;:!?]"), "Whitespace before punctuation (typesetting artifact)"),
    ("replacement-char",     re.compile(r"�"),           "Unicode replacement character U+FFFD"),
    ("triple-space",         re.compile(r"   +"),       "Three or more ASCII spaces (likely OCR)"),
]


class EnglishReviewAdapter(ReviewAdapter):
    language = "en"

    def review_section(
        self,
        section_text: str,
        section_id: int,
        section_position: int,
        label: str,
        glossary: dict,
        quran_corpus,
    ) -> list[Annotation]:
        out: list[Annotation] = []
        for name, pat, descr in _EN_TYPO_PATTERNS:
            for m in pat.finditer(section_text):
                start = max(0, m.start() - 30)
                end = min(len(section_text), m.end() + 30)
                excerpt = section_text[start:end].replace("\n", " ⏎ ")
                out.append(Annotation(
                    section_id=section_id,
                    section_position=section_position,
                    type="typo",
                    confidence="high",
                    original_excerpt=excerpt,
                    annotation=f"Remove or replace artifact ({name})",
                    rationale=descr,
                    source="self",
                ))
        return out
