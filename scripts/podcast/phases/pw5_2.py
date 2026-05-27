"""P5.2 (Wave 5) — extended publish gate G8-G12.

Detects that validate_ship_ready.py has been extended with the five
archetype-aware gates: G8 (capstone-mode-honored), G9 (rich-diagram-coverage),
G10 (manual-review-resolved), G11 (knowledge-base-merge-clean),
G12 (augmenter-A/B-acceptance).
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P5.2"
DESCRIPTION = (
    "scripts/podcast/validate_ship_ready.py — G8-G12 archetype-aware gates added "
    "(capstone, diagram-coverage, manual-review, merge-clean, augmenter-AB)"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "validate_ship_ready.py"

# Required gate markers — each must appear in the script.
_MARKERS = (
    "G8",
    "G9",
    "G10",
    "G11",
    "G12",
    "capstone-mode-honored",
    "rich-diagram-coverage",
    "manual-review-resolved",
    "knowledge-base-merge-clean",
    "augmenter",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "validate_ship_ready.py"
    if not script.exists():
        return False
    text = script.read_text()
    return all(m in text for m in _MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "validate_ship_ready.py"

    missing: list[str] = []
    if not script.exists():
        missing.append(f"{script} not found")
    else:
        text = script.read_text()
        for m in _MARKERS:
            if m not in text:
                missing.append(f"validate_ship_ready.py missing marker: {m!r}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Extended publish gate G8-G12 incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(script)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "validate_ship_ready.py extended with G8-G12 archetype-aware gates "
            "(capstone, diagram-coverage, manual-review, merge-clean, augmenter-AB)."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(script)],
    )
