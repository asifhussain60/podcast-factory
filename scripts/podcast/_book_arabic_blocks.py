"""_book_arabic_blocks.py — one shape for every Arabic display quotation.

THE RULE (Asif, 2026-08-05): an Arabic display quotation and the English
rendering under it are one thing on the page — Arabic centred, in maroon, at
display size, and the translation centred beneath it. "This should be the
standard for the entire book."

The site already knows how to draw that. `markdown.ts` gives a blockquote whose
paragraphs it can tell apart `<p class="ar">` and `<p class="tr">`, and both the
Composer and the print stylesheet centre the pair and set the Arabic in maroon.
What the book did not have was the shape. Two gaps, both measured on
`ayyuhal-walad`:

  THE STRAY PARAGRAPHS  57 of its 67 Arabic display lines were `>` blockquotes
      and 10 were bare paragraphs wrapped in ASCII brackets — every one of them
      in chapter 1. A bare paragraph is styled by `.ar-block`, which centres it
      but sets no colour, and the Composer's EDIT canvas drops that class
      entirely (its allow-list carries `quran`, `ar`, `tr` and nothing else). So
      one chapter's quotations printed black, and in the editor they printed as
      running prose.

  THE ORPHANED TRANSLATIONS  even where the blockquote was right, the English
      under it was a separate paragraph — outside the quotation, left-aligned,
      never `.tr`. That is the half of the rule no chapter had.

So this pass does two things and nothing else: it promotes a standalone Arabic
paragraph to a blockquote line, and it pulls the translation that follows into
the same blockquote.

WHAT COUNTS AS THE TRANSLATION is deliberately narrow — the paragraph
immediately after, wholly enclosed in double quotes. That is how this corpus
sets a rendering, and the alternative (any following English paragraph) would
swallow the author's next sentence into the quotation, which is a fidelity
error, not a formatting one. Anything else is left where it is.

Deterministic, no model, no cost, idempotent: after a run the paragraph is a
blockquote line, so nothing matches it again.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_mirror import ARABIC_LETTER_RE, is_arabic_block

#: A rendering, as this corpus sets one: the whole paragraph inside one pair of
#: double quotes, optionally followed by a bracketed citation and nothing else.
#: Curly quotes included — the compose emits both.
#:
#: The citation clause is not cosmetic. Eleven of this book's verses are set
#: `"…that for which he strives." (Quran, an-Najm: 38)`, and without it they read
#: as prose and their renderings stayed outside the quotation.
#:
#: Nothing may follow. `"…seek forgiveness." (al-Dhariyat: 18) In this there is a
#: sign…` continues into the author's own commentary, and pulling that into the
#: quotation would attribute his words to scripture — a fidelity error dressed as
#: a formatting one.
_RENDERING = re.compile(r'^\s*["“][^"”]+["”][.,;:!?]?\s*(?:\([^()]*\))?\s*$')

_PARENS = "()（）"

#: Below this a line is a stray word, not a quotation somebody set apart.
_MIN_LETTERS = 8


def _is_display_quotation(text: str) -> bool:
    """A line that is nothing but Arabic — this pass's own, narrower question.

    `is_arabic_block` answers "must the paragraph merge treat this as a display
    block?" and needs 20+ letters because it tolerates Latin alongside them. Two
    of this book's Qur'anic verses have exactly 20 and fell through: `إِلَّا مَن تَابَ
    وَآمَنَ وَعَمِلَ صَلِحًۭا` is unmistakably a display quotation and unmistakably short.

    Lowering the mirror's threshold was the wrong fix — it is pinned across three
    languages and governs the merge, the PDF and the reader for every book. This
    asks a stricter question instead (NO Latin at all, not merely less of it),
    which is what makes a lower length bound safe.
    """
    # The mirror's OWN letter class, imported rather than respelled: this
    # function differs from `is_arabic_block` in its bounds, and it must not
    # also differ in what it thinks an Arabic letter is.
    letters = len(ARABIC_LETTER_RE.findall(text))
    return letters >= _MIN_LETTERS and not re.search(r"[A-Za-z]", text)


def _is_quotation(text: str) -> bool:
    return is_arabic_block(text) or _is_display_quotation(text)


def _unwrap(text: str) -> str:
    """Drop the ASCII brackets a bare Arabic paragraph was written inside.

    A blockquote does not use them — 57 of this book's quotations prove the house
    style — and left in place they are read as English punctuation by the bidi
    algorithm and stranded at the wrong end of the line.
    """
    s = text.strip()
    while len(s) > 1 and s[0] in _PARENS and s[-1] in _PARENS:
        s = s[1:-1].strip()
    return s


def normalize_arabic_blocks(body: str) -> tuple[str, dict[str, int]]:
    """Return the body with every Arabic display quotation in blockquote form,
    its translation inside it, plus a count of each change."""
    lines = body.split("\n")
    out: list[str] = []
    stats = {"promoted": 0, "translations_joined": 0}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # A quotation already in blockquote form, or a bare paragraph that is one.
        is_quote_line = stripped.startswith(">") and _is_quotation(stripped.lstrip("> ").strip())
        is_bare_arabic = (
            bool(stripped) and not stripped.startswith((">", "#", "<", "|", "`")) and _is_quotation(_unwrap(stripped))
        )
        if not (is_quote_line or is_bare_arabic):
            out.append(line)
            i += 1
            continue
        if is_bare_arabic:
            out.append("> " + _unwrap(stripped))
            stats["promoted"] += 1
        else:
            out.append(line)
        # Pull in the rendering: one blank line, then a wholly-quoted paragraph.
        if i + 2 < len(lines) and not lines[i + 1].strip() and _RENDERING.match(lines[i + 2]):
            out.append(">")
            out.append("> " + lines[i + 2].strip())
            stats["translations_joined"] += 1
            i += 3
            continue
        i += 1
    return "\n".join(out), stats


def apply_arabic_blocks(book_dir: Path, *, log=lambda _m: None) -> dict[str, int]:
    """Run the pass over ``book/book.md``. Returns the change counts."""
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"promoted": 0, "translations_joined": 0}
    before = book_md.read_text(encoding="utf-8")
    after, stats = normalize_arabic_blocks(before)
    (book_dir / "_system" / "book-arabic-blocks.json").write_text(
        json.dumps({"schema": "book.arabic-blocks/v1", **stats}, indent=2) + "\n", encoding="utf-8"
    )
    if after != before:
        tmp = book_md.with_suffix(".md.tmp")
        tmp.write_text(after, encoding="utf-8")
        tmp.replace(book_md)
    log(
        f"arabic-blocks: {stats['promoted']} standalone quotation(s) promoted, "
        f"{stats['translations_joined']} rendering(s) joined to their quotation"
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--book-dir")
    args = ap.parse_args()
    if args.book_dir:
        book_dir = Path(args.book_dir)
    elif args.slug:
        from _paths import resolve_content

        book_dir = resolve_content(args.slug)
    else:
        ap.error("either <slug> or --book-dir is required")
    apply_arabic_blocks(book_dir, log=print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
