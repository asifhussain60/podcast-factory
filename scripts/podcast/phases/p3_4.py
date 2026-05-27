"""P3.4 phase runner — diagram pilot and classifier gate readiness."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done as detect_done

PHASE_ID = "P3.4"
DESCRIPTION = "diagram pilot and classifier gate aligned"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (
    REPO_ROOT / "_workspace" / "plan" / "research" / "notebooklm-diagram-pilot-findings.md",
    REPO_ROOT / "scripts" / "podcast" / "slides" / "classify_slides.py",
)
DETECT_MARKERS = ("coverage",)
DOR = DoR(
    blockers=(
        "NotebookLM diagram pilot findings and classifier implementation are not both present.",
    ),
    assumptions=(
        "Classifier gate severity is set by measured pilot capability.",
    ),
    ambiguities=(
        "Fallback path policy when classifier is unavailable must be explicitly documented.",
    ),
    operator_action=(
        "Ship pilot findings file plus classify_slides.py with coverage gate logic and fallback behavior."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    return detect_done(DETECT_FILES, DETECT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="done",
            message="Diagram pilot findings and classifier gate artifacts detected.",
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in DETECT_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, DETECT_FILES)
