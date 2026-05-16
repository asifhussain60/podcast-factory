#!/usr/bin/env python3
"""new_episode.py — scaffold a new episode draft folder under a source book.

Usage:
    python new_episode.py <BOOK_DIR> <slug> [--title "Episode Title"] [--registry <PODCAST_ROOT/_system/registry.md>]

What it does:
    1. Reads PODCAST_ROOT/_system/registry.md to find the next monotonic episode number
       (PODCAST_ROOT is BOOK_DIR.parent unless --registry is passed)
    2. Creates BOOK_DIR/_system/episode-drafts/EP##-<slug>/ with stub files (00 through 04, plus 99 optional)
    3. Ensures BOOK_DIR/episodes/ exists (the final concatenated txt lives here, built by build_episode_txt.py)
    4. Adds a draft row to the registry
    5. Prints the new draft folder path

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

| EP# | Title | Slug | Book | Source Type | Status | Date Started | NotebookLM URL |
|-----|-------|------|------|-------------|--------|--------------|----------------|
"""


def next_episode_number(registry_path: Path) -> int:
    if not registry_path.exists():
        return 1
    text = registry_path.read_text(encoding="utf-8")
    nums = [int(m.group(1)) for m in re.finditer(r"\|\s*(\d+)\s*\|", text)]
    return (max(nums) + 1) if nums else 1


def ensure_registry(registry_path: Path) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if not registry_path.exists():
        registry_path.write_text(REGISTRY_HEADER, encoding="utf-8")


def add_registry_row(registry_path: Path, n: int, title: str, slug: str, book_slug: str) -> None:
    today = datetime.date.today().isoformat()
    row = f"| {n:02d} | {title} | {slug} | {book_slug} | _TBD_ | draft | {today} | _pending_ |\n"
    with registry_path.open("a", encoding="utf-8") as f:
        f.write(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new podcast episode draft folder.")
    parser.add_argument("book_dir", type=Path,
                        help="Path to BOOK_DIR (e.g., /PROJECTS/journal/content/podcast/ayyuhal-walad/)")
    parser.add_argument("slug", help="kebab-case episode slug, ≤ 40 chars")
    parser.add_argument("--title", default="Untitled Episode", help="Episode title")
    parser.add_argument("--registry", type=Path, default=None,
                        help="Path to registry.md (defaults to <BOOK_DIR>/../_system/registry.md)")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.slug) or len(args.slug) > 40:
        print(f"ERROR: slug '{args.slug}' must be kebab-case and ≤ 40 chars", file=sys.stderr)
        return 1

    book_dir: Path = args.book_dir.resolve()
    book_slug = book_dir.name
    book_dir.mkdir(parents=True, exist_ok=True)
    (book_dir / "_system" / "episode-drafts").mkdir(parents=True, exist_ok=True)
    (book_dir / "chapters").mkdir(exist_ok=True)
    (book_dir / "episodes").mkdir(exist_ok=True)

    registry_path = args.registry if args.registry else (book_dir.parent / "_system" / "registry.md")
    ensure_registry(registry_path)

    n = next_episode_number(registry_path)
    folder_name = f"EP{n:02d}-{args.slug}"
    draft_dir = book_dir / "_system" / "episode-drafts" / folder_name

    if draft_dir.exists():
        print(f"ERROR: draft folder already exists: {draft_dir}", file=sys.stderr)
        return 1

    draft_dir.mkdir(parents=True)

    for fname, stub in STUB_FILES.items():
        (draft_dir / fname).write_text(stub.format(n=f"{n:02d}", title=args.title), encoding="utf-8")

    add_registry_row(registry_path, n, args.title, args.slug, book_slug)

    print(f"Scaffolded episode draft folder: {draft_dir}")
    print(f"Final deliverable will be:        {book_dir / 'episodes' / (folder_name + '.txt')}")
    print(f"  (build with: python3 scripts/podcast/build_episode_txt.py {draft_dir} {book_dir / 'episodes' / (folder_name + '.txt')})")
    print(f"Registry updated:                 {registry_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
