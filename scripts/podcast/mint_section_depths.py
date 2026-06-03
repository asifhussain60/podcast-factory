"""
mint_section_depths.py — keyword-based pipeline guess for section depth levels.

Scans a chapter .txt file for ## section headings, classifies each section's
depth level using a keyword heuristic, and writes the guesses to the
section_depths table in knowledge.db with source='pipeline'.

Human overrides (set via the Studio editor) take precedence — this function
only writes rows that don't already have a human override (source='human').

Usage (direct):
  python3 mint_section_depths.py <book_dir> <chapter_slug>

Usage (from build_episode_txt.py):
  from mint_section_depths import mint_section_depths_for_chapter
  mint_section_depths_for_chapter(book_dir, chapter_path)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Keyword heuristic — ordered high→low so the rarest/most-specific keywords
# take precedence. Match is case-insensitive.
# ---------------------------------------------------------------------------

_LEVEL_KEYWORDS: list[tuple[str, list[str]]] = [
    ("haqaiq", [
        "haqaiq", "realities", "essential reality", "eternal truth",
        "metaphysical truth", "permanent truth", "al-haqaiq", "ḥaqāʾiq",
    ]),
    ("mabda_maad", [
        "origin and return", "mabda", "ma'ad", "cosmic intellect",
        "emanation", "divine origin", "return to the divine",
        "origin & return", "mabda maad", "al-mabda",
    ]),
    ("mamsool", [
        "parable", "exemplar", "similitude", "analogy", "teaching story",
        "mamsool", "ممثولات", "allegorical story", "instructive example",
    ]),
    ("taveel", [
        "esoteric", "ta'wil", "taveel", "inner meaning", "batin",
        "allegorical", "hidden meaning", "tawil", "taʾwīl",
        "spiritual interpretation", "inner dimension",
    ]),
    ("advanced", [
        "jurisprudence", "fiqh", "legal reasoning", "scholarly commentary",
        "exegesis", "advanced", "formal analysis", "doctrinal analysis",
        "theological argument",
    ]),
    ("general", [
        "history", "context", "background", "introduction", "overview",
        "narrative", "story", "biography", "chronology", "events",
    ]),
]

_SECTION_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)


def _classify_section(heading: str, body: str, book_level: str | None) -> str:
    """Return the depth level code for a section.

    Looks at the heading + first 300 words of body for keyword matches.
    Falls back to *book_level* (from meta.yml) if available, else 'general'.
    """
    search_text = (heading + " " + body[:1500]).lower()
    for level, keywords in _LEVEL_KEYWORDS:
        for kw in keywords:
            if kw in search_text:
                return level
    # Fall back to the book's declared content_level, then 'general'.
    return book_level or "general"


def _read_book_level(book_dir: Path) -> str | None:
    """Read content_level from book_dir/_system/meta.yml (or meta.yml)."""
    for candidate in [book_dir / "_system" / "meta.yml", book_dir / "meta.yml"]:
        if candidate.exists():
            try:
                data = yaml.safe_load(candidate.read_text()) or {}
                return data.get("content_level")
            except Exception:
                pass
    return None


def _get_db():
    """Open knowledge.db in write mode (deferred import to avoid import-time errors)."""
    import sqlite3
    db_path = Path(__file__).parent.parent.parent / "content" / "knowledge-base" / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def mint_section_depths_for_chapter(
    book_dir: Path,
    chapter_path: Path,
    *,
    overwrite_human: bool = False,
    log=None,
) -> list[dict]:
    """Parse *chapter_path* for ## sections, classify each, write to DB.

    Only inserts rows. Human overrides (source='human') are never overwritten
    unless *overwrite_human=True*. Returns the list of rows written.

    Parameters
    ----------
    book_dir : Path
        Book root directory (used to read meta.yml for the fallback level).
    chapter_path : Path
        Path to the chapter .txt file.
    overwrite_human : bool
        If True, also overwrite existing human-sourced depth rows. Default False.
    log : callable | None
        Optional logging function (print-compatible).
    """
    if log is None:
        log = lambda *a: None  # noqa: E731

    book_slug = book_dir.name
    chapter_id = chapter_path.stem  # e.g. "ch01-the-opening"

    text = chapter_path.read_text(encoding="utf-8")
    headings = list(_SECTION_RE.finditer(text))
    if not headings:
        log(f"  mint_section_depths · no ## sections found in {chapter_path.name}")
        return []

    book_level = _read_book_level(book_dir)

    # Extract section bodies (text between this heading and the next).
    sections: list[tuple[int, str, str]] = []  # (ordinal, heading_text, body_text)
    for ord_idx, m in enumerate(headings):
        heading_text = m.group(1).strip()
        body_start = m.end()
        body_end = headings[ord_idx + 1].start() if ord_idx + 1 < len(headings) else len(text)
        body_text = text[body_start:body_end]
        sections.append((ord_idx, heading_text, body_text))

    conn = _get_db()
    cur = conn.cursor()
    written: list[dict] = []

    for ordinal, heading_text, body_text in sections:
        # Check for existing human override.
        cur.execute(
            "SELECT source FROM section_depths WHERE book_slug=? AND chapter_id=? AND section_ordinal=?",
            (book_slug, chapter_id, ordinal),
        )
        row = cur.fetchone()
        if row and row["source"] == "human" and not overwrite_human:
            log(f"  mint_section_depths · section {ordinal} has human override — skipping")
            continue

        depth = _classify_section(heading_text, body_text, book_level)
        slug = heading_text[:60].lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')

        cur.execute(
            """
            INSERT INTO section_depths (book_slug, chapter_id, section_ordinal, section_slug, depth_level, source)
            VALUES (?, ?, ?, ?, ?, 'pipeline')
            ON CONFLICT(book_slug, chapter_id, section_ordinal)
            DO UPDATE SET section_slug=excluded.section_slug,
                          depth_level=excluded.depth_level,
                          source='pipeline',
                          updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
            """,
            (book_slug, chapter_id, ordinal, slug, depth),
        )
        log(f"  mint_section_depths · section {ordinal} '{heading_text[:40]}' → {depth}")
        written.append({"ordinal": ordinal, "slug": slug, "depth_level": depth, "source": "pipeline"})

    conn.commit()
    conn.close()
    return written


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    if len(sys.argv) < 3:
        print("Usage: mint_section_depths.py <book_dir> <chapter_slug>")
        print("  Example: mint_section_depths.py content/drafts/books/ayyuhal-walad ch01-frame-and-the-problem-of-knowledge")
        sys.exit(1)

    book_dir = Path(sys.argv[1]).resolve()
    chapter_slug = sys.argv[2]

    # Accept slug with or without leading ch##- prefix.
    chapters_dir = book_dir / "chapters"
    matches = list(chapters_dir.glob(f"*{chapter_slug}*.txt"))
    if not matches:
        print(f"ERROR: no chapter file matching '{chapter_slug}' in {chapters_dir}")
        sys.exit(1)
    chapter_path = matches[0]

    written = mint_section_depths_for_chapter(book_dir, chapter_path, log=print)
    print(f"\n  {len(written)} section depth(s) written for {chapter_path.name}")


if __name__ == "__main__":
    _main()
