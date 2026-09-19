#!/usr/bin/env python3
"""check_hygiene_ratchets.py — freeze two silent-failure counts per file; they may only fall.

  subprocess_no_timeout  a subprocess.run/check_output/check_call/call with no `timeout=`
  silent_except          an `except` handler whose whole body is `pass` or `continue`
  model_literal          a string that is exactly a Claude/Gemini model id ("claude-opus-4-8"):
                         21 files hard-coded them across five generations, so one price or
                         model change meant editing all of them. New ones belong in the
                         price table (_cost_ledger.py) or a future _models.py registry.

The 2026-09 audit found 128 and 197 of these across scripts/. Fixing them all at once was
rejected: the code is thinly tested and a live book run depends on it. Instead each file's
count is frozen in infra/git-hooks/hygiene-baseline.json. A file may shrink (lower the
baseline with --write-baseline); it may never grow, and a file with no entry may never
gain one. Same shape as DR-005 (check-dr005.py).

Usage:
  check_hygiene_ratchets.py                  # CI / make lint: exit 1 on growth
  check_hygiene_ratchets.py --write-baseline # after fixing some: record the lower counts
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = REPO_ROOT / "infra" / "git-hooks" / "hygiene-baseline.json"

_SUBPROCESS_CALLS = frozenset({"run", "check_output", "check_call", "call"})
_MODEL_ID = re.compile(r"^(claude|gemini)-[A-Za-z0-9._-]+$")
#: The only files allowed to name models: the price table and its future registry.
_MODEL_HOMES = frozenset({"scripts/podcast/_cost_ledger.py", "scripts/podcast/_models.py"})


def _is_subprocess_call(node: ast.Call) -> bool:
    f = node.func
    return (
        isinstance(f, ast.Attribute)
        and f.attr in _SUBPROCESS_CALLS
        and isinstance(f.value, ast.Name)
        and f.value.id == "subprocess"
    )


def _lacks_timeout(node: ast.Call) -> bool:
    for kw in node.keywords:
        if kw.arg == "timeout" or kw.arg is None:  # explicit timeout, or **opts we cannot see into
            return False
    return True


def _is_silent(handler: ast.ExceptHandler) -> bool:
    return all(isinstance(s, (ast.Pass, ast.Continue)) for s in handler.body)


def _count_file(path: Path, *, allow_models: bool = False) -> dict[str, int]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return {}
    counts = {"subprocess_no_timeout": 0, "silent_except": 0, "model_literal": 0}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_subprocess_call(node) and _lacks_timeout(node):
            counts["subprocess_no_timeout"] += 1
        elif isinstance(node, ast.ExceptHandler) and _is_silent(node):
            counts["silent_except"] += 1
        elif (
            not allow_models
            and isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _MODEL_ID.match(node.value)
        ):
            counts["model_literal"] += 1
    return {k: v for k, v in counts.items() if v}


def scan(root: Path) -> dict[str, dict[str, int]]:
    """Per-file counts for production Python under <root>/scripts (tests and caches excluded)."""
    out: dict[str, dict[str, int]] = {}
    for path in sorted((root / "scripts").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if "/tests/" in rel or "__pycache__" in rel:
            continue
        counts = _count_file(path, allow_models=rel in _MODEL_HOMES)
        if counts:
            out[rel] = counts
    return out


def load_baseline(path: Path = BASELINE) -> dict[str, dict[str, int]]:
    return json.loads(path.read_text(encoding="utf-8"))["files"] if path.exists() else {}


def write_baseline(current: dict[str, dict[str, int]], path: Path = BASELINE) -> None:
    totals: dict[str, int] = {}
    for counts in current.values():
        for metric, n in counts.items():
            totals[metric] = totals.get(metric, 0) + n
    payload = {
        "_about": "Shrink-only hygiene ratchet; see scripts/check_hygiene_ratchets.py. Lower with --write-baseline, never raise by hand.",
        "totals": totals,
        "files": current,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compare(current: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> tuple[list[str], list[str]]:
    """(problems, shrunk). A problem is growth or a new violation; shrunk lists what can be lowered."""
    problems: list[str] = []
    shrunk: list[str] = []
    for rel, counts in current.items():
        for metric, n in counts.items():
            allowed = baseline.get(rel, {}).get(metric, 0)
            if n > allowed:
                problems.append(f"{rel}: {metric} is {n}, baseline allows {allowed}")
            elif n < allowed:
                shrunk.append(f"{rel}: {metric} {allowed} -> {n}")
    for rel, counts in baseline.items():
        for metric, allowed in counts.items():
            if current.get(rel, {}).get(metric, 0) == 0 and allowed:
                shrunk.append(f"{rel}: {metric} {allowed} -> 0")
    return problems, shrunk


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-baseline", action="store_true", help="record the current (lower) counts")
    args = ap.parse_args(argv)
    current = scan(REPO_ROOT)
    if args.write_baseline:
        write_baseline(current)
        print(f"baseline written: {sum(sum(c.values()) for c in current.values())} findings in {len(current)} files")
        return 0
    problems, shrunk = compare(current, load_baseline())
    for line in problems:
        print(f"HYGIENE RATCHET: {line}", file=sys.stderr)
    if shrunk:
        print(
            f"hygiene: {len(shrunk)} count(s) fell — run `python3 scripts/check_hygiene_ratchets.py --write-baseline` to lock it in",
            file=sys.stderr,
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
