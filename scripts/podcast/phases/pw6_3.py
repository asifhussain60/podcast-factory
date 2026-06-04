"""P6.3 phase runner — encyclopedic-epistolary spec has 7 Rasāʾil-specific meta fields."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P6.3"
DESCRIPTION = "Encyclopedic-epistolary spec updated with 7 Rasāʾil-specific meta fields"

REPO_ROOT = Path(__file__).resolve().parents[3]

SPEC_PATH = (
    Path(__file__).resolve().parents[3]
    / "content" / "_shared" / "archetypes"
    / "encyclopedic-epistolary" / "spec.yml"
)

REQUIRED_FIELDS = [
    "epistle_count",
    "part_map",
    "augmentation_enabled",
    "diagram_density",
    "phased_rollout",
    "capstone_mode",
    "archetype_id",
]


def is_done(repo_root: Path | None = None) -> bool:
    if not SPEC_PATH.exists():
        return False
    text = SPEC_PATH.read_text(encoding="utf-8")
    return all(field in text for field in REQUIRED_FIELDS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if not SPEC_PATH.exists():
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="encyclopedic-epistolary/spec.yml does not exist.",
            evidence_paths=[str(SPEC_PATH)],
        )
    text = SPEC_PATH.read_text(encoding="utf-8")
    missing = [f for f in REQUIRED_FIELDS if f not in text]
    if missing:
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=f"spec.yml missing fields: {', '.join(missing)}",
            evidence_paths=[str(SPEC_PATH)],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="encyclopedic-epistolary spec.yml contains all 7 required meta fields.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(SPEC_PATH)],
    )
