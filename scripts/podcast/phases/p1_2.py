"""P1.2 phase runner — manual library handoff (proposal writer + docs + SKILL section)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P1.2"
DESCRIPTION = "_proposal_writer.py + manual-library-handoff.md + SKILL.md section"

REPO_ROOT = Path(__file__).resolve().parents[3]
WRITER = REPO_ROOT / "scripts" / "podcast" / "_proposal_writer.py"
DOC = REPO_ROOT / "docs" / "podcast" / "manual-library-handoff.md"
SKILL = REPO_ROOT / "skills-staging" / "podcast" / "SKILL.md"
TEST = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_proposal_writer.py"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    writer = repo_root / "scripts" / "podcast" / "_proposal_writer.py"
    doc = repo_root / "docs" / "podcast" / "manual-library-handoff.md"
    skill = repo_root / "skills-staging" / "podcast" / "SKILL.md"
    test = repo_root / "scripts" / "podcast" / "tests" / "test_proposal_writer.py"
    if not (writer.exists() and doc.exists() and skill.exists() and test.exists()):
        return False
    skill_text = skill.read_text()
    if "Manual library handoff" not in skill_text:
        return False
    writer_text = writer.read_text()
    if "SCHEMA_VERSION" not in writer_text or "write_proposal" not in writer_text:
        return False
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_proposal_writer"],
        cwd=repo_root, capture_output=True, timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "P1.2 not fully met: writer module / handoff doc / SKILL.md section / "
                "tests must all be present and green."
            ),
            evidence_paths=[str(WRITER), str(DOC), str(SKILL), str(TEST)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="proposal writer + handoff doc + SKILL.md section in place; tests green.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(WRITER), str(DOC), str(SKILL)],
    )
