"""Which slide decks a book has, and what each one is called.

Split out of `_listener_book.py` on 2026-08-04 when the per-chapter deck work
pushed that module past the DR-005 line limit. This is the seam that was already
there: everything else in that file answers "which recording, which chapter, what
counts as a blurb", and this answers a question with its own vocabulary — decks,
pages, and the folder they were rasterised into.

WHAT CHANGED, AND WHY IT NEEDED ITS OWN NAMES

The Listener assumed one deck per book, because the only book that had any had
one. The pipeline's default is per-chapter and always was
(`_content_profile.slide_deck_mode`; `book` is the override), and it already
rasterises into `slide-decks/_pages/ch01/`, `_pages/ch02/` … So a book like
Ayyuha al-Walad, with four chapter decks, had none of them found.

The deck id lives in the R2 KEY and has to: `media_asset.key` is the primary key,
so four decks each offering a `page-01.jpg` collapsed onto one row and three
decks' worth of pages disappeared on insert without anything saying so.
"""

from __future__ import annotations

from pathlib import Path

# Where the rasterised pages land, one directory per deck. Written by
# `inject_slide_deck.extract_pages` / `_slide_import` via pdftoppm.
PAGES_DIR = "_pages"
DECKS_DIR = "slide-decks"

# The deck that belongs to no single chapter. Not a special case in the data — it
# is simply the deck a book-wide export produces — but it needs no name, because
# a book with one deck never draws a chooser to name it in.
BOOK_DECK = "book"


def deck_dirs(directory: Path) -> list[Path]:
    """Every deck folder under `slide-decks/_pages/`, in a stable order."""
    root = directory / DECKS_DIR / PAGES_DIR
    return sorted(p for p in root.glob("*") if p.is_dir())


def deck_pages(deck_dir: Path) -> list[Path]:
    """The pages of one deck, in page order.

    pdftoppm zero-pads to the digit count of the last page, so lexical order is
    page order for any deck of fewer than a hundred pages — which is every deck
    this pipeline has produced.
    """
    return sorted(deck_dir.glob("page-*.jpg"))


def deck_title(directory: Path, deck_id: str) -> str | None:
    """What the author called this deck, or None.

    Read from the deck SOURCE's own first heading — `slide-decks/ch01-deck-*.txt`
    opens with the H1 that names it. That file is the thing the author wrote and
    exported the PDF from, so its heading is the deck's real name rather than a
    label reconstructed from a folder called `ch01`.

    Deliberately NOT taken from the reading edition's chapter of the same number.
    Deck folders are numbered against the PODCAST chapter set
    (`chapters/ch01-*.txt`), which for several books is a different segmentation
    from `book.md` — Ayyuha al-Walad has four of one and ten of the other.
    Matching them by ordinal would file every deck under a confidently wrong
    chapter, which is the same guess `read_bridge` refuses to make about
    episodes.

    None when there is no deck source, which is an ordinary state: the chooser
    then falls back to the folder name, and a single-deck book never draws one.
    """
    for source in sorted((directory / DECKS_DIR).glob(f"{deck_id}-deck-*.txt")):
        for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip() or None
            # Only the OPENING heading counts. A deck whose first line is prose
            # has no authored name, and the first `# ` further down belongs to a
            # slide rather than to the deck.
            if line.strip():
                return None
    return None
