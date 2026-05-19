"""P4.1 phase runner — abjad-numerals shared file."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.1"
DESCRIPTION = "content/_shared/arabic/06-abjad-numerals.md — Mashriqi+Maghribi tables + ref calcs"

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "content" / "_shared" / "arabic" / "06-abjad-numerals.md"

REQUIRED_MARKERS = (
    "Mashriqi",                       # both tables present
    "Maghribi",
    "Hisab al-Jummal",                # practice section
    "Allāh",                          # ref calc 66 (with macron, matches file)
    "**66**",
    "**786**",                        # basmala
    "**92**",                         # Muhammad
    "**110**",                        # ʿAlī
    "kun",                            # Ch-02 worked calcs
    "**70**",
    "fayakun",
    "**166**",
)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    target = repo_root / "content" / "_shared" / "arabic" / "06-abjad-numerals.md"
    if not target.exists():
        return False
    text = target.read_text()
    return all(m in text for m in REQUIRED_MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "06-abjad-numerals.md missing required content (Mashriqi + Maghribi "
                "tables, Hisab al-Jummal section, reference calculations, Ch-02 "
                "worked examples)."
            ),
            evidence_paths=[str(TARGET)],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message="Abjad reference file present with full tables + reference calculations.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(TARGET)],
    )
