"""P6.2 phase runner — cost-ledger summary CLI."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P6.2"
DESCRIPTION = "scripts/podcast/cost_ledger_summary.py — sums + emits cost-validation.json"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "scripts" / "podcast" / "cost_ledger_summary.py"
TEST = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_cost_ledger_summary.py"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "cost_ledger_summary.py"
    test = repo_root / "scripts" / "podcast" / "tests" / "test_cost_ledger_summary.py"
    if not (target.exists() and test.exists()):
        return False
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_cost_ledger_summary"],
        cwd=repo_root, capture_output=True, timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message="P6.2 deliverable or its test suite is missing/red.",
            evidence_paths=[str(TARGET), str(TEST)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="cost_ledger_summary.py present; tests green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TARGET)],
    )
