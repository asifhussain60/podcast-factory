"""P4.8 phase runner — plan staleness signals + intelligence_sources for P4 deliverables.

Verifies that `intelligence_sources.podcast.consult_before_any_edit` cites
both P4 deliverables AND the disambiguation plan's header points at its P4
canonical home in podcast-plan.yaml. Pure-verify runner.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.8"
DESCRIPTION = "intelligence_sources cites P4 deliverables; disambig plan header references P4"

REPO_ROOT = Path(__file__).resolve().parents[3]
YAML = REPO_ROOT / "_workspace" / "plan" / "podcast-plan.yaml"
DISAMBIG_PLAN = REPO_ROOT / "_workspace" / "plan" / "numeric-symbolic-disambiguation-plan.md"


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    yaml_path = repo_root / "_workspace" / "plan" / "podcast-plan.yaml"
    plan_path = repo_root / "_workspace" / "plan" / "numeric-symbolic-disambiguation-plan.md"
    if not yaml_path.exists() or not plan_path.exists():
        return False
    yaml_text = yaml_path.read_text()
    plan_text = plan_path.read_text()
    yaml_ok = (
        "consult_before_any_edit:" in yaml_text
        and "numeric-symbolic-disambiguation.md" in yaml_text
        and "06-abjad-numerals.md" in yaml_text
    )
    plan_ok = "P4" in plan_text and "podcast-plan.yaml" in plan_text
    return yaml_ok and plan_ok


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Either intelligence_sources lacks both P4 deliverable refs, OR "
                "numeric-symbolic-disambiguation-plan.md header doesn't point at "
                "its P4 canonical home in podcast-plan.yaml."
            ),
            evidence_paths=[str(YAML), str(DISAMBIG_PLAN)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="intelligence_sources + disambig plan header both wired for P4.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(YAML), str(DISAMBIG_PLAN)],
    )
