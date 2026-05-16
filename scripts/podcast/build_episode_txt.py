#!/usr/bin/env python3
"""build_episode_txt.py — Compile a NotebookLM-ready episode .txt from a draft + chapter.

Under the strict 1:1 chapter ↔ episode mapping (skills-staging/podcast/SKILL.md §0),
the SOURCE block of every episode IS its corresponding chapter file. The episode
draft folder contains ONLY the customize prompt and authoring scaffolds; the chapter
file under BOOK_DIR/chapters/ is the source of truth.

The output file has two clearly delimited blocks:

  === CUSTOMIZE PROMPT — Paste into NotebookLM "Customize" prompt box ===
  <body of 00-framing.md, minus any "Upload checklist" trailer>

  === SOURCE — Upload everything below this line to NotebookLM as the single source ===
  <body of BOOK_DIR/chapters/chNN-<slug>.txt, matched to the episode by slug,
   with all HTML comments stripped and meta-prose tells rejected>

The other draft files (02-key-passages.md, 03-context-pack.md, 04-discussion-spine.md,
99-show-notes.md) are authoring-only scaffolds; they do NOT flow to NotebookLM.

Compliance gates (per content/podcast/_system/notebooklm-best-practices.md):

  - BOOK_DIR/chapters/ must contain at least one .txt before any episode is built.
  - The chapter chNN-<slug>.txt matching the episode EP##-<slug> must exist
    (same slug after the prefix). Slug mismatch = hard error.
  - SOURCE block (the chapter, after stripping) must be 500-5500 words (hard bounds,
    sweet spot 1,800-2,800). Out-of-bound errors and refuses to write.

Meta-protection gates (anti-pattern: chapter prose describing the chapter file itself):

  - HTML comments (`<!-- ... -->`) are stripped from the SOURCE block. Authoring
    metadata can live as HTML comments in the chapter file (ENRICHMENT STATUS,
    Phase 0 tracking, etc.) without reaching NotebookLM.
  - The post-strip SOURCE block is scanned for meta-prose tells (substrings that
    typically introduce a sentence ABOUT the file rather than chapter content).
    Any match is a hard error — the chapter must be cleaned before it can ship.

Usage:
  python3 build_episode_txt.py <BOOK_DIR> <EP##-slug>

Example:
  python3 scripts/podcast/build_episode_txt.py \\
    content/podcast/ayyuhal-walad \\
    EP01-frame-and-first-counsel
"""

import re
import sys
from pathlib import Path

SOURCE_WORD_MIN_HARD = 500
SOURCE_WORD_MAX_HARD = 5500
SOURCE_WORD_MIN_SOFT = 1500
SOURCE_WORD_MAX_SOFT = 4500

EP_PATTERN = re.compile(r"^EP(\d+)-(.+)$")
CH_PATTERN = re.compile(r"^ch(\d+)-(.+)\.txt$")

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Substrings that almost always introduce meta-prose about the file itself,
# not chapter content. If any of these appears in a chapter after comment-stripping,
# the build script refuses — the chapter must be cleaned before it ships to NotebookLM.
# Match is case-insensitive and whole-substring (no word boundaries needed because
# these phrases are distinctive enough).
META_PROSE_TELLS = [
    "this file is",
    "this document is",
    "this chapter file",
    "the body below",
    "the file below",
    "phase 0",
    "phase 0a", "phase 0b", "phase 0c", "phase 0d", "phase 0e", "phase 0f", "phase 0g",
    "enrichment status",
    "enrichment ratio",
    "per content/podcast/_system",
    "nothing has been added that is not in the source",
    "anything ghazali only implies",
    "anything the author only implies",
    "preserved in blockquotes with the original transliteration",
    "ghazali's prose has been clarified",
    "the author's prose has been clarified",
    "structured by beat",
    "refined and enriched presentation",
    "refined presentation of the section",
    "refined presentation of the chapter",
    "[verify citation",
]


