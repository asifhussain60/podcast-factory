#!/usr/bin/env python3
"""check-dr005.py — enforce DR-005: every scripts/podcast/ production file ≤ 600 lines.

Architecture decision DR-005 (architecture.md) mandates ≤600-line modules under
scripts/podcast/. Until 2026-07-18 the "Enforced by pre-commit + CI" claim was
stale — nothing checked line counts. This script makes it real, with the files
already over the limit at gate-introduction time GRANDFATHERED in
dr005-grandfather.txt (R3 of the clean-code hardening plan burns that list
down; remove entries as files are split — never add to it).

Scope: tracked *.py under scripts/podcast/, excluding tests/ trees.

Usage:
  check-dr005.py                 # check every tracked in-scope file (CI)
  check-dr005.py FILE [FILE...]  # check the given paths only (pre-commit)

Exit 0 = clean; exit 1 = a non-grandfathered file exceeds the limit, or a
grandfathered file GREW past its recorded count (ratchet: shrink is fine and
updates nothing; growth of a grandfathered file is a violation).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LIMIT = 600
REPO_ROOT = Path(__file__).resolve().parents[2]
GRANDFATHER_FILE = Path(__file__).resolve().parent / "dr005-grandfather.txt"


def in_scope(path: str) -> bool:
    return path.startswith("scripts/podcast/") and path.endswith(".py") and "/tests/" not in path


def load_grandfather() -> dict[str, int]:
    """Path -> line-count ceiling recorded at gate introduction."""
    out: dict[str, int] = {}
    for raw in GRANDFATHER_FILE.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        path, _, count = line.rpartition(" ")
        out[path.strip()] = int(count)
    return out


def tracked_in_scope() -> list[str]:
    res = subprocess.run(
        ["git", "ls-files", "scripts/podcast/*.py", "scripts/podcast/**/*.py"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return sorted({p for p in res.stdout.split() if in_scope(p)})


def main(argv: list[str]) -> int:
    targets = [p for p in argv if in_scope(p)] if argv else tracked_in_scope()
    grandfather = load_grandfather()
    failures: list[str] = []

    for rel in targets:
        f = REPO_ROOT / rel
        if not f.is_file():
            continue
        n = sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
        if n <= LIMIT:
            continue
        ceiling = grandfather.get(rel)
        if ceiling is None:
            failures.append(
                f"{rel}: {n} lines (limit {LIMIT}) — new DR-005 violation. "
                f"Split the module (see module-decomposition-specs.md)."
            )
        elif n > ceiling:
            failures.append(
                f"{rel}: {n} lines, grew past its grandfathered ceiling of "
                f"{ceiling}. Grandfathered files may shrink, never grow — "
                f"split instead of extending."
            )

    if failures:
        print("DR-005 line-count gate FAILED:", file=sys.stderr)
        for msg in failures:
            print(f"  {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
