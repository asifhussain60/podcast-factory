"""P4.7 phase runner — Master & Disciple Ch-02 scaffolding updates."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.7"
DESCRIPTION = "Master & Disciple Ch-02 scaffolding (Numeric Disambiguation + Anachronism + §J checklist)"

REPO_ROOT = Path(__file__).resolve().parents[3]
MD_BASE = REPO_ROOT / "content" / "podcast" / "library" / "books" / "the-master-and-the-disciple" / "_notebooklm"

# Detect markers per acceptance row in podcast-plan.yaml P4.7:
DETECT = (
    (MD_BASE / "02-glossary.md", ("Twelve Jazāʾir", "Seven Oft-Repeated", "Asāas", "Hisab al-Jummal")),
    (MD_BASE / "03-source-integrity-notes.md", ("Numeric / Symbolic enumeration register", "Anachronism register", "12 jazāʾir")),
    (MD_BASE / "ch02-scaffolding.md", ("Numeric Disambiguation", "12 jazāʾir / regions", "NotebookLM Instruction")),
    (MD_BASE / "06-human-review-checklist.md", ("J. Numeric / Symbolic Disambiguation review", "Failure-mode escalation")),
)


def is_done(repo_root: Path | None = None) -> bool:
    for path, markers in DETECT:
        if not path.exists():
            return False
        text = path.read_text()
        if not all(m in text for m in markers):
            return False
    return True


def execute(repo_root: Path | None = None) -> PhaseResult:
    missing: list[str] = []
    for path, markers in DETECT:
        if not path.exists():
            missing.append(f"missing file: {path}")
            continue
        text = path.read_text()
        absent = [m for m in markers if m not in text]
        if absent:
            missing.append(f"{path.name}: missing markers {absent!r}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "P4.7 scaffolding incomplete:\n  " + "\n  ".join(missing)
            ),
            evidence_paths=[str(p) for p, _ in DETECT],
        )
    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "M&D Ch-02 scaffolding updated: glossary + integrity-notes registers + ch02 "
            "Numeric Disambiguation section + checklist §J all present."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(p) for p, _ in DETECT],
    )
