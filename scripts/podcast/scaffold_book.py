#!/usr/bin/env python3
"""scaffold_book.py — create the canonical BOOK_DIR layout for a new podcasted source.

Authoritative shape: content/podcast/.skill/handbook/book-dir-layout.md. This
script writes that shape in one shot for a new <category>/<book-slug>/ and
appends a one-line index row to content/podcast/.skill/books.md.

Usage:
    python3 scripts/podcast/scaffold_book.py <category> <book-slug> "<Book Title>" \\
        [--author "<Author Name>"] [--force]

Categories (must match library/<category>/): books, articles, documents, lectures, interviews, letters.

Behavior:
- Refuses to overwrite a non-empty BOOK_DIR unless --force is given.
- Creates: chapters/, chapter-contracts/, episodes/, transcripts/, _system/{,
  scratchpad/, source/, source/text/, episode-drafts/}.
- Writes empty stub files in _system/: registry.md, pronunciation.md,
  mangle-map.md, meta-prose-tells.md, enrichment-whitelist.md, enrichment-log.md.
- Writes a starter _README.md and transcripts/_README.md.
- Appends a one-line row to content/podcast/.skill/books.md (idempotent — does
  nothing if the row already exists).

Determinism:
- Same args → same files. Pre-existing user-edited content is preserved unless
  --force.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = REPO_ROOT / "content" / "podcast" / "library"
BOOKS_INDEX = REPO_ROOT / "content" / "podcast" / ".skill" / "books.md"

ALLOWED_CATEGORIES = {"books", "articles", "documents", "lectures", "interviews", "letters"}

# ─── stub bodies ──────────────────────────────────────────────────────────────

README_TEMPLATE = """# Podcast — {title}

**Source:** *{title}*{author_clause}.

**Slug:** `{book_slug}` · **Category:** `{category}` · **Architecture:** v3.5 (chapter-as-source; phonetics in customize prompt only).

## Folder layout

Per `content/podcast/.skill/handbook/book-dir-layout.md`. The full tree is documented there — this README is the book-specific blurb only.

## Upload checklist (per episode)

1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the **single source**.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's **Customize prompt** box.
3. Click *Generate*.
4. After audio renders: transcribe via Azure Speech-to-Text (`scripts/podcast/transcribe_episode.py`) or any external service, drop the transcript at `transcripts/EP##-<slug>.transcript.txt`, then run `audit_transcript.py <BOOK_DIR> EP##-<slug>`.
"""

TRANSCRIPTS_README_TEMPLATE = """# Transcripts

Slug-aligned transcripts for *{title}*. One file per episode, named `EP##-<slug>.transcript.txt` to match `chapters/ch##-<slug>.txt` and `episodes/EP##-<slug>.txt` exactly.

## Provenance

NotebookLM renders the Audio Overview from the chapter + customize prompt. The audio is transcribed by `scripts/podcast/transcribe_episode.py` (Azure Speech-to-Text Fast Transcription API) — or, optionally, by any external service — and the result lands here renamed to the slug-aligned form. `transcribe_episode.py` writes here; the rest of the pipeline only reads.

## Consumers

- `scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>` — empirical drift audit; appends findings to `_learning/findings.jsonl`
- `podcast-challenger` Loop M — empirical-transcript audit
"""

REGISTRY_TEMPLATE = """# Podcast Episode Registry — {title}

{author_line}
Architecture: v3.5 (chapter-as-source; phonetics in customize prompt only).

| EP# | Title | Slug | Source Type | Status | Date Started | NotebookLM URL |
|-----|-------|------|-------------|--------|--------------|----------------|
"""

PRONUNCIATION_TEMPLATE = """# Pronunciation — {title} (book-specific overrides)

Per-book phonetic overrides. Read by `build_episode_txt.py` (via `_rules`) and
`podcast-challenger`. **May ADD terms; MUST NOT contradict** the shared manifest
at `content/_shared/arabic/03-arabic-english-manifest.md`.

Format: pipe table.

| Term | Phonetic | Notes |
|---|---|---|
"""

MANGLE_MAP_TEMPLATE = """# Name Mangling Map — {title} (book-specific)

