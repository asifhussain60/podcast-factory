#!/usr/bin/env python3
"""Normalize Azure OCR's `((text))` double-paren artifact to markdown italics.

Azure Document Intelligence emits `((text))` for what was likely italics
or quotation marks in the source PDF. Phase 0b refinement preserves these
inconsistently (about 75% normalized, 25% left as-is in observed KaR run).
This deterministic post-process converts every remaining `((text))` to
`*text*` (markdown italics) so the assembled refined-english.md is
internally consistent.

Idempotent — running it twice produces the same output as running it once.

Usage:
    python3 scripts/podcast/normalize_double_parens.py <path-to-md>
        [--in-place]

If --in-place, the original is overwritten and a `.bak` sibling is saved.
Without --in-place, the normalized text goes to stdout.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PAREN_PATTERN = re.compile(r"\(\(([^()]+)\)\)")


def normalize(text: str) -> tuple[str, int]:
    """Replace every `((token))` with `*token*`. Returns (text, n_replaced)."""
    n = 0

    def _sub(m: re.Match[str]) -> str:
        nonlocal n
        n += 1
        return f"*{m.group(1)}*"

    return PAREN_PATTERN.sub(_sub, text), n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--in-place", action="store_true",
                    help="overwrite the input file (saves .bak)")
    args = ap.parse_args()

    if not args.path.is_file():
        print(f"error: {args.path} not found", file=sys.stderr)
        return 1

    src = args.path.read_text(encoding="utf-8")
    out, n = normalize(src)

    if args.in_place:
        args.path.with_suffix(args.path.suffix + ".bak").write_text(src, encoding="utf-8")
        args.path.write_text(out, encoding="utf-8")
        print(f"normalized {n} occurrence(s); backup at {args.path}.bak", file=sys.stderr)
    else:
        sys.stdout.write(out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
