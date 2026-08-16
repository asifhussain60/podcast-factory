"""Source-reference data — the pipeline's crosswalk, made ready for the reader.

`book/source-crosswalk.json` is built by the translation-edition print step
(`_translation_text.build_source_crosswalk`) to typeset a "Source Crosswalk"
appendix in the printed PDF. It is read here for a second, independent use: a
reader-facing "Source: pp. X-Y — Heading" line in the Podcast Factory Library,
shown only when the reader opts in via a toolbar toggle.

Only two fields travel from the crosswalk into the Listener: the page range
and the source headings. The excerpt (verbatim original-book text) and
`drift_findings` (internal QA notes) are deliberately left on disk — the
excerpt because it is copyrighted source prose no reader-facing surface
should reproduce, the findings because they are not written for a reader.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key  # noqa: E402


@dataclass
class SourceReference:
    """One chapter's source-crosswalk summary, ready to publish."""

    anchor: str
    page_range: str
    headings: list[str]


def read_source_references(book_dir: Path, chapters: list) -> list[SourceReference]:
    """The crosswalk's page range + headings, paired to chapters by TITLE.

    Not by `index`: the crosswalk is built from the SOURCE book's own chapter
    numbering (`book-toc.json`'s `bk_index`), and `book.md` can carry chapters
    the source never had — every book gets an "Introduction to the Book"
    chapter the pipeline writes on its own (see `b78c4e86`), which shifts
    every later chapter's position by one. A positional pairing silently
    attaches chapter 1's page range to chapter 2, and so on down the book.

    Matched the same way `read_bridge` above pairs an episode to a chapter:
    `anchor_key(entry["title"])` against `Chapter.anchor`, both already
    stripped of leading numbers and punctuation by that one function, so an
    added chapter shifts positions without breaking a single pairing.

    A book with no crosswalk file returns an empty list, which is what keeps
    the toggle off the toolbar entirely on those books rather than showing a
    dead control.
    """
    path = book_dir / "book" / "source-crosswalk.json"
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    known = {c.anchor for c in chapters}

    references: list[SourceReference] = []
    for entry in data.get("chapters", []):
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        anchor = anchor_key(title)
        if anchor not in known:
            continue

        page_range = str(entry.get("source_page_range") or "").strip()
        headings = [
            heading.strip()
            for heading in (entry.get("source_headings") or [])
            if isinstance(heading, str) and heading.strip()
        ]
        if not page_range and not headings:
            continue

        references.append(SourceReference(anchor=anchor, page_range=page_range, headings=headings))

    return references
