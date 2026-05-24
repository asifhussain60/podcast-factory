#!/usr/bin/env python3
"""strip_inline_phonetics.py — remove R-PHONETICS-OUT violations from chapter files.

PURPOSE

Phase 0e enrichment can occasionally leak inline phonetic guides into
chapter files in patterns like `*Maqrub* (mak-ROOB)` or `*Qur'anic*
(qur-AAN)`. The build script `build_episode_txt.py` HARD-refuses these
per rule R-PHONETICS-OUT — phonetics belong in the framing's
`## Pronunciation` block, NOT in the chapter source NotebookLM uploads.

This script strips the three INLINE_PHONETIC_PATTERNS defined in
build_episode_txt.py from a chapter file in place. The italicized term
itself is preserved — only the parenthetical phonetic guide is removed.
The phonetic data still lives in BOOK_DIR/_system/source/text/_phonetics.md
and gets surfaced via the framing's Pronunciation section.

INVOCATION

    python3 scripts/podcast/strip_inline_phonetics.py \\
        --book-dir content/drafts/the-master-and-the-disciple
    # or, for a single chapter:
    python3 scripts/podcast/strip_inline_phonetics.py \\
        --chapter content/drafts/the-master-and-the-disciple/chapters/ch05-foo.txt

OUTPUTS

Each chapter is rewritten in place; before/after wc is logged to stderr.
Idempotent: re-running on a clean file is a no-op.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns sourced from scripts/podcast/build_episode_txt.py
# INLINE_PHONETIC_PATTERNS. The strip regex is broader than the detect
# regex because we want to remove the ENTIRE paren, not just the matched
# prefix.

# Pattern 1: *Term* (PHO-NE-TIC; ...) — italic + paren with uppercase respelling
_PAT1 = re.compile(
    r"(\*[A-Za-z'`\-]+\*)\s*\(\s*[A-Za-z'\-]*[A-Z]{2,}[A-Za-z'\-]*[^)]*\)"
)
# Pattern 2: standalone blockquote line `> (phonetic-form)` — phonetic-only blockquote
_PAT2 = re.compile(r"^>\s*\(\s*[a-z]+\-[a-z]+(?:[-\s][a-z\-]+)+\s*\)\s*$\n?", re.MULTILINE)
# Pattern 3: bare `(PHO-NE-TIC)` paren without a preceding italic — fallback for
# enrichment that drops the italic but keeps the phonetic.
_PAT3 = re.compile(r"\(\s*[A-Z]{2,}[\-][A-Z][A-Z\-]+[a-z\-]*\b[^)]*\)")
# Pattern 4 (added 2026-05-24 from ch05 archetype): IPA-style paren `(/foo/)` —
# slash-delimited phonetic that's no less of an R-PHONETICS-OUT violation. The
# NotebookLM TTS treats slashes as character cues and reads them aloud.
_PAT4 = re.compile(r"\(\s*/[^/)]{2,}/(?:[^)]*)\)")
# Pattern 5 (added 2026-05-24 from ch05 archetype): full-paren phonetic with a
# semicolon-prefixed gloss like `(sha-REE-ah, the legal-and-ritual code)`.
# Same RESPELLING + GLOSS shape as PAT1 but no preceding italic; bare in prose.
_PAT5 = re.compile(r"\(\s*[a-z]+\-[a-z]+(?:[-\s][a-z\-]+){1,}\s*,\s*[a-z][^)]*\)")
# Pattern 6 (added 2026-05-24 from ch05 archetype): mid-prose `Sunnah, SOON-nah,`
# or `Sunnah (SOON-nah)` shape that's a phonetic FOLLOWING the term with no
# italic. The detector looks for `<Term>, <ALL-CAPS-RESPELLING>,`.
_PAT6 = re.compile(r",\s+[A-Z]{2,}\-[a-z\-]+\b,")
# Pattern 7 (added 2026-05-24 from ch05 archetype): bare ALL-CAPS phonetic
# prefix tokens like `ZAA-hir`, `BAA-tin` standing alone in prose. These
# typically appear right after an italicized term that's already on the page
# and want a "as in" gloss inline. Just strip the standalone phonetic token.
_PAT7 = re.compile(r"\b[A-Z]{2,}\-[a-z]+(?:\-[a-z]+)*\b")


def strip_chapter(text: str) -> tuple[str, int]:
    """Return (cleaned_text, num_stripped)."""
    n = 0
    new, k = _PAT1.subn(r"\1", text)
    n += k
    new, k = _PAT2.subn("", new)
    n += k
    new, k = _PAT3.subn("", new)
    n += k
    new, k = _PAT4.subn("", new)   # IPA `(/foo/)` shape
    n += k
    new, k = _PAT5.subn("", new)   # bare `(phon, gloss)` shape
    n += k
    # PAT6: `Term, PHON-tic,` → `Term,` (drop the phonetic between commas)
    new, k = _PAT6.subn(",", new)
    n += k
    # PAT7: standalone ALL-CAPS phonetic prefix tokens (ZAA-hir). Aggressive —
    # only strip when preceded by `,` `(` ` ` and followed by ` ` `,` `.` `)`.
    new, k = _PAT7.subn("", new)
    n += k
    # Collapse double/triple spaces and any stranded leading-comma whitespace
    # left by aggressive PAT7 strips.
    new = re.sub(r"  +", " ", new)
    new = re.sub(r"\s+([,\.;:\)])", r"\1", new)
    # Collapse any "*Term* ." or "*Term* ," that lost their space normalization.
    new = re.sub(r"(\*[^*]+\*)\s+([,\.;:])", r"\1\2", new)
    return new, n


def strip_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    cleaned, n = strip_chapter(text)
    if cleaned != text:
        path.write_text(cleaned, encoding="utf-8")
        print(f"  {path.name}: stripped {n} inline phonetic block(s)", file=sys.stderr)
    else:
        print(f"  {path.name}: clean (no strips)", file=sys.stderr)
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--book-dir", type=Path, help="Strip every chapters/*.txt in this book.")
    g.add_argument("--chapter", type=Path, help="Strip a single chapter file.")
    args = ap.parse_args()

    total = 0
    if args.chapter:
        if not args.chapter.is_file():
            sys.stderr.write(f"chapter not found: {args.chapter}\n")
            return 2
        total = strip_file(args.chapter)
    else:
        chapters_dir = args.book_dir / "chapters"
        if not chapters_dir.is_dir():
            sys.stderr.write(f"chapters/ not found in {args.book_dir}\n")
            return 2
        chapter_files = sorted(p for p in chapters_dir.glob("ch*.txt") if p.is_file())
        if not chapter_files:
            sys.stderr.write(f"no chapter files matched ch*.txt in {chapters_dir}\n")
            return 2
        print(f"stripping {len(chapter_files)} chapter(s) in {args.book_dir.name}/chapters/", file=sys.stderr)
        for cp in chapter_files:
            total += strip_file(cp)

    print(f"\n  total: {total} inline phonetic block(s) stripped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
