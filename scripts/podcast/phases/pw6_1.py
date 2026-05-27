"""P6.1 phase runner — anti-patterns catalog for all three archetype directories."""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P6.1"
DESCRIPTION = "Anti-patterns catalog complete for all three archetype directories"

REPO_ROOT = Path(__file__).resolve().parents[3]

ARCHETYPE_SLUGS = ["play-novel", "lecture-series", "encyclopedic-epistolary"]
REQUIRED_SECTIONS = [
    "## Host behavior",
    "## Citation",
    "## Register",
]


def _anti_patterns_file(repo_root: Path, slug: str) -> Path:
    return repo_root / "content" / "_shared" / "archetypes" / slug / "anti-patterns.md"


def _file_valid(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < 200:
        return False
    return any(s in text for s in REQUIRED_SECTIONS)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    return all(_file_valid(_anti_patterns_file(repo_root, s)) for s in ARCHETYPE_SLUGS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    missing = [
        s for s in ARCHETYPE_SLUGS
        if not _file_valid(_anti_patterns_file(repo_root, s))
    ]
    if missing:
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message=f"anti-patterns.md missing or invalid for: {', '.join(missing)}",
            evidence_paths=[str(_anti_patterns_file(repo_root, s)) for s in missing],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="anti-patterns.md present and valid for all three archetype directories.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(_anti_patterns_file(repo_root, s)) for s in ARCHETYPE_SLUGS],
    )