def assert_chapters_populated(book_dir: Path) -> list[Path]:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        sys.exit(
            f"ERROR: missing chapters/ directory: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    txt_files = sorted(chapters_dir.glob("*.txt"))
    if not txt_files:
        sys.exit(
            f"ERROR: chapters/ is empty: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    return txt_files


def find_chapter_by_slug(chapters_dir: Path, episode_slug: str) -> Path:
    """Locate ch??-<slug>.txt where <slug> matches the episode's <slug>."""
    candidates = []
    for f in sorted(chapters_dir.glob("*.txt")):
        m = CH_PATTERN.match(f.name)
        if m and m.group(2) == episode_slug:
            candidates.append(f)
    if not candidates:
        existing = ", ".join(f.name for f in sorted(chapters_dir.glob("*.txt")))
        sys.exit(
            f"ERROR: no chapter file matches slug '{episode_slug}' in {chapters_dir}\n"
            f"  Expected: ch??-{episode_slug}.txt\n"
            f"  Existing chapters: {existing}\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), the episode "
            f"slug after 'EP##-' must match the chapter slug after 'ch##-' exactly."
        )
    if len(candidates) > 1:
        sys.exit(
            f"ERROR: multiple chapter files match slug '{episode_slug}': "
            f"{[c.name for c in candidates]}. Resolve the duplicate before building."
        )
    return candidates[0]


def strip_upload_checklist(framing_md: str) -> str:
    parts = re.split(r"(?im)^[#]{1,3}\s*Upload checklist.*$", framing_md, maxsplit=1)
    return parts[0].rstrip() + "\n"


def strip_html_comments(text: str) -> str:
    """Remove <!-- ... --> blocks (multi-line aware), collapse the blank line they leave."""
    cleaned = HTML_COMMENT_RE.sub("", text)
    # Collapse 3+ consecutive newlines to 2 so the stripped section doesn't leave a gap.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def assert_no_meta_prose(source: str, chapter_path: Path) -> None:
    """Refuse to build if the SOURCE contains tells that it's describing itself."""
    lower = source.lower()
    hits = [tell for tell in META_PROSE_TELLS if tell in lower]
    if hits:
        lines = source.splitlines()
        offending = []
        for tell in hits:
            for ln, line in enumerate(lines, 1):
                if tell in line.lower():
                    offending.append(f"  {chapter_path.name}:{ln}: {line.strip()[:120]}")
                    break
        joined = "\n".join(offending[:8])
        sys.exit(
            f"ERROR: chapter contains meta-prose that would reach NotebookLM hosts.\n"
            f"  Tells found: {', '.join(repr(h) for h in hits)}\n"
            f"  Offending lines:\n{joined}\n\n"
            f"  Chapter files must contain ONLY chapter content. Authoring metadata\n"
            f"  belongs in `<!-- ... -->` HTML comments (auto-stripped at build) or in\n"
            f"  a sidecar file. Meta-prose paragraphs that describe the chapter file\n"
            f"  itself ('This file is a refined presentation...', 'Phase 0e enrichment...')\n"
            f"  must be removed. See skills-staging/podcast/SKILL.md §6 Output Rules."
        )


def word_count(text: str) -> int:
    return len(text.split())


def build(book_dir: Path, episode_id: str) -> None:
    book_dir = book_dir.resolve()
    if not book_dir.is_dir():
        sys.exit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")

    m = EP_PATTERN.match(episode_id)
    if not m:
        sys.exit(
            f"ERROR: episode id '{episode_id}' does not match EP##-<slug>. "
            f"Example: EP01-frame-and-first-counsel"
        )
    episode_num, episode_slug = m.group(1), m.group(2)

    draft_dir = book_dir / "_system" / "episode-drafts" / episode_id
    if not draft_dir.is_dir():
        sys.exit(f"ERROR: missing draft folder: {draft_dir}")

    framing_file = draft_dir / "00-framing.md"
    if not framing_file.exists():
        sys.exit(f"ERROR: missing 00-framing.md in {draft_dir}")

    assert_chapters_populated(book_dir)
    chapter_file = find_chapter_by_slug(book_dir / "chapters", episode_slug)

    framing_raw = framing_file.read_text(encoding="utf-8")
    framing = strip_html_comments(strip_upload_checklist(framing_raw)).strip()

    source_raw = chapter_file.read_text(encoding="utf-8")
    source = strip_html_comments(source_raw).strip()

    # Anti-pattern check: chapter prose describing the chapter file itself.
    assert_no_meta_prose(source, chapter_file)

    source_words = word_count(source)
    if source_words < SOURCE_WORD_MIN_HARD or source_words > SOURCE_WORD_MAX_HARD:
        sys.exit(
            f"ERROR: SOURCE block (chapter {chapter_file.name}, post-strip) is "
            f"{source_words} words. Hard band is "
            f"{SOURCE_WORD_MIN_HARD}-{SOURCE_WORD_MAX_HARD}. "
            f"See content/podcast/_system/notebooklm-best-practices.md §3."
        )

    framing_words = word_count(framing)

    out_path = book_dir / "episodes" / f"{episode_id}.txt"
    body = (
        f'=== CUSTOMIZE PROMPT ({framing_words} words) — '
        f'Paste everything in this block into NotebookLM\'s "Customize" prompt box ===\n\n'
        f"{framing}\n\n"
        f'=== SOURCE ({source_words} words, from {chapter_file.name}) — '
        f'Upload everything below this line to NotebookLM as the single source ===\n\n'
        f"{source}\n"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")

    warnings = []
    if source_words < SOURCE_WORD_MIN_SOFT:
        warnings.append(
            f"SOURCE is {source_words} words — under the {SOURCE_WORD_MIN_SOFT}-word "
            f"Default Deep Dive floor. Hosts may resort to filler."
        )
    if source_words > SOURCE_WORD_MAX_SOFT:
        warnings.append(
            f"SOURCE is {source_words} words — over the {SOURCE_WORD_MAX_SOFT}-word "
            f"Longer Deep Dive ceiling. Conversation may lose thread."
        )

    print(
        f"Wrote {out_path}\n"
        f"  framing:  {framing_words} words (post HTML-comment + checklist strip)\n"
        f"  source:   {source_words} words (post HTML-comment strip; chapter: {chapter_file.name})\n"
        f"  total:    {framing_words + source_words} words"
    )
    for w in warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: build_episode_txt.py <BOOK_DIR> <EP##-slug>")
    build(Path(sys.argv[1]), sys.argv[2])
