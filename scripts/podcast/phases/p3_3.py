"""P3.3 phase runner — augmentation phase readiness."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done as detect_done

PHASE_ID = "P3.3"
DESCRIPTION = "augmentation phase complete with verification and cache"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (
    REPO_ROOT / "scripts" / "podcast" / "phases" / "augmentation.py",
    REPO_ROOT / "scripts" / "podcast" / "intelligence" / "_citation_verify.py",
)
DETECT_MARKERS = ("verify_url", "verify_doi", "--offline")
DOR = DoR(
    blockers=(
        "Augmentation phase and citation verification module are not yet fully landed.",
    ),
    assumptions=(
        "Live verification path uses URL HEAD + Crossref DOI lookups with cache.",
    ),
    ambiguities=(
        "Network indeterminate outcomes should queue manual review, not fail the phase.",
    ),
    operator_action=(
        "Implement augmentation phase and citation verification module with cache + offline mode "
        "and wire to manual review for indeterminate checks."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    return detect_done(DETECT_FILES, DETECT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="done",
            message="Augmentation phase and citation verification detected.",
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in DETECT_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, DETECT_FILES)
