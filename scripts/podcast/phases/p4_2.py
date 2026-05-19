"""P4.2 phase runner — numeric/symbolic disambiguation handbook."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.2"
DESCRIPTION = "content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md — general protocol"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "content" / "podcast" / ".skill" / "handbook" / "numeric-symbolic-disambiguation.md"

# The 6 sections P4.2 acceptance requires:
REQUIRED_SECTIONS = (
    "Activation triggers",
    "Per-ambiguity workflow",
    "ONE-TIME enumeration",
    "Anachronism handling",
    "Invented content is a P0 BLOCKED",
    "Source-preference register",
)

REQUIRED_CROSS_REFS = (
    "06-abjad-numerals.md",
    "numeric-symbolic-disambiguation-plan.md",
)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "content" / "podcast" / ".skill" / "handbook" / "numeric-symbolic-disambiguation.md"
    if not target.exists():
        return False
    text = target.read_text()
    if not all(s in text for s in REQUIRED_SECTIONS):
        return False
    if not all(r in text for r in REQUIRED_CROSS_REFS):
        return False
    return True


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "numeric-symbolic-disambiguation.md missing required sections "
                f"({', '.join(REQUIRED_SECTIONS)}) or cross-references "
                f"({', '.join(REQUIRED_CROSS_REFS)})."
            ),
            evidence_paths=[str(TARGET)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="Disambiguation handbook present with all 6 sections + cross-refs.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TARGET)],
    )
