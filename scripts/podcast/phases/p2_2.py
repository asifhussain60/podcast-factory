"""P2.2 phase runner — sunny-day E2E test."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P2.2"
DESCRIPTION = "scripts/podcast/tests/e2e/test_full_pipeline.py — mocked sunny-day E2E"

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST = REPO_ROOT / "scripts" / "podcast" / "tests" / "e2e" / "test_full_pipeline.py"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    test = repo_root / "scripts" / "podcast" / "tests" / "e2e" / "test_full_pipeline.py"
    if not test.exists():
        return False
    text = test.read_text()
    # Required: SunnyDayE2ETests + numeric-disambiguation-register check + halt-at-0f assertion
    required = (
        "class SunnyDayE2ETests",
        "numeric-disambiguation-register",
        "halts_at_0f",
        "NO ARTIFACT",  # P5.2 regression assertion
    )
    if not all(s in text for s in required):
        return False
    # Tests green
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.e2e.test_full_pipeline"],
        cwd=repo_root, capture_output=True, timeout=120,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message="P2.2 test missing required content OR test suite red.",
            evidence_paths=[str(TEST)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="sunny-day E2E test present + green; state-machine ordering verified.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TEST)],
    )
