"""P5.3 (Wave 5) — self-learning promotion lane.

Detects that the promotion_lane.py script is present with the full
cross-book clustering and regression-gated promotion logic.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P5.3"
DESCRIPTION = (
    "scripts/podcast/promotion_lane.py — self-learning promotion lane "
    "(cluster findings → regression-gated spec proposals)"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "promotion_lane.py"

# Required markers — core concepts of the promotion lane.
_MARKERS = (
    "CLUSTER_THRESHOLD",
    "regression",
    "HUMAN_REVIEW_SEVERITIES",
    "Tier-2",
    "Tier-3",
    "findings.jsonl",
    "promotion-proposals",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "promotion_lane.py"
    if not script.exists():
        return False
    text = script.read_text()
    return all(m in text for m in _MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "promotion_lane.py"

    missing: list[str] = []
    if not script.exists():
        missing.append(f"{script} not found")
    else:
        text = script.read_text()
        for m in _MARKERS:
            if m not in text:
                missing.append(f"promotion_lane.py missing marker: {m!r}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Self-learning promotion lane incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(script)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "promotion_lane.py present with cross-book clustering, "
            "regression-gated Tier-2/Tier-3 classification, and human-review safeguard."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(script)],
    )