Loaded by `scripts/podcast/audit_transcript.py` via `load_book_mangle_map(BOOK_DIR)`
and merged into the global `NAME_MANGLING_MAP`. Holds **book-specific** mangled
forms (e.g. the book's own title, the specific narrators or characters in this
book). Generic Arabic / Islamic vocabulary lives in the global map.

Format: pipe table; mangled forms comma-separated.

| Canonical | Mangled forms (comma-separated) |
|---|---|
"""

META_PROSE_TELLS_TEMPLATE = """# Meta-Prose Tells — {title} (book-specific)

Loaded by `scripts/podcast/build_episode_txt.py` via `load_book_meta_prose_tells(BOOK_DIR)`
and appended to the global `META_PROSE_TELLS` list. Holds **author-specific**
self-describing prose phrases (e.g. `"anything <author> only implies"`,
`"<author>'s prose has been clarified"`).

Format: one tell per line, prefixed with `- `. Match is case-insensitive substring.

## Tells

"""

ENRICHMENT_WHITELIST_TEMPLATE = """# Enrichment Whitelist — {title} (Tier 1, book-specific)

Per `content/podcast/.skill/handbook/enrichment-sources.md` §1, Tier 1 is the
**author's own corpus**, scoped per book. Enumerate {author_short}'s corpus here;
citations from these works are highest-priority enrichment for any chapter in
this book.

## Works (Tier 1 for this book)

{author_corpus_placeholder}

## Citation format (Tier 1 for this book)

| Work | Format |
|---|---|
"""

ENRICHMENT_LOG_TEMPLATE = """# Enrichment Log — {title}

Per-chapter enrichment status and provenance. Updated as Phase 0e completes for
each chapter.

