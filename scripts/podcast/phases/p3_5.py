"""P3.5 phase runner — phased rollout + tier-2 gate readiness."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done as detect_done

PHASE_ID = "P3.5"
DESCRIPTION = "phased rollout and tier-2 cost gate complete"
REPO_ROOT = Path(__file__).resolve().parents[3]

DETECT_FILES = (
    REPO_ROOT / "scripts" / "podcast" / "orchestrate_book.py",
)
DETECT_MARKERS = ("phased_rollout", "phase boundary", "tier-2")
DOR = DoR(
    blockers=(
        "Phased rollout boundary gating with explicit tier-2 approvals is not yet verifiably wired.",
    ),
    assumptions=(
        "Large books halt at phase boundaries before cost commitment to the next phase.",
    ),
    ambiguities=(
        "Cost-ceiling presentation and gate semantics must be consistent with wave governance docs.",
    ),
    operator_action=(
        "Wire orchestrator phased-rollout boundary halts and tier-2 approval prompts with cost guardrails."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    return detect_done(DETECT_FILES, DETECT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="done",
            message="Phased rollout and tier-2 gate markers detected.",
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in DETECT_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, DETECT_FILES)
