"""The source a chapter was made from, made ready for the moderators' Source pane.

Two kinds of text, kept apart because the difference matters to whoever judges a correction:

  * ``scan``      the OCR of the scanned pages (`_system/source/ocr/raw-extract.md`) — the
                  original letters, and possibly an OCR error;
  * ``extracted`` the pipeline's own English extraction (`_system/source/text/refined-english.md`)
                  — already an interpretation.

BOTH are cut on the ``<!-- page N -->`` markers each file carries, and a chapter is paired to its
pages through ``book/source-crosswalk.json`` by TITLE (``anchor_key``), never by index: every book
gets a pipeline-written introduction that shifts positions by one, so a positional pairing silently
hands chapter 1's pages to chapter 2. The same reason ``_listener_source_ref`` gives.

READ BY MODERATORS AND ADMINS ONLY, in the Library. ``_listener_source_ref`` deliberately keeps the
verbatim source off the reader-facing table because it is copyrighted prose; this module feeds a
DIFFERENT pair of tables (``source_page``, ``source_span``) that the Worker returns only to a
moderator and, for anyone else, without querying at all. Never merge the two.

A book with neither file simply has no rows, which is what makes the pane say so instead of
showing an empty box.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key  # noqa: E402

_PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s*-->")
# The scanning app's own stamp on every page — not the book's text.
_WATERMARKS = ("Scanned with CamScanner",)

# The share of a scan's non-blank lines that are fragments rather than words.
_NOISY_AT = 0.08
_UNRELIABLE_AT = 0.25
_LETTERS = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


@dataclass
class SourcePageRow:
    kind: str  # "scan" | "extracted"
    page: int
    text: str


@dataclass
class SourceSpanRow:
    anchor: str
    kind: str
    first_page: int
    last_page: int
    quality: str  # "clean" | "noisy" | "unreliable"


def _split_pages(text: str) -> dict[int, str]:
    """`<!-- page N -->` blocks, keyed by page number, watermark lines removed."""
    parts = _PAGE_MARK.split(text)
    pages: dict[int, str] = {}
    # parts = [preamble, "1", body1, "2", body2, ...]
    for number, body in zip(parts[1::2], parts[2::2]):
        lines = [
            line.rstrip() for line in body.splitlines() if line.strip() and not any(w in line for w in _WATERMARKS)
        ]
        cleaned = "\n".join(lines).strip()
        if cleaned:
            pages[int(number)] = cleaned
    return pages


def read_source_pages(book_dir: Path) -> list[SourcePageRow]:
    """Every page of the scan and of the extracted text, when those files exist."""
    book_dir = Path(book_dir)
    rows: list[SourcePageRow] = []
    for kind, relative in (
        ("scan", "_system/source/ocr/raw-extract.md"),
        ("extracted", "_system/source/text/refined-english.md"),
    ):
        path = book_dir / relative
        if not path.exists():
            continue
        rows += [
            SourcePageRow(kind=kind, page=page, text=text)
            for page, text in sorted(_split_pages(path.read_text(encoding="utf-8")).items())
        ]
    return rows


def scan_quality(texts: list[str]) -> str:
    """How far to trust a run of OCR: clean, noisy or unreliable.

    A heuristic and an honest one: a fragment line (no run of three letters, or a replacement
    character) is what a failed recognition looks like, and the share of them is the signal. A
    per-book override in `_system/source/ocr/quality.json` (`{"quality": "unreliable"}`) wins, for
    the case a person knows better — a handwritten scan that happens to produce plausible letters.
    """
    lines = [line for text in texts for line in text.splitlines() if line.strip()]
    if not lines:
        return "clean"
    fragments = sum(1 for line in lines if "�" in line or not _LETTERS.search(line))
    share = fragments / len(lines)
    if share >= _UNRELIABLE_AT:
        return "unreliable"
    return "noisy" if share >= _NOISY_AT else "clean"


def _override(book_dir: Path) -> str | None:
    path = Path(book_dir) / "_system/source/ocr/quality.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("quality")
    except (json.JSONDecodeError, AttributeError):
        return None
    return value if value in ("clean", "noisy", "unreliable") else None


def read_source_spans(book_dir: Path, chapters: list, pages: list[SourcePageRow]) -> list[SourceSpanRow]:
    """Which pages belong to which chapter, paired by TITLE through the crosswalk.

    A chapter with no crosswalk entry, or none of whose pages exist in the file, gets no row for
    that kind — never a guess at a range.
    """
    path = Path(book_dir) / "book" / "source-crosswalk.json"
    if not path.exists() or not pages:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    by_kind: dict[str, dict[int, str]] = {}
    for row in pages:
        by_kind.setdefault(row.kind, {})[row.page] = row.text

    known = {c.anchor for c in chapters}
    forced = _override(book_dir)
    entries = data.get("chapters", []) if isinstance(data, dict) else data

    spans: list[SourceSpanRow] = []
    for entry in entries:
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        anchor = anchor_key(title)
        if anchor not in known:
            continue

        for kind, field in (("scan", "arabic_source_pages"), ("extracted", "source_pages")):
            have = by_kind.get(kind, {})
            wanted = [p for p in (entry.get(field) or entry.get("source_pages") or []) if p in have]
            if not wanted:
                continue
            quality = "clean"
            if kind == "scan":
                quality = forced or scan_quality([have[p] for p in wanted])
            spans.append(
                SourceSpanRow(anchor=anchor, kind=kind, first_page=min(wanted), last_page=max(wanted), quality=quality)
            )
    return spans


def source_statements(book, sql_str) -> list[str]:
    """The statements that (re)write a book's source text, cleared and rewritten like the rest.

    One row per PAGE, because D1 rejects a statement past ~100KB and a scanned chapter runs long; a
    page is always small. Nothing here names a privilege bit: the Worker decides who may read these
    rows, and returns nothing for anyone but a moderator without querying them at all.
    `sql_str` is the publisher's own quoting, passed in so there is one rule and no import cycle.
    """
    slug = sql_str(book.slug)
    out = [f"DELETE FROM source_page WHERE slug = {slug};", f"DELETE FROM source_span WHERE slug = {slug};"]
    for page in book.source_pages:
        out.append(
            "INSERT INTO source_page (slug, kind, page, text) VALUES "
            f"({slug}, {sql_str(page.kind)}, {page.page}, {sql_str(page.text)});"
        )
    for span in book.source_spans:
        out.append(
            "INSERT INTO source_span (slug, anchor_key, kind, first_page, last_page, quality) VALUES "
            f"({slug}, {sql_str(span.anchor)}, {sql_str(span.kind)}, "
            f"{span.first_page}, {span.last_page}, {sql_str(span.quality)});"
        )
    return out
