"""P5.1 (Wave 5) — retroactive enhancement flow for shipped books.

Detects that the unified-schema migration script is present and contains
the canonical archetype map for all known books.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P5.1"
DESCRIPTION = (
    "scripts/podcast/migrate_meta_yml.py — idempotent unified-schema migration "
    "with default archetype map for all shipped books"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "migrate_meta_yml.py"

# Required markers — archetype map entries + idempotency marker.
_MARKERS = (
    "ARCHETYPE_MAP",
    "kitab-al-riyad",
    "scholarly-deep-dive",
    "play-novel",
    "lecture-series",
    "encyclopedic-epistolary",
    "aphorism-collection",
    "idempotent",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "migrate_meta_yml.py"
    if not script.exists():
        return False
    text = script.read_text()
    return all(m in text for m in _MARKERS)


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    script = root / "scripts" / "podcast" / "migrate_meta_yml.py"

    missing: list[str] = []
    if not script.exists():
        missing.append(f"{script} not found")
    else:
        text = script.read_text()
        for m in _MARKERS:
            if m not in text:
                missing.append(f"migrate_meta_yml.py missing marker: {m!r}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Retroactive enhancement script incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(script)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "migrate_meta_yml.py present with complete archetype map "
            "(scholarly-deep-dive, play-novel, lecture-series, encyclopedic-epistolary, aphorism-collection)."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(script)],
    )
