"""P11.1 phase runner — multi-mac decision doc (doc-only deliverable)."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P11.1"
DESCRIPTION = "docs/podcast/multi-mac-decision.md — locked choice (primary-only + SSH viewers)"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "docs" / "podcast" / "multi-mac-decision.md"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "docs" / "podcast" / "multi-mac-decision.md"
    if not target.exists():
        return False
    text = target.read_text()
    # Required content per yaml P11.1 acceptance
    return (
        "primary-only" in text.lower()
        and "SSH-tunneled" in text
        and "RESOLVED" in text
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message="multi-mac-decision.md missing required content (primary-only / SSH-tunneled / RESOLVED).",
            evidence_paths=[str(TARGET)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="multi-mac-decision.md present; choice documented + Q1 resolution recorded.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TARGET)],
    )
