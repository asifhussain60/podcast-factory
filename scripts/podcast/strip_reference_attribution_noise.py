#!/usr/bin/env python3
"""Strip bibliographic reference tails from chapter blockquotes.

This keeps the quoted teaching and named speaker, while removing chapter-prose
scaffolding such as:
  in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam (Saying) 147
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _paths import resolve_content  # noqa: E402
from _rules import strip_noise_reference_attributions  # noqa: E402


def strip_book(book_dir: Path, *, dry_run: bool = False) -> tuple[int, int]:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        raise FileNotFoundError(f"missing chapters directory: {chapters_dir}")

    files_changed = 0
    total_strips = 0
    for path in sorted(chapters_dir.glob("ch*.txt")):
        text = path.read_text(encoding="utf-8")
        cleaned, count = strip_noise_reference_attributions(text)
        if count == 0:
            continue
        files_changed += 1
        total_strips += count
        if not dry_run:
            path.write_text(cleaned, encoding="utf-8")
        print(f"{path.name}: stripped {count} reference tail{'s' if count != 1 else ''}")
    return files_changed, total_strips


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--slug", help="Content slug to clean")
    group.add_argument("--book-dir", type=Path, help="Resolved content directory to clean")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    book_dir = args.book_dir if args.book_dir else resolve_content(args.slug)
    files_changed, total_strips = strip_book(book_dir, dry_run=args.dry_run)
    mode = "would strip" if args.dry_run else "stripped"
    print(f"{mode}: {total_strips} reference tails across {files_changed} chapter files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
