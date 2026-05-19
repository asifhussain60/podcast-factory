"""P5.4 phase runner — Phase-id constants module.

Idempotent. is_done() is true iff `scripts/podcast/_phases.py` exists with
the Phase StrEnum having all 14 canonical values AND the test suite is
green. The deliverable file ships in the same commit as this runner; the
runner just validates + marks acceptance rows.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P5.4"
DESCRIPTION = "scripts/podcast/_phases.py — Phase StrEnum (14 canonical values)"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_FILE = REPO_ROOT / "scripts" / "podcast" / "_phases.py"
TEST_FILE = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_phases.py"

EXPECTED_VALUES = (
    "01-preflight", "02-branch", "03-scaffold",
    "04-ocr-translate", "05-refine-english", "06-phonetics",
    "07-chapter-design", "08-enrichment", "09-series-plan",
    "10-register-series", "11-per-chapter", "12-trainer",
    "13-merge", "14-done",
)


def is_done(repo_root: Path | None = None) -> bool:
    """True iff _phases.py exists, has all 14 canonical values, and tests pass."""
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "_phases.py"
    if not target.exists():
        return False
    text = target.read_text()
    if not all(v in text for v in EXPECTED_VALUES):
        return False
    # Optionally run the unit tests as the final gate. Tolerate test absence
    # (the runner can run before the test file exists, but we ship them together).
    test = repo_root / "scripts" / "podcast" / "tests" / "test_phases.py"
    if not test.exists():
        return False
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_phases"],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    """Author the constants module + mark its acceptance rows.

    The file content is generated deterministically from EXPECTED_VALUES.
    Re-execution is safe; idempotent.
    """
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "scripts" / "podcast" / "_phases.py"

    # The deliverable file should already exist (shipped in the same commit
    # as this runner). is_done() handles validation. If somehow missing,
    # we don't auto-generate — that's a human-review situation.
    if not target.exists():
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=(
                "scripts/podcast/_phases.py missing. This file should be checked "
                "in alongside this runner. Restore from git or re-author."
            ),
            evidence_paths=[str(target)],
        )

    # Validate by calling is_done() — this also runs the test suite.
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=(
                "Validation failed: _phases.py exists but is_done() returned False. "
                "Either the 14 canonical values are missing OR the test suite "
                "scripts.podcast.tests.test_phases is red."
            ),
            evidence_paths=[str(target)],
        )

    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message=f"_phases.py present with 14 canonical Phase values; tests green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(target)],
    )
