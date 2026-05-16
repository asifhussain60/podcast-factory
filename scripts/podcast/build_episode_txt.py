#!/usr/bin/env python3
"""build_episode_txt.py — Concatenate an episode-draft bundle into a single .txt deliverable.

Reads the 5-6 markdown files in an episode-draft folder (00-framing.md, 01-source-primary.md,
02-key-passages.md, 03-context-pack.md, 04-discussion-spine.md, 99-show-notes.md) and emits a
single concatenated .txt with `=== <section-name> ===` separators between sections, suitable as
a NotebookLM source.

Files prefixed `01-source-primary.scratch.md` and any other `.scratch.md` are skipped — they are
authoring scaffolds, not part of the final deliverable.

Usage:
  python3 build_episode_txt.py <draft-dir> <output-txt>

Example:
  python3 scripts/podcast/build_episode_txt.py \
    content/podcast/ayyuhal-walad/_system/episode-drafts/EP01-ayyuhal-walad-ch1 \
    content/podcast/ayyuhal-walad/episodes/EP01-ayyuhal-walad-ch1.txt
"""

import sys
from pathlib import Path

SECTION_TITLES = {
    "00-framing.md": "FRAMING",
    "01-source-primary.md": "SOURCE-PRIMARY",
    "02-key-passages.md": "KEY-PASSAGES",
    "03-context-pack.md": "CONTEXT-PACK",
    "04-discussion-spine.md": "DISCUSSION-SPINE",
    "99-show-notes.md": "SHOW-NOTES",
}

ORDER = ["00-framing.md", "01-source-primary.md", "02-key-passages.md",
         "03-context-pack.md", "04-discussion-spine.md", "99-show-notes.md"]


def build(draft_dir: Path, out_path: Path) -> None:
    if not draft_dir.is_dir():
        sys.exit(f"Not a directory: {draft_dir}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []

    for fname in ORDER:
        f = draft_dir / fname
        if not f.exists():
            continue
        title = SECTION_TITLES[fname]
        body = f.read_text(encoding="utf-8").strip()
        chunks.append(f"=== {title} ===\n\n{body}\n")

    if not chunks:
        sys.exit(f"No section files found in {draft_dir}")

    out_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes, {len(chunks)} sections)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: build_episode_txt.py <draft-dir> <output-txt>")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
