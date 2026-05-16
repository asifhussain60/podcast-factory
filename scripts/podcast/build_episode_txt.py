#!/usr/bin/env python3
"""build_episode_txt.py — Compile a draft folder into a single NotebookLM-ready .txt.

The output file has two clearly delimited blocks:

  === CUSTOMIZE PROMPT — Paste into NotebookLM "Customize" prompt box ===
  <body of 00-framing.md, minus any "Upload checklist" trailer>

  === SOURCE — Upload everything below this line to NotebookLM as the single source ===
  <body of 01-source-primary.md>

The other draft files (02-key-passages.md, 03-context-pack.md, 04-discussion-spine.md,
99-show-notes.md) remain authoring-only scaffolds in the draft folder and do NOT flow
to NotebookLM. They shape the refined source-primary but the listener never sees them.

Compliance gates (per content/podcast/_system/notebooklm-best-practices.md):

  - SOURCE block must be 500-5,500 words (hard bounds). Sweet spot 1,800-2,800.
    Out-of-band emits a warning; out-of-bound errors and refuses to write.
  - BOOK_DIR/chapters/ must contain at least one .txt before any episode is built.
    Episodes cannot exist without source-book chapters.

Usage:
  python3 build_episode_txt.py <draft-dir> <output-txt>

Example:
  python3 scripts/podcast/build_episode_txt.py \\
    content/podcast/ayyuhal-walad/_system/episode-drafts/EP01-ayyuhal-walad-ch1 \\
    content/podcast/ayyuhal-walad/episodes/EP01-ayyuhal-walad-ch1.txt
"""

import re
import sys
from pathlib import Path

SOURCE_WORD_MIN_HARD = 500
SOURCE_WORD_MAX_HARD = 5500
SOURCE_WORD_MIN_SOFT = 1500
SOURCE_WORD_MAX_SOFT = 4500


def find_book_dir(draft_dir: Path) -> Path:
    """draft_dir is BOOK_DIR/_system/episode-drafts/EP##-<slug>/ → walk up 3."""
    return draft_dir.parent.parent.parent


def assert_chapters_populated(book_dir: Path) -> None:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        sys.exit(
            f"ERROR: missing chapters/ directory: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Populate chapters/ before building any episode."
        )
    txt_files = sorted(chapters_dir.glob("*.txt"))
    if not txt_files:
        sys.exit(
            f"ERROR: chapters/ is empty: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Populate chapters/ with one .txt per book chapter before building any episode.\n"
            f"  Hint: for this book the source sections are at "
            f"{book_dir / '_system' / 'source' / 'text' / 'sections'}/."
        )


def strip_upload_checklist(framing_md: str) -> str:
    """Drop any trailing '## Upload checklist' block — that's not a customize prompt."""
    parts = re.split(r"(?im)^[#]{1,3}\s*Upload checklist.*$", framing_md, maxsplit=1)
    return parts[0].rstrip() + "\n"


def word_count(text: str) -> int:
    return len(text.split())


def build(draft_dir: Path, out_path: Path) -> None:
    if not draft_dir.is_dir():
        sys.exit(f"ERROR: not a directory: {draft_dir}")

    book_dir = find_book_dir(draft_dir)
    assert_chapters_populated(book_dir)

    framing_file = draft_dir / "00-framing.md"
    source_file = draft_dir / "01-source-primary.md"

    if not framing_file.exists():
        sys.exit(f"ERROR: missing 00-framing.md in {draft_dir}")
    if not source_file.exists():
        sys.exit(f"ERROR: missing 01-source-primary.md in {draft_dir}")

    framing = strip_upload_checklist(framing_file.read_text(encoding="utf-8")).strip()
    source = source_file.read_text(encoding="utf-8").strip()

    source_words = word_count(source)
    if source_words < SOURCE_WORD_MIN_HARD or source_words > SOURCE_WORD_MAX_HARD:
        sys.exit(
            f"ERROR: SOURCE block is {source_words} words. "
            f"Hard band is {SOURCE_WORD_MIN_HARD}-{SOURCE_WORD_MAX_HARD}. "
            f"See content/podcast/_system/notebooklm-best-practices.md §3."
        )

    framing_words = word_count(framing)

    body = (
        f'=== CUSTOMIZE PROMPT ({framing_words} words) — '
        f'Paste everything in this block into NotebookLM\'s "Customize" prompt box ===\n\n'
        f"{framing}\n\n"
        f'=== SOURCE ({source_words} words) — '
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
        f"  framing: {framing_words} words\n"
        f"  source:  {source_words} words\n"
        f"  total:   {framing_words + source_words} words"
    )
    for w in warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: build_episode_txt.py <draft-dir> <output-txt>")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
