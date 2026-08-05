"""intake_status.py — cockpit status view for a running volume/book (Phase 6, Q10).

Read-ONLY shaping of orchestrator-state.json into the dict the live cockpit polls:
phase, cost-vs-cap, per-chapter progress, and whether the run is paused at a
human-review gate (0f / 0ci / 06a / finalize) or the between-volumes pause. The
UI is read-only while a volume runs (single-writer rule) — this never writes.

All reads go through the Phase-1 resolver, so a composite volume slug
(``asaas-vol-02``) resolves to its volume dir exactly like the pipeline sees it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths
from _progress import read_state
from phases.series_plan import _book_cost_so_far, _series_numeric

# Phases that HALT for human review (not failures — the run is waiting on a person).
HUMAN_GATES: frozenset[str] = frozenset({"0f", "0ci", "06a", "finalize"})

# Human-readable label per gate, for the approval card.
GATE_LABELS: dict[str, str] = {
    "0f": "Review the series plan (episode list / length tier)",
    "0ci": "Review the book-intelligence gap analysis",
    "06a": "Review the source before per-chapter authoring",
    "finalize": "Review the finished volume before publish",
}


def status_view(slug: str) -> dict[str, Any]:
    """Return the cockpit status dict for ``slug`` (a book or a composite volume).

    ``found=False`` when the slug doesn't resolve. Otherwise surfaces phase,
    phase_status, the human-gate (if halted at one), cost-vs-cap, and per-chapter
    progress. Pure read — never mutates state.
    """
    found = _paths.find_content(slug)
    if not found:
        return {"found": False, "slug": slug}
    _status, bucket, book_dir = found
    state = read_state(book_dir) or {}

    phase = state.get("phase")
    phase_status = state.get("phase_status")
    at_gate = phase_status == "halted" and phase in HUMAN_GATES

    per = state.get("phases", {}).get("per-chapter", {})
    timings = per.get("chapter_timings", {}) if isinstance(per.get("chapter_timings"), dict) else {}
    completed = per.get("completed_slugs", []) or []
    failed = per.get("failed_slugs", []) or []

    book_spend = _book_cost_so_far(book_dir)
    per_chapter_cap = _series_numeric(book_dir, "per_chapter_cost_cap_usd", default=5.0)
    book_cap = _series_numeric(book_dir, "book_cost_cap_usd", default=0.0)

    return {
        "found": True,
        "slug": slug,
        "bucket": bucket,
        "publication_status": state.get("status", "draft"),
        "work_slug": state.get("work_slug"),
        "volume": state.get("volume"),
        "phase": phase,
        "phase_status": phase_status,
        "last_completed_phase": state.get("last_completed_phase"),
        "last_error": _short_error(state.get("last_error")),
        "at_human_gate": at_gate,
        "gate": {
            "name": phase,
            "label": GATE_LABELS.get(phase, "Human review required"),
        }
        if at_gate
        else None,
        "cost": {
            "book_spend_usd": round(book_spend, 2),
            "per_chapter_cap_usd": per_chapter_cap,
            "book_cap_usd": book_cap,
            "book_cap_active": book_cap > 0,
            "over_book_cap": book_cap > 0 and book_spend > book_cap,
        },
        "chapters": {
            "completed": len(completed),
            "failed": len(failed),
            "total": _chapter_total(book_dir, completed, failed, timings),
            "completed_slugs": sorted(completed),
            "failed_slugs": sorted(failed),
            "timings": timings,
        },
    }


def _chapter_total(book_dir: Path, completed, failed, timings) -> int:
    """Best-effort total chapter count: contracts on disk, else known slugs."""
    cdir = book_dir / "chapter-contracts"
    if cdir.is_dir():
        n = len(sorted(cdir.glob("*.yml")))
        if n:
            return n
    return len(set(completed) | set(failed) | set(timings.keys()))


def _short_error(err: Any) -> str | None:
    if isinstance(err, dict):
        return str(err.get("message", ""))[:300] or None
    if isinstance(err, str):
        return err[:300] or None
    return None


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="cockpit status for a volume/book")
    p.add_argument("slug")
    args = p.parse_args(argv)
    view = status_view(args.slug)
    print(json.dumps({"ok": view.get("found", False), "status": view}))
    return 0 if view.get("found") else 2


if __name__ == "__main__":
    sys.exit(main())
