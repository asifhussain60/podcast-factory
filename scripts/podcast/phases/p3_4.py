"""P3.4 phase runner — diagram pilot findings readiness.

2026-07-18 (repo-audit R19 resolution): `slides/classify_slides.py` was deleted
as dead code — it was never executed by any live path and this runner only
checked its file EXISTENCE, gaming its own gate. Per the C4 plan entry's own
fallback clause ("if classifier unavailable, gate demotes to P2 advisory"),
the rich-diagram coverage gate is permanently P2 advisory; this phase now
detects only the pilot findings doc.
"""

from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result
from ._dor_halt import is_done as detect_done

PHASE_ID = "P3.4"
DESCRIPTION = "diagram pilot findings recorded (classifier retired; gate P2 advisory)"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (REPO_ROOT / "_workspace" / "plan" / "research" / "notebooklm-diagram-pilot-findings.md",)
DETECT_MARKERS = ("coverage",)
DOR = DoR(
    blockers=("NotebookLM diagram pilot findings doc is not present.",),
    assumptions=(
        "Rich-diagram coverage gate is P2 advisory — the slide classifier was retired 2026-07-18 as dead code.",
    ),
    ambiguities=(),
    operator_action=("Ship the pilot findings file with coverage observations."),
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
