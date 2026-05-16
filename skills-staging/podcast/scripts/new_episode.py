#!/usr/bin/env python3
"""new_episode.py — scaffold a new episode folder in the podcast workspace.

Usage:
    python new_episode.py <PODCAST_DIR> <slug> [--title "Episode Title"]

What it does:
    1. Reads _registry.md to find the next monotonic episode number
    2. Creates episodes/EP##-<slug>/ with stub files (00 through 04, plus 99 optional)
    3. Adds a draft row to _registry.md
    4. Creates _workspace/EP##-<slug>/ for scratch distillation
    5. Prints the new episode folder path

Stub files are skeletal — Claude fills them during Phase 3.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

STUB_FILES = {
    "00-framing.md": "# Framing — Episode {n}: {title}\n\n## Audience\n\n_To be filled in Phase 1._\n\n## Angle\n\n## Host Dynamic\n\n## Central Tensions\n\n## Tone Constraints\n\n## Steering Instructions\n",
    "01-source-primary.md": "# {title} — [Author]\n\n## Source\n\n- **Author:**\n- **Work:**\n- **Edition/Translator:**\n- **Year:**\n- **Section/Chapter:**\n- **Source path:**\n",
    "02-key-passages.md": "# Key Passages — {title}\n\n_Verbatim quotes from the source, in source order. Each passage in a blockquote with attribution._\n",
    "03-context-pack.md": "# Context Pack — {title}\n\n## Author\n\n## Tradition\n\n## Historical Moment\n\n## Related Works\n\n## Why Now\n",
    "04-discussion-spine.md": "# Discussion Spine — Episode {n}: {title}\n\n_6–12 beats. Each beat: Key question, Tension, Anchor passage, Landing._\n",
    "99-show-notes.md": "# Show Notes — Episode {n}: {title}\n\n## Blurb\n\n## Listening Time\n\n## Sources\n\n## References Mentioned\n\n## Related Episodes\n",
}

REGISTRY_HEADER = """# Podcast Episode Registry

| EP# | Title | Slug | Source Type | Status | Date Started | NotebookLM URL |
|-----|-------|------|-------------|--------|--------------|----------------|
"""


def next_episode_number(registry_path: Path) -> int:
    if not registry_path.exists():
        return 1
    text = registry_path.read_text(encoding="utf-8")
    nums = [int(m.group(1)) for m in re.finditer(r"\|\s*(\d+)\s*\|", text)]
    return (max(nums) + 1) if nums else 1


def ensure_registry(registry_path: Path) -> None:
    if not registry_path.exists():
        registry_path.write_text(REGISTRY_HEADER, encoding="utf-8")


def add_registry_row(registry_path: Path, n: int, title: str, slug: str) -> None:
    today = datetime.date.today().isoformat()
    row = f"| {n:02d} | {title} | {slug} | _TBD_ | draft | {today} | _pending_ |\n"
    with registry_path.open("a", encoding="utf-8") as f:
        f.write(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new podcast episode folder.")
    parser.add_argument("podcast_dir", type=Path, help="Path to PODCAST_DIR (e.g., /PROJECTS/journal/podcast/)")
    parser.add_argument("slug", help="kebab-case episode slug, ≤ 40 chars")
    parser.add_argument("--title", default="Untitled Episode", help="Episode title")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.slug) or len(args.slug) > 40:
        print(f"ERROR: slug '{args.slug}' must be kebab-case and ≤ 40 chars", file=sys.stderr)
        return 1

    podcast_dir: Path = args.podcast_dir
    podcast_dir.mkdir(parents=True, exist_ok=True)
    (podcast_dir / "episodes").mkdir(exist_ok=True)
    (podcast_dir / "_archive").mkdir(exist_ok=True)
    (podcast_dir / "_workspace").mkdir(exist_ok=True)

    registry_path = podcast_dir / "_registry.md"
    ensure_registry(registry_path)

    n = next_episode_number(registry_path)
    folder_name = f"EP{n:02d}-{args.slug}"
    episode_dir = podcast_dir / "episodes" / folder_name
    workspace_dir = podcast_dir / "_workspace" / folder_name

    if episode_dir.exists():
        print(f"ERROR: episode folder already exists: {episode_dir}", file=sys.stderr)
        return 1

    episode_dir.mkdir(parents=True)
    workspace_dir.mkdir(parents=True)

    for fname, stub in STUB_FILES.items():
        (episode_dir / fname).write_text(stub.format(n=f"{n:02d}", title=args.title), encoding="utf-8")

    add_registry_row(registry_path, n, args.title, args.slug)

    print(f"Scaffolded episode folder: {episode_dir}")
    print(f"Scratch workspace:          {workspace_dir}")
    print(f"Registry updated:           {registry_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
