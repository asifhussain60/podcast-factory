"""P4.3 phase runner — SKILL.md pre-read extension.

Verifies that SKILL.md cites both the abjad-numerals reference (06-abjad-
numerals.md) and the numeric-symbolic-disambiguation handbook. Pure-verify
runner; the edits ship in the same commit.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.3"
DESCRIPTION = "SKILL.md pre-read list includes abjad + disambiguation references"

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_FILE = REPO_ROOT / "skills-staging" / "podcast" / "SKILL.md"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    p = repo_root / "skills-staging" / "podcast" / "SKILL.md"
    if not p.exists():
        return False
    text = p.read_text()
    return (
        "06-abjad-numerals.md" in text
        and "numeric-symbolic-disambiguation.md" in text
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "SKILL.md missing references to 06-abjad-numerals.md and/or "
                "numeric-symbolic-disambiguation.md. Add them under the §10 "
                "pre-read list before W1 can claim P4.3 done."
            ),
            evidence_paths=[str(SKILL_FILE)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="SKILL.md cites both P4 deliverables in the pre-read list.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(SKILL_FILE)],
    )
