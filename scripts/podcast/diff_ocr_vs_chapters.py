#!/usr/bin/env python3
"""diff_ocr_vs_chapters.py — Drift report between OCR translation and curated chapters.

For the master-and-the-disciple OCR-diff track: compares the Arabic-source
machine-translation (translated-en.md from ocr_image_pages.py) against the
curated English chapter .md files. Emits a single drift-report.md that
surfaces, per chapter:

    - Length comparison (chars, words, paragraphs)
    - Proper-noun coverage (does every named person/term in the curated
      chapter appear at least once in the OCR text? OCR may use different
      spellings, so we normalize aggressively).
    - "Explanatory Clarification" blocks in curated that have no
      OCR counterpart (= curator-added value).
    - First/last 250-char head/tail side-by-side preview.

This is NOT a semantic-equivalence checker. It's a fast structural
sanity check to flag potentially substantive divergence for human review.

INVOCATION

    python3 scripts/podcast/diff_ocr_vs_chapters.py \\
        --book-dir content/drafts/the-master-and-the-disciple

OUTPUT

    BOOK_DIR/_system/source/ocr/drift-report.md
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+")
# Proper-noun proxy: capitalized words of length ≥3, not at sentence-start
# only — we do a simple capitalized-token frequency across the whole text
# and pick tokens that appear 2+ times and aren't in a stop-list.
COMMON_CAPS = {
    "The", "A", "An", "In", "Of", "And", "Or", "But", "If", "He", "She", "It",
    "They", "We", "You", "I", "His", "Her", "Their", "Our", "My", "Your",
    "This", "That", "These", "Those", "Then", "When", "Where", "What", "Who",
    "Why", "How", "Allaah", "Allah", "God", "Lord", "Master", "Disciple",
    "Chapter", "Book", "Scholar", "Seeker", "Persia", "Persian",
    "But", "So", "For", "Yet", "Even", "Such", "Also", "Now", "There", "Here",
    "On", "At", "By", "To", "Be", "Is", "Was", "Are", "Were", "Have", "Has",
    "Had", "Do", "Does", "Did", "Can", "Could", "Will", "Would", "Should",
    "May", "Might", "Must",
}


def normalize_for_match(s: str) -> str:
    """Normalize for proper-noun matching: lowercase, strip diacritic-ish
    marks like  ʿ, ʾ, ̄, hyphens, apostrophes, ' marks."""
    s = s.lower()
    for ch in "ʿʾ'’`-_·":
        s = s.replace(ch, "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_proper_nouns(text: str, min_freq: int = 1) -> list[str]:
    tokens = WORD_RE.findall(text)
    counter = Counter(t for t in tokens if t[:1].isupper() and len(t) >= 4)
    return sorted(
        {t for t, c in counter.items() if c >= min_freq and t not in COMMON_CAPS},
        key=lambda t: (-counter[t], t),
    )


def find_clarifications(chapter_text: str) -> list[str]:
    """Find `[Explanatory Clarification: ...]` or "Explanatory Clarification"
    paragraphs in the curated chapter. These are curator-added analogies
    that won't exist in OCR."""
    bracketed = re.findall(r"\[Explanatory Clarification[^\]]+\]", chapter_text)
    inline = re.findall(
        r"^Explanatory Clarification[:\n][^\n]+(?:\n[^\n]+)*",
        chapter_text,
        flags=re.MULTILINE,
    )
    return bracketed + inline


def chapter_stats(text: str) -> dict[str, int]:
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    words = WORD_RE.findall(text)
    return {
        "chars": len(text),
        "words": len(words),
        "paragraphs": len(paragraphs),
    }


def head_tail(text: str, n: int = 250) -> tuple[str, str]:
    # Skip leading markdown header for head sample
    lines = text.split("\n", 1)
    body = lines[1] if lines[0].startswith("#") else text
    body = body.lstrip()
    return body[:n], text[-n:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    args = ap.parse_args()
    book_dir: Path = args.book_dir.resolve()

    chapters_dir = book_dir / "chapters"
    ocr_translated = book_dir / "_system" / "source" / "ocr" / "translated-en.md"
    out_path = book_dir / "_system" / "source" / "ocr" / "drift-report.md"

    if not chapters_dir.is_dir():
        sys.stderr.write(f"chapters/ not found: {chapters_dir}\n")
        return 2
    if not ocr_translated.is_file():
        sys.stderr.write(f"OCR translated-en.md not found: {ocr_translated}\n")
        return 2

    ocr_text = ocr_translated.read_text(encoding="utf-8")
    ocr_norm = normalize_for_match(ocr_text)
    ocr_stats = chapter_stats(ocr_text)

    chapters = sorted(chapters_dir.glob("ch*.md"))

    lines: list[str] = []
    lines.append("# OCR ↔ Curated-Chapter Drift Report")
    lines.append("")
    lines.append(f"Book: `{book_dir.name}`")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- OCR translated-en.md: **{ocr_stats['chars']:,} chars / "
                 f"{ocr_stats['words']:,} words / {ocr_stats['paragraphs']:,} paragraphs**")
    curated_total = Counter()
    for cp in chapters:
        s = chapter_stats(cp.read_text(encoding="utf-8"))
        curated_total["chars"] += s["chars"]
        curated_total["words"] += s["words"]
        curated_total["paragraphs"] += s["paragraphs"]
    lines.append(f"- Curated chapters/*.md (sum): **{curated_total['chars']:,} chars / "
                 f"{curated_total['words']:,} words / {curated_total['paragraphs']:,} paragraphs**")
    if ocr_stats["chars"]:
        ratio = curated_total["chars"] / ocr_stats["chars"]
        lines.append(f"- Curated/OCR ratio: **{ratio:.2f}×** "
                     f"(>1 means curated added content; <1 means curator condensed)")
    lines.append("")
    lines.append("---")
    lines.append("")

    for cp in chapters:
        ch_text = cp.read_text(encoding="utf-8")
        s = chapter_stats(ch_text)
        nouns = extract_proper_nouns(ch_text)
        # Coverage: which curated proper nouns are NOT present in OCR (any spelling)?
        missing = []
        present = []
        for n in nouns[:25]:  # top 25 by frequency
            if normalize_for_match(n) in ocr_norm:
                present.append(n)
            else:
                missing.append(n)
        clarifications = find_clarifications(ch_text)
        head, _tail = head_tail(ch_text)

        lines.append(f"## {cp.stem}")
        lines.append("")
        lines.append(f"- File: [`{cp.relative_to(book_dir)}`]({cp.relative_to(book_dir)})")
        lines.append(f"- Curated: {s['chars']:,} chars / {s['words']:,} words / {s['paragraphs']:,} paragraphs")
        lines.append(f"- Top proper nouns: {', '.join(nouns[:15]) or '_(none detected)_'}")
        lines.append(f"- Proper-noun coverage in OCR: **{len(present)}/{len(present)+len(missing)} present**")
        if missing:
            lines.append(f"  - **Missing** (may signal substantive divergence or just spelling drift): "
                         f"`{'`, `'.join(missing)}`")
        if clarifications:
            lines.append(f"- Curator-added Explanatory Clarifications: **{len(clarifications)}**")
        else:
            lines.append("- Curator-added Explanatory Clarifications: 0")
        lines.append("")
        lines.append(f"  Curated chapter opening (first 250 chars):")
        lines.append("")
        lines.append(f"  > {head.replace(chr(10), ' ')[:250]}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "**Curated/OCR ratio > 1.5** → curator added substantial analogies, "
        "Explanatory Clarifications, or expansions. Decide per chapter whether "
        "those additions belong in the podcast source bundle or in a separate "
        "Customize-prompt enrichment layer."
    )
    lines.append("")
    lines.append(
        "**Missing proper nouns** → either OCR phonetic-drift (e.g., curator "
        "uses 'Aboo Maa-lik' but OCR machine-translates to 'Abu Malik' or "
        "differently) OR a genuine omission/addition. Spot-check the named "
        "term in `_system/source/ocr/translated-en.md` to confirm."
    )
    lines.append("")
    lines.append(
        "**Clarifications > 0** → curator-added analogies that won't survive "
        "an OCR-replace. Confirm OCR-DIFF mode (keep curated) before any "
        "automated rewrite."
    )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
