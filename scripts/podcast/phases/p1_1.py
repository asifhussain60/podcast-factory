"""P1.1 phase runner — Journal/podcast boundary check.

Idempotent. is_done() runs `_boundary_check.py` as a subprocess; exit 0
means clean tree, so the row stays checked. Re-execution on a clean tree
is a no-op.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P1.1"
DESCRIPTION = "scripts/podcast/_boundary_check.py — AST scan for cross-skill writes"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_FILE = REPO_ROOT / "scripts" / "podcast" / "_boundary_check.py"
TEST_FILE = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_boundary_check.py"


def is_done(repo_root: Path | None = None) -> bool:
    """True iff _boundary_check.py exists, the tree scans clean, and tests pass."""
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "_boundary_check.py"
    if not target.exists():
        return False

    # Tree must scan clean (exit 0).
    rc = subprocess.run(
        [sys.executable, str(target)],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    ).returncode
    if rc != 0:
        return False

    # Tests must pass (when present).
    test = repo_root / "scripts" / "podcast" / "tests" / "test_boundary_check.py"
    if not test.exists():
        return False
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_boundary_check"],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    """Validate _boundary_check.py + run it once to confirm baseline clean."""
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "_boundary_check.py"

    if not target.exists():
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="scripts/podcast/_boundary_check.py missing. Restore from git or re-author.",
            evidence_paths=[str(target)],
        )

    # Run the scan on the current tree.
    proc = subprocess.run(
        [sys.executable, str(target)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=(
                f"Boundary violations detected. Resolve before W1 can complete:\n"
                f"{proc.stderr.strip()}"
            ),
            evidence_paths=[str(target)],
        )

    # is_done() also runs the tests; if it returns True we're fully green.
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=(
                "Boundary scan clean BUT test suite scripts.podcast.tests."
                "test_boundary_check is red or missing. Fix tests before claiming P1.1 done."
            ),
            evidence_paths=[str(target)],
        )

    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="Boundary check clean; tree has zero cross-skill writes; tests green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(target)],
    )
