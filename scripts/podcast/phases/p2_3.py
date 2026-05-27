"""P2.3 phase runner — augmenter implementation + tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P2.3"
DESCRIPTION = "knowledge augmenter implementation + test surface"

REPO_ROOT = Path(__file__).resolve().parents[3]
AUGMENTER = REPO_ROOT / "scripts" / "podcast" / "knowledge" / "augmenter.py"
TEST = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_augmenter.py"


def _tests_green(repo_root: Path) -> bool:
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_augmenter"],
        cwd=repo_root,
        capture_output=True,
        timeout=120,
    ).returncode
    return rc == 0


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    augmenter = repo_root / "scripts" / "podcast" / "knowledge" / "augmenter.py"
    test = repo_root / "scripts" / "podcast" / "tests" / "test_augmenter.py"
    if not augmenter.exists() or not test.exists():
        return False
    text = augmenter.read_text(encoding="utf-8")
    # Guard against scaffold stubs.
    if "NotImplementedError" in text:
        return False
    return _tests_green(repo_root)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not AUGMENTER.exists() or not TEST.exists():
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="augmenter implementation or tests missing.",
            evidence_paths=[str(AUGMENTER), str(TEST)],
        )
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="augmenter exists but tests are red or scaffold stubs remain.",
            evidence_paths=[str(AUGMENTER), str(TEST)],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="augmenter implementation landed and tests are green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(AUGMENTER), str(TEST)],
    )
