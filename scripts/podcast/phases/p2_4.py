"""P2.4 phase runner — podcast-e2e CI workflow."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P2.4"
DESCRIPTION = ".github/workflows/podcast-e2e.yml — PR-gating CI workflow"

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "podcast-e2e.yml"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    wf = repo_root / ".github" / "workflows" / "podcast-e2e.yml"
    if not wf.exists():
        return False
    text = wf.read_text()
    return (
        "pull_request" in text
        and "scripts/podcast/" in text
        and "unittest" in text
        and "_boundary_check" in text
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message="podcast-e2e.yml missing or doesn't gate on the required surface.",
            evidence_paths=[str(WORKFLOW)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="podcast-e2e.yml present; gates on scripts/podcast/ + runs unittest + boundary check.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(WORKFLOW)],
    )
