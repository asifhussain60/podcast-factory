"""P4.4 phase runner — pre-refined-source-mode handbook extension.

Verifies the handbook contains the Numeric Disambiguation section + the
invented-enumeration failure-mode entry. Pure-verify runner.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.4"
DESCRIPTION = "pre-refined-source-mode handbook has Numeric Disambiguation + failure-mode #6"

REPO_ROOT = Path(__file__).resolve().parents[3]
HANDBOOK = REPO_ROOT / "content" / "podcast" / ".skill" / "handbook" / "pre-refined-source-mode.md"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    p = repo_root / "content" / "podcast" / ".skill" / "handbook" / "pre-refined-source-mode.md"
    if not p.exists():
        return False
    text = p.read_text()
    # Required markers from P4.4 acceptance:
    #   • the new scaffolding step (Numeric Disambiguation)
    #   • the new failure-mode entry (invented enumeration = P0)
    return (
        "## Numeric Disambiguation" in text
        and "Asserting an invented enumeration" in text
        and "P0 BLOCKED" in text
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "pre-refined-source-mode.md missing Numeric Disambiguation section "
                "or the invented-enumeration P0 failure-mode entry."
            ),
            evidence_paths=[str(HANDBOOK)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="Handbook carries the Numeric Disambiguation scaffolding step + P0 failure-mode.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(HANDBOOK)],
    )
