"""phases/merge.py — Merge content branch into develop.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT
from _progress import read_state


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _book_dir_from_state(book_slug: str) -> "Path | None":
    """Locate book_dir via _paths.find_content (used by phase_merge_to_develop)."""
    from _paths import find_content as _find
    found = _find(book_slug)
    return found[2] if found else None


def phase_merge_to_develop(book_slug: str, category: str | None = None) -> None:
    """Fast-forward develop + merge content branch with --no-ff. Never touches main.

    Branch name is derived from category via scripts/podcast/_branching.py.
    If category is omitted (legacy callers), reads it from state.json.
    """
    from _branching import branch_name as _branch_name
    if category is None:
        bd = _book_dir_from_state(book_slug)
        if bd is not None:
            st = read_state(bd) or {}
            category = st.get("category")
    branch = _branch_name(category, book_slug)
    rc, _, err = _git("checkout", "develop")
    if rc != 0:
        raise RuntimeError(f"`git checkout develop` failed: {err}")
    rc, _, err = _git("pull", "--ff-only", "origin", "develop")
    if rc != 0:
        _err(f"warning: `git pull --ff-only origin develop` failed: {err}")
    rc, _, err = _git(
        "merge",
        "--no-ff",
        branch,
        "-m",
        f"Merge branch '{branch}' into develop",
    )
    if rc != 0:
        raise RuntimeError(f"`git merge --no-ff {branch}` failed: {err}")
    rc, _, err = _git("push", "origin", "develop")
    if rc != 0:
        _err(f"warning: `git push origin develop` failed: {err}\n  (local merge preserved)")
