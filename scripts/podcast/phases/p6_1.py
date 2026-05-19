"""P6.1 phase runner — cost-ledger writer."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P6.1"
DESCRIPTION = "scripts/podcast/_cost_ledger.py — JSONL writer + token-usage parser"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "scripts" / "podcast" / "_cost_ledger.py"
TEST = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_cost_ledger.py"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "_cost_ledger.py"
    test = repo_root / "scripts" / "podcast" / "tests" / "test_cost_ledger.py"
    if not (target.exists() and test.exists()):
        return False
    # Validate the module exposes the required public surface.
    text = target.read_text()
    required = (
        "def append_cost_row",
        "def compute_cost_usd",
        "def parse_usage_from_stdout",
        "def append_from_claude_p_stdout",
        "PRICING_USD_PER_MILLION_TOKENS",
    )
    if not all(s in text for s in required):
        return False
    # Tests green.
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_cost_ledger"],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="P6.1 deliverable or its test suite is missing/red. Inspect and fix.",
            evidence_paths=[str(TARGET), str(TEST)],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="_cost_ledger.py present with required surface; tests green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TARGET)],
    )
