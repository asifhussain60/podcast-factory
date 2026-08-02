"""_arabic_paragraphs.py — the Arabic source, addressed by its own paragraph numbers.

The critical edition numbers its paragraphs, and the OCR kept those numbers: a line
beginning `(١)` opens paragraph 1 and runs until the next such line. The refined
English carries the SAME numbering, `(1)`..`(558)`, which is what makes an English
paragraph addressable in Arabic at all — `book-toc.json` maps a chapter to line
ranges in the refined English, those lines carry ¶ numbers, and those numbers name
Arabic blocks here.

WHY `^\\([٠-٩]+\\)` AND NOT A LOOSER MATCH. Footnote references in this scan are
bare, unparenthesised digits glued to the preceding letter (`وَلَا٢`, 103 of them).
Every one of the 557 real paragraph markers sits at column 0 inside parentheses, so
anchoring the pattern to the line start makes the two impossible to confuse. A
looser pattern would read footnote markers as paragraph breaks and shred the text.

¶511 IS MISSING, and is not interpolated. The OCR mangled its marker, so its text
sits inside block 510. Asking for 511 returns block 510 flagged `merged` — the
honest answer, "this text is in here somewhere", rather than a guessed split.

Reads through `_vowelled_source.resolve_arabic_source`, so it serves the VOWELLED
copy while that copy is still the vowelling of the current OCR, and silently falls
back to the raw scan once it is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# A paragraph marker: parenthesised Arabic-Indic digits, at column 0, nothing else
# before them. See the module docstring for why the anchor is load-bearing.
_MARKER_RE = re.compile(r"^\(([٠-٩]+)\)")

_PAGE_RE = re.compile(r"^<!--\s*page\s+\d+\s*-->")

# A footnote reference as this scan writes them: 1-2 Arabic-Indic digits welded to
# the letter before them. They are apparatus, not the author's words, and they read
# as noise mid-sentence when the paragraph is shown to a reader.
#
# The letter is CAPTURED and put back rather than matched in a lookbehind, because
# the source is vowelled: in `الْعَالِمُ٢` the character immediately before the digit
# is a damma, not a letter, so a fixed-width lookbehind for a letter never fires and
# every reference survived. Any marks the letter carries are captured with it.
_FOOTNOTE_REF_RE = re.compile(r"([ؠ-ي][ً-ْٰ]*)[٠-٩]{1,2}")

# The one number the scan lost; its text lives in the block before it.
MERGED_INTO = {511: 510}


@dataclass(frozen=True)
class ArabicParagraph:
    number: int
    text: str
    merged: bool = False


def _to_int(arabic_digits: str) -> int:
    return int(arabic_digits.translate(_ARABIC_INDIC))


def source_path(book_dir: Path) -> Path | None:
    """The Arabic source to read, vowelled when that copy is current."""
    raw = Path(book_dir) / "_system" / "source" / "ocr" / "raw-extract.md"
    if not raw.exists():
        return None
    from _vowelled_source import resolve_arabic_source

    return resolve_arabic_source(raw)


def parse_blocks(text: str, *, strip_footnote_refs: bool = False) -> dict[int, ArabicParagraph]:
    """Map every paragraph number to its Arabic text.

    A block is its marker line plus every following line up to the next marker,
    with page markers dropped — they are scan furniture and 48 of the 95 in this
    book land mid-paragraph, so keeping them would cut sentences in half.
    """
    blocks: dict[int, ArabicParagraph] = {}
    current: int | None = None
    buf: list[str] = []

    def flush() -> None:
        if current is None:
            return
        body = "\n".join(buf).strip()
        if strip_footnote_refs:
            body = _FOOTNOTE_REF_RE.sub(r"\1", body)
        blocks[current] = ArabicParagraph(number=current, text=body)

    for line in (text or "").splitlines():
        if _PAGE_RE.match(line):
            continue
        m = _MARKER_RE.match(line)
        if m:
            flush()
            current = _to_int(m.group(1))
            buf = [line]
        elif current is not None:
            buf.append(line)
    flush()

    # The lost marker: point it at the block its text actually lives in, flagged.
    for missing, host in MERGED_INTO.items():
        if missing not in blocks and host in blocks:
            blocks[missing] = ArabicParagraph(number=missing, text=blocks[host].text, merged=True)
    return blocks


def load_blocks(book_dir: Path, *, strip_footnote_refs: bool = False) -> dict[int, ArabicParagraph]:
    """`parse_blocks` over the book's resolved Arabic source. Empty when absent."""
    path = source_path(book_dir)
    if path is None or not path.exists():
        return {}
    return parse_blocks(path.read_text(encoding="utf-8"), strip_footnote_refs=strip_footnote_refs)


def numbers_in_range(blocks: dict[int, ArabicParagraph], first: int, last: int) -> list[int]:
    """Every paragraph number present between two bounds, inclusive."""
    return sorted(n for n in blocks if first <= n <= last)


def join(blocks: dict[int, ArabicParagraph], numbers: list[int]) -> str:
    """The Arabic for a list of paragraph numbers, in reading order.

    A number that merged into an earlier block is emitted once, not twice — asking
    for both 510 and 511 must not print the same paragraph to the reader twice.
    """
    seen: set[str] = set()
    out: list[str] = []
    for n in sorted(set(numbers)):
        para = blocks.get(n)
        if para is None or para.text in seen:
            continue
        seen.add(para.text)
        out.append(para.text)
    return "\n\n".join(out)
