"""Where a correction's quote sits in a book -- the shared text layer for the
repo side of the corrections workflow.

Four scripts need the same answer to "where in this chapter is that quote?":
`build_correction_packets`, `review_corrections`, `pull_corrections` and
`import_correction_suggestions`. Four answers would be free to disagree, and a
disagreement here is the silent kind -- a correction applied to the wrong
sentence of a religious text, or a suggestion imported with an anchor the reader
cannot find. So there is one implementation, here.

TWO VIEWS OF THE SAME CHAPTER, and the difference is the whole design:

  reader view   the chapter as a reader sees it -- markdown syntax stripped,
                whitespace collapsed, split into blocks. This is what a
                moderator's selection is made against, so this is what a stored
                `block_index` / `start_offset` / `quote` refer to. It is only
                ever READ from.
  source view   the markdown text itself. This is what an accepted correction is
                spliced into. A quote that matches in the reader view but not
                here spans formatting (a word inside `**bold**`), and splicing
                plain text into the middle of markup would corrupt it -- so
                such a correction is reported, never guessed.

Blocks are numbered the way `_narration_plan.chapter_blocks` numbers them
(split on blank lines after HTML comments are removed), because that is the
repo's existing statement of which rendered block a paragraph is; the read-along
cues are already keyed on it. `listener/app/lib/anchor.ts` treats the stored
index as a hint and falls back to searching by quote, so an off-by-one for a
list or a quotation (the renderer folds those into a single block) degrades to a
slower resolve, never to a wrong one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from _listener_book import split_chapters

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

#: How much preceding text an anchor keeps. Mirrors `PREFIX_LENGTH` in
#: listener/app/lib/anchor.ts.
PREFIX_LENGTH = 48


def flatten(text: str) -> str:
    """Collapse whitespace runs, keeping offsets meaningful (no trim)."""
    return re.sub(r"\s+", " ", text)


def normalize_text(text: str) -> str:
    """Mirror of `normalizeText` in anchor.ts: collapse whitespace and trim."""
    return flatten(text).strip()


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookChapter:
    key: str  # _book_edits.anchor_key of the heading -- the Composer's identity
    heading: str  # the `## ` line's text, exactly what write_chapter_body wants
    number: int | None  # the printed "3." in "## 3. Title", None for an introduction
    body: str


_NUMBER_RE = re.compile(r"^\s*([0-9]+)\.")


def read_chapters(book_dir: Path) -> list[BookChapter]:
    """Every `## ` chapter of the reading edition, in order.

    Reuses `_listener_book.split_chapters` -- the publisher's own splitter -- so
    a chapter here is exactly a chapter the Library holds.
    """
    book_md = Path(book_dir) / "book" / "book.md"
    if not book_md.exists():
        return []
    out: list[BookChapter] = []
    for ch in split_chapters(book_md.read_text(encoding="utf-8")):
        m = _NUMBER_RE.match(ch.title)
        out.append(
            BookChapter(
                key=ch.anchor,
                heading=ch.title,
                number=int(m.group(1)) if m else None,
                body=ch.markdown,
            )
        )
    return out


def find_chapter(chapters: list[BookChapter], key: str) -> BookChapter | None:
    """The chapter whose key is `key`. First wins if a book repeats a heading."""
    for ch in chapters:
        if ch.key == key:
            return ch
    return None


def duplicate_keys(chapters: list[BookChapter]) -> set[str]:
    seen: set[str] = set()
    dup: set[str] = set()
    for ch in chapters:
        (dup if ch.key in seen else seen).add(ch.key)
    return dup


# ---------------------------------------------------------------------------
# Reader view
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HEADING_MARK_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
_QUOTE_MARK_RE = re.compile(r"(?m)^\s{0,3}>\s?")
_LIST_MARK_RE = re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+")
_EMPH_RE = re.compile(r"\*+")
_UNDERSCORE_EMPH_RE = re.compile(r"(?<![\w])_+|_+(?![\w])")


def plain_text(markdown: str) -> str:
    """What a reader sees of a block of markdown: syntax stripped, whitespace collapsed.

    Deliberately small. It handles the constructs `renderMarkdown` turns into
    markup around text this book actually contains (emphasis, links, headings,
    quotations, list bullets, inline code); anything else is left as typed, which
    can only make a quote FAIL to match -- reported -- never match wrongly.
    """
    text = _LINK_RE.sub(r"\1", markdown)
    text = _HEADING_MARK_RE.sub("", text)
    text = _QUOTE_MARK_RE.sub("", text)
    text = _LIST_MARK_RE.sub("", text)
    text = text.replace("`", "")
    text = _EMPH_RE.sub("", text)
    text = _UNDERSCORE_EMPH_RE.sub("", text)
    return flatten(text).strip()


def split_blocks(body: str) -> list[str]:
    """The chapter's markdown blocks, numbered as `_narration_plan.chapter_blocks` numbers them."""
    stripped = _HTML_COMMENT.sub("", body).strip()
    if not stripped:
        return []
    return re.split(r"\n\s*\n", stripped)


