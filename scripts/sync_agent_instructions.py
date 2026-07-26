#!/usr/bin/env python3
"""sync_agent_instructions.py — generate AGENTS.md from CLAUDE.md.

CLAUDE.md is CANONICAL. AGENTS.md is GENERATED. Edit CLAUDE.md; run this; stage both.

WHY THIS EXISTS
---------------
The two files were maintained by hand and were ~83% identical. On 2026-07-26 the drift
was measured and it was not cosmetic:

  * AGENTS.md was MISSING FIVE standing rules that CLAUDE.md carried — including the
    Book Composer singular-path rule, the narrative-frame rule, and the
    site-health-sentinel runtime gate.
  * A blind "Claude" -> "Codex" substitution had been applied to it at some point and
    had damaged real facts: `Technical/claude-code-training` (a content slug that
    exists on disk) became `Technical/Codex-training`; `.claude/hooks/` became
    `.Codex/hooks/`; `~/.claude/projects/.../memory/` became `~/.Codex/projects/...`,
    which does not exist under either casing; and "Claude+Azure pipeline" became
    "Codex+Azure pipeline", which is simply false about what the pipeline calls.
  * It also kept a stale response-template paragraph for six days after CLAUDE.md was
    corrected, and a stale copy of the LLM-agnostic rule.

This is the SAME failure already documented for `.codex/agents/book-challenger.toml`:
a hand-maintained mirror carrying a blind driver substitution that produced paths and
product names which do not exist. The fix that worked there is the fix here.

WHY GENERATE RATHER THAN INCLUDE
--------------------------------
Both files are auto-loaded into every session by their respective drivers. Extracting
the shared 83% into a third file and pointing at it would be the textbook DRY fix and
would be WRONG: models do not reliably follow an include out of an auto-loaded context
file, so it would quietly weaken every future session. Generation keeps each file
fully self-contained — identical session behaviour, one place to edit.

SUBSTITUTIONS ARE DELIBERATELY MINIMAL
--------------------------------------
Almost nothing in CLAUDE.md is driver-specific; it is repo fact. Only the "who loads
this file" sentence genuinely differs. Every other former difference was corruption.

A DENY-LIST guard runs after substitution and FAILS if the output contains any token
known to be a product of the old blind rewrite. That is what stops this script from
recreating the very damage it was written to undo.

Usage:
    sync_agent_instructions.py            # regenerate AGENTS.md
    sync_agent_instructions.py --check    # exit non-zero if AGENTS.md is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "CLAUDE.md"
GENERATED = REPO_ROOT / "AGENTS.md"

BANNER = """<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source: CLAUDE.md. Regenerate: python3 scripts/sync_agent_instructions.py
     Hand edits are overwritten and `--check` fails on drift. Edit CLAUDE.md instead.

     Kept as a full self-contained copy rather than a pointer on purpose: this file is
     auto-loaded into every session, and models do not reliably follow an include out
     of an auto-loaded context file. -->
"""

# The ONLY genuinely driver-specific sentence. Everything else in CLAUDE.md is repo
# fact and is copied verbatim — including `~/.claude/...` memory paths, which name
# where the authoritative memory actually lives regardless of which driver is reading.
SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    (
        "This file is auto-loaded by Claude Code on\nevery session in this directory; treat it as your standing brief.",
        "This file is the Codex-facing mirror of CLAUDE.md, generated from it; treat it\nas your standing brief.",
    ),
)

# Tokens the old blind rewrite produced. None names a real file, slug, or product.
# If any reappears, the generator has reintroduced the bug and must fail loudly.
FORBIDDEN = (
    "Codex-training",  # the real slug is claude-code-training
    ".Codex/",  # the real dirs are .claude/ and .codex/
    "~/.Codex",
    "Codex+Azure",  # the pipeline calls Claude
    "Codex Cowork",  # not a product
    "infra/Codex-agents",
)


def render() -> str:
    text = CANONICAL.read_text(encoding="utf-8")
    for old, new in SUBSTITUTIONS:
        if old not in text:
            raise SystemExit(
                f"sync_agent_instructions: expected substitution anchor not found in CLAUDE.md:\n  {old[:80]!r}\n"
                "CLAUDE.md changed shape — update SUBSTITUTIONS rather than letting the mirror drift."
            )
        text = text.replace(old, new, 1)

    offenders = [tok for tok in FORBIDDEN if tok in text]
    if offenders:
        raise SystemExit(
            "sync_agent_instructions: output contains token(s) from the old blind "
            f"Claude->Codex rewrite: {', '.join(offenders)}.\n"
            "These name no real file, slug, or product. Fix SUBSTITUTIONS."
        )

    return BANNER + "\n" + text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit non-zero on drift; write nothing")
    args = ap.parse_args()

    expected = render()
    current = GENERATED.read_text(encoding="utf-8") if GENERATED.is_file() else None

    if args.check:
        if current != expected:
            print(
                "AGENTS.md is stale or hand-edited.\n"
                "Run: python3 scripts/sync_agent_instructions.py   (then stage AGENTS.md)",
                file=sys.stderr,
            )
            return 1
        print("agent-instructions: AGENTS.md in sync with CLAUDE.md")
        return 0

    if current == expected:
        print("agent-instructions: already in sync")
        return 0
    GENERATED.write_text(expected, encoding="utf-8")
    print(f"agent-instructions: regenerated {GENERATED.relative_to(REPO_ROOT)} from CLAUDE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
