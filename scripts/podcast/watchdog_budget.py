#!/usr/bin/env python3
"""watchdog_budget.py — record a relaunch attempt and report whether budget remains.

WHY THIS EXISTS

  `watch_orchestrator.sh` counted its attempts in a shell variable, and
  `orchestrate_book.py` spawns a FRESH watchdog on every bare `--resume`. Each
  new watchdog started counting from 1, so the documented `--max-retries 20`
  ceiling never bound across respawns: one real run reached 201 attempts while
  every line reported "attempt N/20".

  The count therefore has to outlive the shell, which means it belongs in
  `orchestrator-state.json`. It is written through `_progress`, not with `jq`,
  so it keeps the tmpfile+fsync+rename discipline every other state write uses —
  a `jq '...' > file` would truncate the state file in place and lose it
  entirely if the process died mid-write.

USAGE

    python3 watchdog_budget.py <slug> --max 20

  Prints one line for the watchdog to log, e.g.
    attempt 3/20 on phase 0b
  and exits:
    0  — budget remains, relaunch
    3  — budget exhausted for this phase, do NOT relaunch
    2  — could not resolve the book or its state (advisory; caller proceeds)

  `--peek` reports without incrementing, for a status read.
  `--clear` forgets the current phase's count, for a phase that HALTED cleanly:
  a halt is progress to a human gate, not a failed attempt, and carrying the
  count forward made the next `--resume` after the human acted exit BUDGET
  EXHAUSTED before running anything.

The budget is PER PHASE and is cleared automatically the moment that phase
reaches `completed` (see `_progress._update_phase_locked`), so a book that
legitimately advances through all 29 phases never accumulates a count.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import find_content
from _progress import attempts_for, clear_attempts, read_state, record_attempt

EXIT_OK = 0
EXIT_UNRESOLVED = 2
EXIT_EXHAUSTED = 3


def main() -> int:
    ap = argparse.ArgumentParser(prog="watchdog_budget")
    ap.add_argument("slug")
    ap.add_argument("--max", type=int, default=20, help="attempts allowed per phase (0 disables the ceiling)")
    ap.add_argument("--peek", action="store_true", help="report without incrementing")
    ap.add_argument("--clear", action="store_true", help="forget the current phase's count (a clean halt)")
    args = ap.parse_args()

    found = find_content(args.slug)
    if not found:
        print(f"budget: cannot resolve book {args.slug!r} — proceeding without a ceiling", file=sys.stderr)
        return EXIT_UNRESOLVED
    book_dir = found[2]

    state = read_state(book_dir)
    if state is None:
        print(f"budget: no state file for {args.slug!r} — proceeding without a ceiling", file=sys.stderr)
        return EXIT_UNRESOLVED

    phase = state.get("phase") or "(unknown)"

    if args.clear:
        clear_attempts(book_dir, phase)
        print(f"attempt count cleared on phase {phase} (halted cleanly)")
        return EXIT_OK

    if args.peek:
        n = attempts_for(state, phase)
    else:
        n = record_attempt(book_dir, phase)

    ceiling = "unlimited" if args.max <= 0 else str(args.max)
    print(f"attempt {n}/{ceiling} on phase {phase}")

    # A ceiling of 0 means "no ceiling" — matches how the cost caps in
    # series-plan.md already spell disabled, so there is one convention.
    if args.max > 0 and n > args.max:
        print(
            f"budget: phase {phase!r} has been attempted {n} times without completing "
            f"(ceiling {args.max}) — refusing to relaunch.",
            file=sys.stderr,
        )
        return EXIT_EXHAUSTED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
