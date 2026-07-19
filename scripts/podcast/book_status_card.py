#!/usr/bin/env python3
"""book_status_card.py — one book's progress as a status card: done, left, % complete.

The repo could already answer "what phase is this book in" (the state file) and
"what does the fleet look like" (cross_book_dashboard). Neither answers the
question a human actually asks while a run is in flight: *how far along is it,
and what is still ahead?* That answer was being assembled by hand every time,
which makes it inconsistent and, worse, guessable — a percentage nobody can
reproduce is worse than no percentage.

This module computes it from the state file alone, deterministically:

  * WEIGHTED phases, not a phase count. The pipeline's phases are wildly uneven —
    a deterministic register step and a multi-hour per-chapter convergence loop
    are not each "one thirtieth". Weights below are relative wall-clock cost, so
    the number tracks felt progress rather than list position.
  * SUB-PHASE credit where the state file records it. The per-chapter loop knows
    how many chapters it has completed, so a book halfway through it reads as
    halfway through it, not as 0% until the phase flips.
  * SKIPPED phases leave the denominator. A book with no slide decks is not
    permanently short of 100% for work it was never going to do.

Pure: reads state, returns a dict, renders a string. No LLM, no mutation, no
network — so it is safe to call from a heartbeat as often as you like.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import find_content  # noqa: E402
from _progress import PHASES, read_state  # noqa: E402

# Relative wall-clock weight per phase. A phase absent here weighs 1. These are
# deliberately coarse — the point is that the long phases dominate the number the
# way they dominate the wait, not that any single figure is precise.
_PHASE_WEIGHTS: dict[str, int] = {
    "pre-flight": 1,
    "branch": 1,
    "scaffold": 1,
    "0a": 6,
    "0b": 8,
    "0c": 4,
    "0ci": 4,
    "0d": 8,
    "0e": 8,
    "0literary": 4,
    "06a": 1,
    "0f": 1,
    "0g": 1,
    "per-chapter": 40,
    "per-chapter-optimize": 8,
    "per-chapter-slides": 12,
    "audio-script": 8,
    "audio-render": 8,
    "finalize": 2,
    "audio-ingest": 4,
    "0book-design": 3,
    "0book-compose": 20,
    "0book-illustrate": 6,
    "0book-slide-import": 4,
    "0book-render": 3,
    "publish": 1,
    "trainer": 2,
    "merge": 1,
    "done": 1,
}

_DONE_STATUSES = frozenset({"completed", "skipped"})
_ICONS = {
    "completed": "✅",
    "skipped": "⏭️",
    "running": "🔄",
    "failed": "🔴",
    "halted": "⏸️",
    "pending": "⏳",
}


def _weight(phase: str) -> int:
    return _PHASE_WEIGHTS.get(phase, 1)


def _fraction_done(phase: str, block: dict[str, Any]) -> float:
    """How much of ONE phase is complete, 0.0-1.0, using sub-phase credit if recorded."""
    status = str(block.get("status") or "pending")
    if status in _DONE_STATUSES:
        return 1.0
    if status != "running":
        return 0.0
    # The per-chapter loop is the only phase that publishes its own progress.
    completed = block.get("completed_slugs")
    if isinstance(completed, list) and completed:
        total = len(completed) + len(block.get("failed_slugs") or [])
        current = block.get("current_chapter")
        if current:
            total += 1
        return min(0.95, len(completed) / total) if total else 0.0
    # A running phase with nothing else to go on counts as half — honest about
    # being underway without claiming knowledge the state file does not have.
    return 0.5


def compute_progress(state: dict[str, Any]) -> dict[str, Any]:
    """Per-phase status plus the weighted percentage. The single source of the number."""
    blocks = state.get("phases") or {}
    rows: list[dict[str, Any]] = []
    earned = 0.0
    total = 0
    # The completed frontier: the furthest phase this book has actually finished.
    # Anything BEHIND it that is not itself finished was bypassed — an older
    # pipeline shape, a lane that does not apply (a NotebookLM book records no
    # audio-render), or a step the run simply never stamped. Those leave the
    # denominator, because counting them would report a shipped book as
    # permanently unfinished. They are not swallowed: any bypassed phase that
    # failed or halted is collected and surfaced on the card.
    frontier = max(
        (i for i, p in enumerate(PHASES) if str((blocks.get(p) or {}).get("status") or "") in _DONE_STATUSES),
        default=-1,
    )
    bypassed: list[dict[str, str]] = []
    for index, phase in enumerate(PHASES):
        block = blocks.get(phase) or {}
        status = str(block.get("status") or "pending")
        if index < frontier and status not in _DONE_STATUSES:
            if status in ("failed", "halted"):
                bypassed.append({"phase": phase, "status": status})
            continue
        weight = _weight(phase)
        fraction = _fraction_done(phase, block)
        # A skipped phase leaves the denominator entirely — a book that will never
        # render slides should still be able to reach 100%.
        if status == "skipped":
            continue
        total += weight
        earned += weight * fraction
        rows.append(
            {
                "phase": phase,
                "status": status,
                "icon": _ICONS.get(status, "⏳"),
                "fraction": round(fraction, 2),
                "note": block.get("note") or block.get("error") or "",
            }
        )
    pct = round(100 * earned / total, 1) if total else 0.0
    done = [r for r in rows if r["status"] in _DONE_STATUSES]
    remaining = [r for r in rows if r["status"] not in _DONE_STATUSES]
    return {
        "percent_complete": pct,
        "phases": rows,
        "done": [r["phase"] for r in done],
        "remaining": [r["phase"] for r in remaining],
        "bypassed_unresolved": bypassed,
        "current": state.get("phase"),
        "current_status": state.get("phase_status"),
        "last_error": state.get("last_error"),
    }


def _spend_usd(book_dir: Path) -> float:
    """Real money only. Flat-rate subscription work is not a cost and is never shown."""
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return 0.0
    total = 0.0
    try:
        for raw in ledger.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                total += float(json.loads(raw).get("cost_usd") or 0)
            except Exception:
                continue
    except Exception:
        return 0.0
    return round(total, 2)


def _est_now() -> str:
    """Wall clock in US Eastern, 12-hour — the only time format this repo reports."""
    try:
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now = datetime.now(timezone.utc)
    return now.strftime("%-I:%M %p EST")


def build_card(book_dir: Path) -> dict[str, Any]:
    """Everything the card shows, as data — so a caller can render it any way."""
    book_dir = Path(book_dir).resolve()
    state = read_state(book_dir) or {}
    progress = compute_progress(state)
    return {
        "slug": state.get("book_slug") or book_dir.name,
        "generated_at": _est_now(),
        "spend_usd": _spend_usd(book_dir),
        "status": state.get("status"),
        **progress,
    }


def render_card(card: dict[str, Any], *, verbose: bool = False) -> str:
    """The card as markdown: a metrics table, then what is done and what is left."""
    bar_width = 24
    filled = int(round(bar_width * card["percent_complete"] / 100))
    bar = "█" * filled + "·" * (bar_width - filled)
    lines = [
        "─" * 68,
        f"### {card['slug']} — {card['percent_complete']}% complete",
        "",
        f"`{bar}`",
        "",
        "| | |",
        "|---|---|",
        f"| Progress | {card['percent_complete']}% ({len(card['done'])} of "
        f"{len(card['done']) + len(card['remaining'])} steps) |",
        f"| Current step | {card['current']} — {card['current_status']} |",
        f"| Steps left | {len(card['remaining'])} |",
        f"| Real spend | ${card['spend_usd']:.2f} |",
        f"| Checked | {card['generated_at']} |",
    ]
    if card.get("last_error"):
        lines.append(f"| Last error | {str(card['last_error'])[:80]} |")
    if card.get("bypassed_unresolved"):
        left_behind = ", ".join(f"{b['phase']} ({b['status']})" for b in card["bypassed_unresolved"][:3])
        lines.append(f"| Left behind | {left_behind} |")
    lines.append("")
    if verbose:
        lines.append("| Step | | |")
        lines.append("|---|---|---|")
        for row in card["phases"]:
            lines.append(f"| {row['icon']} | {row['phase']} | {row['status']} |")
    else:
        remaining = card["remaining"]
        lines.append(f"**Left:** {', '.join(remaining[:6])}" + (" …" if len(remaining) > 6 else ""))
    lines.append("─" * 68)
    return "\n".join(lines)


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv
    if not argv:
        print("usage: book_status_card.py <book-slug|BOOK_DIR> [--json] [--verbose]", file=sys.stderr)
        return 2
    target = Path(argv[0])
    if target.exists():
        book_dir: Path | None = target
    else:
        found = find_content(argv[0])
        book_dir = found[2] if found else None
    if book_dir is None or not Path(book_dir).exists():
        print(f"no book found for {argv[0]!r}", file=sys.stderr)
        return 1
    card = build_card(Path(book_dir))
    print(json.dumps(card, ensure_ascii=False, indent=2) if as_json else render_card(card, verbose=verbose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
