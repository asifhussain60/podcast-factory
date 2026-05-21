#!/usr/bin/env python3
"""Sanitize Phase 0d chapter contracts that contain markdown asterisks
which YAML mis-parses as undefined aliases.

The Phase 0d LLM emits list items like:
    tone_constraints:
      - When X sides with *al-Islah*, ... *in this chapter the two...*

YAML reads `*in` as a reference to anchor `in`, which doesn't exist,
and errors with `ComposerError: found undefined alias 'in'`.

Fix: convert every offending flow-scalar list item to a folded block
scalar (`- >`). Inside a folded block, `*` has no YAML semantics.

Idempotent: items already in `- >` or `- |` style are left alone.
Items without markdown asterisks are left alone.

Usage:
    python3 scripts/podcast/sanitize_contract_yaml.py <file.yml> [<more.yml> ...]
        [--check]   only diagnose, don't write
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# A flow-scalar list item that needs conversion:
#   ^<indent>- <content>$
# where <content> doesn't start with a YAML block-scalar indicator (> or |).
LIST_ITEM = re.compile(r"^(?P<indent> +)- (?P<rest>(?![>|]).*)$")

# Markdown asterisk that YAML might parse as an anchor reference:
#   *<word-of-letters-or-hyphens>(space|punct|end)
# We match conservatively — only when followed by something that could END
# the anchor name (non-anchor-char), since YAML stops at non-anchor-name chars.
MARKDOWN_ALIAS = re.compile(r"\*[A-Za-z][\w-]*(?=[\s,.;:!?')])")


def needs_fold(content: str) -> bool:
    """True iff the content has a markdown-asterisk that YAML could mis-parse."""
    return bool(MARKDOWN_ALIAS.search(content))


def sanitize(text: str) -> tuple[str, int]:
    """Convert offending flow list items into folded block scalars."""
    out_lines: list[str] = []
    n_fixed = 0
    for line in text.splitlines(keepends=True):
        m = LIST_ITEM.match(line.rstrip("\n"))
        if m and needs_fold(m.group("rest")):
            indent = m.group("indent")
            rest = m.group("rest")
            out_lines.append(f"{indent}- >\n")
            out_lines.append(f"{indent}  {rest}\n")
            n_fixed += 1
        else:
            out_lines.append(line)
    return "".join(out_lines), n_fixed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--check", action="store_true",
                    help="only diagnose; don't write")
    args = ap.parse_args()

    overall_rc = 0
    for p in args.paths:
        if not p.is_file():
            print(f"  skip (not a file): {p}", file=sys.stderr)
            continue

        src = p.read_text(encoding="utf-8")

        # Check current parse status
        try:
            yaml.safe_load(src)
            cur_ok = True
        except yaml.YAMLError as e:
            cur_ok = False
            cur_err = str(e)

        if cur_ok:
            print(f"  ok (already parses): {p.name}")
            continue

        new, n = sanitize(src)

        # Verify the fix parses
        try:
            yaml.safe_load(new)
            new_ok = True
            new_err = None
        except yaml.YAMLError as e:
            new_ok = False
            new_err = str(e)

        if not new_ok:
            print(f"  FAIL: {p.name} — sanitizer applied {n} fix(es) but still doesn't parse")
            print(f"    before: {cur_err[:120]}")
            print(f"    after:  {new_err[:120]}")
            overall_rc = 1
            continue

        if args.check:
            print(f"  would fix: {p.name} ({n} item(s) converted)")
        else:
            p.with_suffix(p.suffix + ".bak").write_text(src, encoding="utf-8")
            p.write_text(new, encoding="utf-8")
            print(f"  fixed: {p.name} ({n} item(s) converted; backup .bak)")

    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
