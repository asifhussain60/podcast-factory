"""P4.2 (Wave 4) — backbone visualization and live dashboard.

Detects that the plan-dashboard has:
  - PipelineSpine.tsx: interactive backbone component with Phase/Module/Agent
    data model and click-through navigation
  - dashboard.astro: live dashboard page with roadmap + metric tiles
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.2"
DESCRIPTION = (
    "plan-dashboard/src/components/PipelineSpine.tsx (backbone viz) + "
    "plan-dashboard/src/pages/dashboard.astro (live dashboard)"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SPINE_FILE = REPO_ROOT / "plan-dashboard" / "src" / "components" / "PipelineSpine.tsx"
_DASH_FILE = REPO_ROOT / "plan-dashboard" / "src" / "pages" / "dashboard.astro"

# Backbone visualization markers — Phase/Module/Agent data model.
_SPINE_MARKERS = (
    "interface Phase",
    "interface Module",
    "interface Agent",
    "modules",
)

# Live dashboard markers — metric tiles + roadmap data-binding.
_DASH_MARKERS = (
    "roadmap",
    "metric",
    "Live progress",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    spine = root / "plan-dashboard" / "src" / "components" / "PipelineSpine.tsx"
    dash = root / "plan-dashboard" / "src" / "pages" / "dashboard.astro"
    if not spine.exists() or not dash.exists():
        return False
    spine_text = spine.read_text()
    dash_text = dash.read_text()
    return (
        all(m in spine_text for m in _SPINE_MARKERS)
        and all(m in dash_text for m in _DASH_MARKERS)
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    spine = root / "plan-dashboard" / "src" / "components" / "PipelineSpine.tsx"
    dash = root / "plan-dashboard" / "src" / "pages" / "dashboard.astro"

    missing: list[str] = []
    if not spine.exists():
        missing.append(f"{spine} not found")
    else:
        spine_text = spine.read_text()
        for m in _SPINE_MARKERS:
            if m not in spine_text:
                missing.append(f"PipelineSpine.tsx missing marker: {m}")

    if not dash.exists():
        missing.append(f"{dash} not found")
    else:
        dash_text = dash.read_text()
        for m in _DASH_MARKERS:
            if m not in dash_text:
                missing.append(f"dashboard.astro missing marker: {m}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Backbone visualization or live dashboard incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(spine), str(dash)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "Backbone visualization (PipelineSpine.tsx) and live dashboard "
            "(dashboard.astro) present with all required markers."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(spine), str(dash)],
    )
