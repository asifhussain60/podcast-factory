#!/usr/bin/env python3
"""_progress.py — atomic state-file writer for orchestrate_book.py.

The state file at `<BOOK_DIR>/_system/orchestrator-state.json` is the
**single source of truth** for the autonomous orchestrator. Per the v2
spec (docs/architecture/podcast-orchestrator.html), there is no committed
`PROGRESS.md` artifact — this file is read by `orchestrate-book --status`
to render a human view on demand.

Atomicity: every write goes through a tmpfile + fsync + rename so that
`--resume` after a kill always sees either the old state or the new state,
never a partial file.

Schema (versioned via `schema_version`):

    {
      "schema_version": 1,
      "book_slug": "<slug>",
      "category": "books|articles|...",
      "branch": "book/<slug>",
      "phase": "<phase-id>",
      "phase_status": "running|completed|failed|halted",
      "last_completed_phase": "<phase-id>" | null,
      "next_phase": "<phase-id>" | null,
      "last_error": null | { "phase": "...", "message": "...", "ts": "..." },
      "phases": {
        "pre-flight": { "ts_started": "...", "ts_completed": "...", "status": "..." },
        "branch":     { ... },
        "scaffold":   { ... },
        "0a":         { ... },
        "0b":         { ... },
        ...
      },
      "cost": { "azure_usd": 0.0, "anthropic_usd": 0.0 },
      "wall_clock_sec": 0,
      "ts_started":  "<UTC ISO8601>",
      "ts_updated":  "<UTC ISO8601>",
      "challenger_version": "<semver-from-_rules.py>",
      "orchestrator_version": "<this-script's version>"
    }
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORCHESTRATOR_VERSION = "1.2"  # 2026-05-19: chunked 0b/0c + unit_mode (chapter|section|auto) + --retry-phase
SCHEMA_VERSION = 1

# Phase identifiers in canonical order — keep in sync with orchestrate_book.py.
PHASES = (
    "pre-flight",
    "branch",
    "scaffold",
    "0a",       # Azure OCR + Translation (deterministic)
    "0b",       # English refinement (LLM)
    "0c",       # Arabic phonetic pass (LLM)
    "0d",       # Chapter design (LLM)
    "0e",       # Enrichment (LLM)
    "0f",       # Series plan halt (deterministic write + human gate)
    "0g",       # Register series (deterministic)
    "per-chapter",  # iterated across the chapter list on --resume
    "per-chapter-slides",  # optional; gated by series.enable_slide_decks. Per-chapter slide-deck authoring + slide-deck-challenger convergence. Skipped (status="skipped") when flag is false.
    "trainer",
    "merge",
    "done",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "orchestrator-state.json"


def read_state(book_dir: Path) -> dict[str, Any] | None:
    """Return the current state dict or None if no state file exists."""
    p = state_path(book_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def initial_state(book_slug: str, category: str) -> dict[str, Any]:
    """Build the initial state dict for a new orchestrator run."""
    now = _utc_now()
    # Best-effort challenger version stamp.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _rules import CHALLENGER_VERSION as _cv  # type: ignore
        challenger_version = _cv
    except Exception:
        challenger_version = "unknown"

    return {
        "schema_version": SCHEMA_VERSION,
        "book_slug": book_slug,
        "category": category,
        "branch": f"book/{book_slug}",
        "phase": "pre-flight",
        "phase_status": "running",
        "last_completed_phase": None,
        "next_phase": "branch",
        "last_error": None,
        "phases": {p: {"status": "pending"} for p in PHASES},
        "cost": {"azure_usd": 0.0, "anthropic_usd": 0.0},
        "wall_clock_sec": 0,
        "ts_started": now,
        "ts_updated": now,
        "challenger_version": challenger_version,
        "orchestrator_version": ORCHESTRATOR_VERSION,
    }


def write_state(book_dir: Path, state: dict[str, Any]) -> Path:
    """Atomically write the state dict to <BOOK_DIR>/_system/orchestrator-state.json.

    Uses tmpfile + fsync + rename so concurrent readers always see a valid file.
    Returns the absolute path that was written.
    """
    p = state_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["ts_updated"] = _utc_now()

    # tmpfile in the same directory so rename is atomic on the same filesystem.
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".orchestrator-state.", suffix=".tmp", dir=p.parent
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, p)
    except Exception:
        # Clean up the tmpfile if something blew up before rename.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return p


def update_phase(
    book_dir: Path,
    *,
    phase: str,
    status: str,
    error: str | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Advance the state to the given phase + status. Idempotent on identical input.

    status is one of: running | completed | failed | halted | skipped.
    """
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase!r} (expected one of {PHASES})")
    if status not in ("running", "completed", "failed", "halted", "skipped"):
        raise ValueError(f"unknown status: {status!r}")

    state = read_state(book_dir)
    if state is None:
        raise RuntimeError(
            f"no orchestrator state file at {state_path(book_dir)} — "
            "call initial_state() + write_state() before update_phase()."
        )

    now = _utc_now()
    state["phase"] = phase
    state["phase_status"] = status
    phase_block = state["phases"].setdefault(phase, {"status": "pending"})
    if status == "running" and not phase_block.get("ts_started"):
        phase_block["ts_started"] = now
    if status in ("completed", "failed", "halted", "skipped"):
        phase_block["ts_completed"] = now
    phase_block["status"] = status
    if extras:
        phase_block.update(extras)

    if status == "completed":
        state["last_completed_phase"] = phase
        # Compute next_phase as the phase after this one (or None if last).
        try:
            idx = PHASES.index(phase)
            state["next_phase"] = PHASES[idx + 1] if idx + 1 < len(PHASES) else None
        except (ValueError, IndexError):
            state["next_phase"] = None

    if error is not None:
        state["last_error"] = {"phase": phase, "message": error, "ts": now}
    elif status == "completed":
        state["last_error"] = None

    write_state(book_dir, state)
    return state


def render_status(state: dict[str, Any]) -> str:
    """Human-readable rendering of the state dict for `--status`.

    Stable format so successive runs are diffable.
    """
    lines = []
    lines.append(f"book:                  {state.get('book_slug')}")
    lines.append(f"branch:                {state.get('branch')}")
    lines.append(f"current phase:         {state.get('phase')}  [{state.get('phase_status')}]")
    lines.append(f"last completed:        {state.get('last_completed_phase') or '(none)'}")
    lines.append(f"next:                  {state.get('next_phase') or '(none)'}")
    lines.append(f"orchestrator version:  {state.get('orchestrator_version')}")
    lines.append(f"challenger version:    {state.get('challenger_version')}")
    lines.append(f"started:               {state.get('ts_started')}")
    lines.append(f"updated:               {state.get('ts_updated')}")
    cost = state.get("cost", {})
    lines.append(
        f"cost so far:           Azure ${cost.get('azure_usd', 0):.2f}  "
        f"Anthropic ${cost.get('anthropic_usd', 0):.2f}"
    )
    err = state.get("last_error")
    if err:
        lines.append(f"last error:            [{err.get('phase')}] {err.get('message')}  @ {err.get('ts')}")
    lines.append("")
    lines.append("phase log:")
    for p in PHASES:
        block = state.get("phases", {}).get(p, {"status": "pending"})
        status = block.get("status", "pending")
        marker = {
            "pending":   "·",
            "running":   "›",
            "completed": "✓",
            "failed":    "✗",
            "halted":    "⏸",
            "skipped":   "—",
        }.get(status, "?")
        ts = block.get("ts_completed") or block.get("ts_started") or ""
        lines.append(f"  {marker} {p:<14} {status:<10} {ts}")
    return "\n".join(lines) + "\n"