def block_texts(body: str) -> list[str]:
    """Reader-view text of every block, index-aligned with `split_blocks`."""
    return [plain_text(b) for b in split_blocks(body)]


@dataclass(frozen=True)
class Hit:
    block_index: int
    start: int
    end: int  # exclusive; offsets are into the block's reader-view text


def _occurrences(hay: str, needle: str) -> list[int]:
    out: list[int] = []
    if not needle:
        return out
    i = hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def locate_reader(body: str, quote: str) -> list[Hit]:
    """Every place `quote` occurs in the reader view of `body` (overlaps counted).

    An EXACT match after whitespace normalisation, which is the only comparison
    `resolveAnchor` allows itself. Callers demand exactly one hit.
    """
    needle = normalize_text(quote)
    hits: list[Hit] = []
    for idx, text in enumerate(block_texts(body)):
        for off in _occurrences(text, needle):
            hits.append(Hit(idx, off, off + len(needle)))
    return hits


def prefix_before(block_text: str, start: int) -> str:
    """Up to `PREFIX_LENGTH` characters before `start`, as anchor.ts stores it."""
    return block_text[max(0, start - PREFIX_LENGTH) : start]


# ---------------------------------------------------------------------------
# Source view
# ---------------------------------------------------------------------------


def _flexible(quote: str) -> re.Pattern[str]:
    tokens = normalize_text(quote).split(" ")
    return re.compile(r"\s+".join(re.escape(t) for t in tokens if t))


def locate_source(body: str, quote: str) -> list[tuple[int, int]]:
    """Every (start, end) of `quote` in the MARKDOWN text of `body`.

    Whitespace-flexible, because the reader collapsed the runs the source keeps
    (a wrapped line). A match that crosses a blank line is a selection spanning
    two paragraphs, which the reader cannot produce -- dropped, so it reads as
    "not found" rather than being spliced across a paragraph break.
    """
    if not normalize_text(quote):
        return []
    pattern = _flexible(quote)
    return [(m.start(), m.end()) for m in pattern.finditer(body) if not re.search(r"\n\s*\n", m.group(0))]


def block_span(body: str, start: int, end: int) -> tuple[int, int]:
    """The (start, end) of the blank-line-delimited paragraph of `body` holding [start, end)."""
    lo = body.rfind("\n\n", 0, start)
    lo = 0 if lo == -1 else lo + 2
    hi = body.find("\n\n", end)
    hi = len(body) if hi == -1 else hi
    return lo, hi


def paragraph_of(body: str, start: int, end: int) -> str:
    lo, hi = block_span(body, start, end)
    return body[lo:hi]


def substitute(body: str, spans_and_texts: list[tuple[int, int, str]]) -> str:
    """Apply several (start, end, replacement) edits to `body`, last position first.

    Working backwards is what keeps every earlier offset valid; the caller has
    already refused overlaps, so no edit can land inside another's replacement.
    """
    out = body
    for start, end, text in sorted(spans_and_texts, key=lambda t: t[0], reverse=True):
        out = out[:start] + text + out[end:]
    return out


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]
