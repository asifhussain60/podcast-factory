"""P3.2 phase runner — multi-tier capstone readiness."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done as detect_done

PHASE_ID = "P3.2"
DESCRIPTION = "multi-tier capstone module complete"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (
    REPO_ROOT / "scripts" / "podcast" / "_authoring" / "capstone.py",
)
DETECT_MARKERS = ("CrossTierRead", "full_brethren")
DOR = DoR(
    blockers=(
        "Dedicated capstone module with recursion-invariant enforcement is not yet detected.",
    ),
    assumptions=(
        "Tier-2 capstone reads only tier-1 bundle + chapter abstracts.",
    ),
    ambiguities=(
        "Capstone mode defaults must match per-book meta.yml schema.",
    ),
    operator_action=(
        "Implement scripts/podcast/_authoring/capstone.py with recursion guards, mode handling, "
        "and doctrinal-clean assertion path."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    return detect_done(DETECT_FILES, DETECT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="done",
            message="Multi-tier capstone module detected with invariant markers.",
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in DETECT_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, DETECT_FILES)
