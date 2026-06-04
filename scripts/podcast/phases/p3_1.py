"""P3.1 phase runner — archetype expansion specs readiness."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done as detect_done

PHASE_ID = "P3.1"
DESCRIPTION = "archetype expansion specs landed and validated"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (
    REPO_ROOT / "content" / "_shared" / "archetypes" / "play-novel" / "spec.yml",
    REPO_ROOT / "content" / "_shared" / "archetypes" / "lecture-series" / "spec.yml",
    REPO_ROOT / "content" / "_shared" / "archetypes" / "encyclopedic-epistolary" / "spec.yml",
)
DETECT_MARKERS = ("required_fields",)
DOR = DoR(
    blockers=(
        "Three archetype spec bundles are not yet detected on disk with validation markers.",
    ),
    assumptions=(
        "Each archetype bundle includes exemplar.md, spec.yml, and anti-patterns.md.",
    ),
    ambiguities=(
        "Spec schema keys must match chapter-design and series-plan consumers.",
    ),
    operator_action=(
        "Author and validate play-novel, lecture-series, and encyclopedic-epistolary archetype specs "
        "under content/_shared/archetypes/ with required_fields markers."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    return detect_done(DETECT_FILES, DETECT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="done",
            message="Archetype expansion specs detected and validated.",
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in DETECT_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, DETECT_FILES)
