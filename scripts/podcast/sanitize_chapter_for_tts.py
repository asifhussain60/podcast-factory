#!/usr/bin/env python3
"""sanitize_chapter_for_tts.py — strip diacritics + apply TTS-safe substitutions to chapter sources.

PURPOSE

  NotebookLM's TTS engine reads the chapter file as the SOURCE for the audio
  overview. Diacritic-bearing Arabic transliteration (ḥayūlā, daʿwa, al-mubdiʿ,
  Duʿa ʿArafa) gets either spelled letter-by-letter or fabricated. Quranic
  citations rendered as "(Quran 3:18)" get spoken as "Surah 3 verse 18" or the
  Arabic surah name — neither what the recipe wants.

  This script applies a one-pass transformation: strip diacritics, substitute
  high-frequency Arabic technicals with TTS-tested forms, expand Quranic
  citations inline with English chapter names, drop romanized-Arabic
  blockquote pairs (keeping the English translation), and paraphrase academic
  English vocabulary the TTS mispronounces.

  Substitution rules live in `_tts_sanitize.py` so both this script and the
  episode-prompt restructure share one source of truth.

USAGE

  # Single file (writes back in place):
  python3 scripts/podcast/sanitize_chapter_for_tts.py library/books/kitab-al-riyad/chapters/ch01-the-perfect-and-the-perfection-of-the-soul.txt

  # Directory of chapters (writes each back in place):
  python3 scripts/podcast/sanitize_chapter_for_tts.py library/books/kitab-al-riyad/chapters/

  # Dry run — print report without modifying files:
  python3 scripts/podcast/sanitize_chapter_for_tts.py --dry-run library/books/kitab-al-riyad/chapters/

IDEMPOTENCY

  Safe to re-run. The substitution rules are designed so once-sanitized text
  passes through unchanged (e.g., "Taw-heed" is not re-substituted because
  "Tawhid" is no longer present after the first pass).

OUTPUT

  Modifies files in place; prints a per-file report of changes applied.
  Exits 0 on success.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _tts_sanitize import sanitize_text  # noqa: E402


def process_file(path: Path, dry_run: bool) -> int:
    """Sanitize one chapter file. Returns the number of substitutions applied."""
    original = path.read_text(encoding="utf-8")
    new_text, report = sanitize_text(original)
    print(f"\n{path}")
    print(report.summary())
    if not dry_run and new_text != original:
        path.write_text(new_text, encoding="utf-8")
        print(f"  → wrote {len(new_text):,} bytes")
    elif dry_run and new_text != original:
        print(f"  → would write {len(new_text):,} bytes (dry-run)")
    return report.total_changes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sanitize_chapter_for_tts.py",
        description="Apply TTS-safe substitutions to a chapter source or a directory of chapters.",
    )
    parser.add_argument("path", help="Chapter file or directory containing chapter .txt files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report changes without modifying files")
    args = parser.parse_args(argv)

    target = Path(args.path).resolve()
    if not target.exists():
        print(f"ERROR: path not found: {target}", file=sys.stderr)
        return 1

    if target.is_file():
        files = [target]
    else:
        files = sorted(p for p in target.glob("*.txt")
                       if p.is_file() and "Glossary" not in p.name)
        if not files:
            print(f"ERROR: no .txt files found in {target}", file=sys.stderr)
            return 1

    total = 0
    for f in files:
        total += process_file(f, args.dry_run)

    print(f"\n{'='*60}")
    print(f"Total: {len(files)} file(s), {total} substitution(s){' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