| Chapter | Status | Outside-source % | Notes | Date |
|---|---|---|---|---|
"""

# ─── core ─────────────────────────────────────────────────────────────────────


def book_dir_for(category: str, book_slug: str) -> Path:
    return LIBRARY_DIR / category / book_slug


def is_non_empty(p: Path) -> bool:
    return p.exists() and p.is_dir() and any(p.iterdir())


def write_if_absent_or_force(path: Path, body: str, force: bool, written: list[Path], skipped: list[Path]) -> None:
    if path.exists() and not force:
        skipped.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    written.append(path)


def append_books_index_row(category: str, book_slug: str, title: str) -> bool:
    """Append one row to .skill/books.md if not already present. Returns True if appended."""
    BOOKS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    if not BOOKS_INDEX.exists():
        BOOKS_INDEX.write_text(
            "# Podcast Library Index\n\n"
            "One row per book under `content/podcast/library/<category>/<book-slug>/`.\n\n"
            "| Category | Book Slug | Title | Registry |\n"
            "|---|---|---|---|\n",
            encoding="utf-8",
        )
    existing = BOOKS_INDEX.read_text(encoding="utf-8")
    needle = f"| {category} | {book_slug} |"
    if needle in existing:
        return False
    registry_link = f"[registry](../library/{category}/{book_slug}/_system/registry.md)"
    row = f"| {category} | {book_slug} | {title} | {registry_link} |\n"
    with BOOKS_INDEX.open("a", encoding="utf-8") as f:
        f.write(row)
    return True


def scaffold(category: str, book_slug: str, title: str, author: str | None, force: bool, allow_existing: bool = False) -> int:
    if category not in ALLOWED_CATEGORIES:
        print(
            f"ERROR: category {category!r} not in {sorted(ALLOWED_CATEGORIES)}",
            file=sys.stderr,
        )
        return 1

    book_dir = book_dir_for(category, book_slug)
    if is_non_empty(book_dir) and not force and not allow_existing:
        print(
            f"ERROR: {book_dir.relative_to(REPO_ROOT)} exists and is non-empty.\n"
            f"  Re-run with --force to overwrite stub files (existing chapter "
            f"and contract files are still preserved unless they collide), "
            f"or --allow-existing to fill in only missing stubs (preflight-artifacts mode).",
            file=sys.stderr,
        )
        return 1

    written: list[Path] = []
    skipped: list[Path] = []

    # Create directories.
    for sub in (
        "chapters",
        "chapter-contracts",
        "episodes",
        "transcripts",
        "_system",
        "_system/scratchpad",
        "_system/source",
        "_system/source/text",
        "_system/episode-drafts",
    ):
        (book_dir / sub).mkdir(parents=True, exist_ok=True)

    # Template bindings.
    author_clause = f" by {author}" if author else ""
    author_line = f"Author: **{author}**." if author else "Author: _unspecified_."
    author_short = author.split(",")[0].split(" ")[-1] if author else "the author"
    author_corpus_placeholder = (
        "- _Enumerate this book's author's corpus here. One work per line._"
    )

    bindings = dict(
        title=title,
        book_slug=book_slug,
        category=category,
        author_clause=author_clause,
        author_line=author_line,
        author_short=author_short,
        author_corpus_placeholder=author_corpus_placeholder,
    )

    # Write stub files.
    files = [
        (book_dir / "_README.md", README_TEMPLATE.format(**bindings)),
        (book_dir / "transcripts" / "_README.md", TRANSCRIPTS_README_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "registry.md", REGISTRY_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "pronunciation.md", PRONUNCIATION_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "mangle-map.md", MANGLE_MAP_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "meta-prose-tells.md", META_PROSE_TELLS_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "enrichment-whitelist.md", ENRICHMENT_WHITELIST_TEMPLATE.format(**bindings)),
        (book_dir / "_system" / "enrichment-log.md", ENRICHMENT_LOG_TEMPLATE.format(**bindings)),
    ]
    for path, body in files:
        write_if_absent_or_force(path, body, force, written, skipped)

    # Append top-level books.md index row.
    appended = append_books_index_row(category, book_slug, title)

    # Report.
    print(f"Scaffolded {book_dir.relative_to(REPO_ROOT)}")
    if written:
        print("  Written:")
        for p in written:
            print(f"    {p.relative_to(REPO_ROOT)}")
    if skipped:
        print("  Unchanged (pre-existing; --force to overwrite):")
        for p in skipped:
            print(f"    {p.relative_to(REPO_ROOT)}")
    print(
        f"  Books index: {'appended row' if appended else 'row already present'} "
        f"at {BOOKS_INDEX.relative_to(REPO_ROOT)}"
    )
    print()
    print("Next steps:")
    print(f"  1. Drop the verbatim source file into {(book_dir / '_system' / 'source').relative_to(REPO_ROOT)}/<Source-Title>.<ext>")
    print("  2. Run Phase 0a (OCR / format normalization) → _system/source/text/normalized.md")
    print("  3. Run Phase 0b (English refinement), Phase 0c (Arabic phonetic pass)")
    print("  4. Run Phase 0d (content-depth-driven chapter design) → chapters/ch##-<slug>.txt")
    print("  5. Run Phase 0e (enrichment)")
    print("  6. python3 scripts/podcast/extract_chapter.py ch##-<slug>  (per episode)")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("category", help=f"One of {sorted(ALLOWED_CATEGORIES)}")
    ap.add_argument("book_slug", help="kebab-case, ≤40 chars")
    ap.add_argument("title", help='Human-readable title, e.g. "The Master and the Disciple"')
    ap.add_argument("--author", default=None, help="Author name, free text")
    ap.add_argument("--force", action="store_true", help="Overwrite stub files in a non-empty BOOK_DIR")
    ap.add_argument(
        "--allow-existing",
        action="store_true",
        help="Fill in only missing stub files when BOOK_DIR is non-empty "
             "(preflight-artifacts mode: registry.md / concept-glossary.md / source/ pre-staged).",
    )
    args = ap.parse_args()

    if len(args.book_slug) > 40 or not args.book_slug.replace("-", "").isalnum():
        print(
            f"ERROR: book-slug {args.book_slug!r} must be kebab-case and ≤40 chars",
            file=sys.stderr,
        )
        return 1

    return scaffold(args.category, args.book_slug, args.title, args.author, args.force, args.allow_existing)


if __name__ == "__main__":
    sys.exit(main())
