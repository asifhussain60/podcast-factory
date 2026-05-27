"""P6.2 phase runner — exemplar episode complete for all three archetype directories."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P6.2"
DESCRIPTION = "Exemplar episode complete for all three archetype directories"

REPO_ROOT = Path(__file__).resolve().parents[3]

ARCHETYPE_SLUGS = ["play-novel", "lecture-series", "encyclopedic-epistolary"]
REQUIRED_SECTIONS = [
    "## Opening",
    "## Discussion",
    "## Closing",
]


def _exemplar_file(repo_root: Path, slug: str) -> Path:
    return repo_root / "content" / "_shared" / "archetypes" / slug / "exemplar.md"


def _file_valid(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < 300:
        return False
    return any(s in text for s in REQUIRED_SECTIONS)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    return all(_file_valid(_exemplar_file(repo_root, s)) for s in ARCHETYPE_SLUGS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    missing = [
        s for s in ARCHETYPE_SLUGS
        if not _file_valid(_exemplar_file(repo_root, s))
    ]
    if missing:
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=f"exemplar.md missing or too short for: {', '.join(missing)}",
            evidence_paths=[str(_exemplar_file(repo_root, s)) for s in missing],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="exemplar.md present and valid for all three archetype directories.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(_exemplar_file(repo_root, s)) for s in ARCHETYPE_SLUGS],
    )
