#!/usr/bin/env python3
"""check_doc_links.py — fail on a dead repo-relative link in the normative docs.

Repairing dead links without a gate is a symptom-level fix: the 2026-07-26 sweep found
19 of them, and the dominant cause was a directory (`content/podcast/.skill/handbook/`)
that had been gone since the 2026-05-23 restructure while six files still cited it. The
same rot returns within a release unless something checks.

SCOPE IS DELIBERATELY NARROW — the normative surface only:

    infra/claude-agents/*.md     canonical agent specs
    skills-staging/**/*.md       skill definitions + their references
    CLAUDE.md, AGENTS.md, framework.md, README.md

NOT all markdown. `_workspace/reviews/` and `docs/assessment/` are historical
transcripts full of paths that were correct WHEN WRITTEN; flagging those would make the
gate un-adoptable, and a gate people route around is worse than none.

What is skipped, and why:
  - external URLs, mailto:, in-page anchors
  - `~`-rooted paths (a real file, just outside the repo)
  - anything inside a fenced code block: those are usage examples, and `<name>.md` or
    `path` is illustrative rather than a claim that a file exists
  - angle-bracket placeholders like `<slug>` anywhere in the target

Usage:
    check_doc_links.py            # sweep the whole normative surface
    check_doc_links.py --files a.md,b.md
Exit codes: 0 = clean, 1 = at least one dead link.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GLOBS = (
    "infra/claude-agents/*.md",
    "skills-staging/*/SKILL.md",
    "skills-staging/*/references/*.md",
)
ROOT_DOCS = ("CLAUDE.md", "AGENTS.md", "framework.md", "README.md")

# A repo-relative target is resolved from the repo root when it starts with a known
# top-level directory, and relative to the citing file otherwise.
REPO_PREFIXES = (
    "content/",
    "scripts/",
    "_workspace/",
    "_learning/",
    "infra/",
    "docs/",
    "plan-dashboard/",
    "skills-staging/",
    "tests/",
    "tools/",
    ".github/",
    ".claude/",
    ".codex/",
)

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+?)(?:#[^)]*)?\)")
_FENCE = re.compile(r"^\s*(```|~~~)")
# Inline code spans are stripped before link matching. The convention line in CLAUDE.md
# is literally "`[name](path)`" — an illustration of the link FORM, not a link. Treating
# it as one made the gate report three findings that were never defects, and a gate that
# cries wolf gets switched off.
_CODE_SPAN = re.compile(r"`+[^`]*`+")


def _lines_outside_fences(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((i, _CODE_SPAN.sub("", line)))
    return out


def _is_checkable(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "file:", "#", "~")):
        return False
    if "<" in target or ">" in target:
        return False  # `<name>.md`, `<slug>` — a placeholder, not a claim
    return True


def dead_links(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in _lines_outside_fences(text):
        for m in _LINK.finditer(line):
            target = m.group(1)
            if not _is_checkable(target):
                continue
            base = REPO_ROOT if target.startswith(REPO_PREFIXES) else path.parent
            if not (base / target).exists():
                found.append((lineno, target))
    return found


def surface() -> list[Path]:
    paths: list[Path] = []
    for g in GLOBS:
        paths.extend(sorted(REPO_ROOT.glob(g)))
    paths.extend(REPO_ROOT / d for d in ROOT_DOCS if (REPO_ROOT / d).is_file())
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--files", help="comma-separated paths to check instead of the full surface")
    args = ap.parse_args()

    if args.files:
        candidates = [Path(p) for p in args.files.split(",") if p.strip()]
        allowed = {p.resolve() for p in surface()}
        paths = [p for p in candidates if p.resolve() in allowed]
    else:
        paths = surface()

    total = 0
    for p in paths:
        for lineno, target in dead_links(p):
            rel = p.relative_to(REPO_ROOT)
            print(f"{rel}:{lineno}  dead link -> {target}", file=sys.stderr)
            total += 1

    if total:
        print(
            f"\n{total} dead link(s) across the normative docs. Fix the link, or delete the\n"
            "reference if the target is genuinely gone — do not point at a near-miss.",
            file=sys.stderr,
        )
        return 1
    print(f"doc-links: clean — {len(paths)} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
