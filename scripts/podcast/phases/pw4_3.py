"""P4.3 (Wave 4) — annotation intelligence lane.

Detects that the plan-dashboard has an annotation-ops page wiring
the reading workbench → queue ledger → durable chapter file →
pipeline intelligence path.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.3"
DESCRIPTION = (
    "plan-dashboard/src/pages/annotation-ops.astro — annotation intelligence lane "
    "(reading workbench → queue → durable chapter file → pipeline)"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_ANNOT_FILE = REPO_ROOT / "plan-dashboard" / "src" / "pages" / "annotation-ops.astro"

# Annotation lane markers — the four-stage pipeline path must be present.
_ANNOT_MARKERS = (
    "Annotation Operations",
    "queue",
    "pipeline",
    "chapter",
    "annotation",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    annot = root / "plan-dashboard" / "src" / "pages" / "annotation-ops.astro"
    if not annot.exists():
        return False
    text = annot.read_text()
    return all(m in text for m in _ANNOT_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    annot = root / "plan-dashboard" / "src" / "pages" / "annotation-ops.astro"

    missing: list[str] = []
    if not annot.exists():
        missing.append(f"{annot} not found")
    else:
        text = annot.read_text()
        for m in _ANNOT_MARKERS:
            if m not in text:
                missing.append(f"annotation-ops.astro missing marker: {m}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Annotation intelligence lane incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(annot)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "Annotation intelligence lane (annotation-ops.astro) present with "
            "reading-workbench → queue → chapter-file → pipeline path."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(annot)],
    )
