"""state.py — the lane's own step ledger.

DELIBERATELY SEPARATE from `_system/orchestrator-state.json` and from
`_progress.PHASES`. The podcast phase list is not extended, not reordered, and
not made skippable by this lane — that list governs every existing book. A
supplication has its own, much shorter, sequence and records it in its own file:

    _system/supplication-state.json

Nothing in the podcast pipeline reads this file, and this file never claims a
podcast phase name.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import SupplicationError

STATE_FILENAME = "supplication-state.json"

# The lane's ordered steps. `review` is a HUMAN HALT — the driver stops there
# and will not proceed until it is explicitly cleared, so no translation spend
# happens against boundaries a person has not seen.
STEPS: tuple[str, ...] = (
    "intake",
    "ocr",
    "segment",
    "review",
    "translate",
    "verify",
    "render",
    "deliver",
)

HALT_STEPS: frozenset[str] = frozenset({"review"})


def state_path(book_dir: Path) -> Path:
    return book_dir / "_system" / STATE_FILENAME


def load(book_dir: Path) -> dict[str, Any]:
    p = state_path(book_dir)
    if not p.is_file():
        raise SupplicationError(f"no supplication state at {p} — run the intake step first.")
    return json.loads(p.read_text(encoding="utf-8"))


def init(book_dir: Path, *, slug: str, source_language: str) -> dict[str, Any]:
    st = {
        "lane": "supplication",
        "slug": slug,
        "source_language": source_language,
        "step": STEPS[0],
        "step_status": "pending",
        "completed_steps": [],
        "last_error": None,
        "updated_at": _now(),
    }
    save(book_dir, st)
    return st


def save(book_dir: Path, st: dict[str, Any]) -> None:
    st["updated_at"] = _now()
    p = state_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def mark_running(book_dir: Path, step: str) -> dict[str, Any]:
    st = load(book_dir)
    st.update(step=step, step_status="running", last_error=None)
    save(book_dir, st)
    return st


def mark_done(book_dir: Path, step: str) -> dict[str, Any]:
    st = load(book_dir)
    completed = [s for s in st.get("completed_steps", []) if s != step]
    completed.append(step)
    st.update(step=step, step_status="done", completed_steps=completed, last_error=None)
    save(book_dir, st)
    return st


def mark_halted(book_dir: Path, step: str, note: str) -> dict[str, Any]:
    st = load(book_dir)
    st.update(step=step, step_status="halted", last_error=None, halt_note=note)
    save(book_dir, st)
    return st


def mark_failed(book_dir: Path, step: str, err: str) -> dict[str, Any]:
    st = load(book_dir)
    st.update(step=step, step_status="failed", last_error=err)
    save(book_dir, st)
    return st


def clear_halt(book_dir: Path) -> dict[str, Any]:
    """Human sign-off on the review halt — the ONLY way past it."""
    st = load(book_dir)
    if st.get("step") not in HALT_STEPS:
        raise SupplicationError(f"not at a halt step (currently {st.get('step')!r}); nothing to clear.")
    completed = [s for s in st.get("completed_steps", []) if s != st["step"]]
    completed.append(st["step"])
    st.update(step_status="done", completed_steps=completed, halt_note=None)
    st["review_cleared_at"] = _now()
    save(book_dir, st)
    return st


def next_step(st: dict[str, Any]) -> str | None:
    """The first step not yet completed."""
    done = set(st.get("completed_steps", []))
    for s in STEPS:
        if s not in done:
            return s
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
