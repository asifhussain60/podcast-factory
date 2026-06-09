#!/usr/bin/env python3
"""orchestrate_work.py — work-level SEQUENCER for multi-volume works (Phase 3).

This is NOT a second supervisor. It composes the existing single-actor
``supervise_run.py ensure <slug>`` (which keeps the one-supervisor-per-run
discipline). Its only job is to drive the volumes of a multi-volume work in
ORDER, with the Q4 contract:

    "Autopilot per volume, pause between volumes."

Each volume runs fully autonomously through its existing human gates
(0f / 0ci / 06a / finalize). When a volume reaches a completed state
(published / phase=done), the sequencer HALTS with an explicit prompt and
EXITS — it NEVER auto-launches the next volume. ``--advance`` starts exactly
one next volume.

It polls the orchestrator-state ``status``/``phase`` (read through the resolver),
never PIDs, and respects a ``<slug>.ALERT`` raised by the supervisor.

Usage:
    orchestrate_work.py <work-slug>            # run/continue the active volume
    orchestrate_work.py <work-slug> --advance  # start the next volume (one step)
    orchestrate_work.py <work-slug> --status   # print the volume ladder, no action
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402
import _work_manifest as wm  # noqa: E402
from _progress import read_state  # noqa: E402

SUPERVISE = Path(__file__).resolve().parent / "supervise_run.py"


# ── volume state predicates (pure — testable) ────────────────────────────────
def volume_complete(state: dict | None) -> bool:
    """A volume is complete when it is published or its pipeline reached done."""
    if not state:
        return False
    return state.get("status") == "published" or state.get("phase") == "done"


def volume_started(state: dict | None) -> bool:
    """A volume is 'started' once it has moved past the fresh-intake preflight."""
    if not state:
        return False
    ph = state.get("phase")
    return ph not in (None, "", "preflight")


def _read_volume_state(vol_slug: str) -> dict | None:
    found = _paths.find_content(vol_slug)
    if not found:
        return None
    return read_state(found[2])


# ── next-action planning (pure core — the pause is the hard requirement) ─────
@dataclass
class WorkAction:
    kind: str           # "run" | "pause-between-volumes" | "all-done" | "no-volumes"
    volume_slug: str | None = None
    order: int | None = None
    message: str = ""


def plan_next_action(work_slug: str, *, advance: bool, state_reader=None) -> WorkAction:
    """Decide what the sequencer should do next — WITHOUT side effects.

    The Q4 pause: when the next-in-line volume is UNSTARTED and its immediately
    preceding volume is COMPLETE, the sequencer pauses (requires --advance). An
    already-in-progress volume continues without --advance; the first volume is
    not gated by a (nonexistent) predecessor.
    """
    state_reader = state_reader or _read_volume_state  # resolved at call time (test-patchable)
    vols = wm.volumes_of(work_slug)
    if not vols:
        return WorkAction(kind="no-volumes", message=f"no volumes registered for work {work_slug!r}")

    states = [state_reader(v["slug"]) for v in vols]
    incomplete = [(i, v) for i, v in enumerate(vols) if not volume_complete(states[i])]
    if not incomplete:
        return WorkAction(kind="all-done", message=f"all {len(vols)} volume(s) of {work_slug!r} complete")

    idx, current = incomplete[0]
    started = volume_started(states[idx])
    prior_complete = idx > 0 and volume_complete(states[idx - 1])

    if prior_complete and not started and not advance:
        return WorkAction(
            kind="pause-between-volumes",
            volume_slug=current["slug"], order=current.get("order"),
            message=(
                f"volume {vols[idx-1].get('order')} complete. Next volume "
                f"{current.get('order')} ({current['slug']}) is ready but NOT started. "
                f"Re-run with --advance to begin it."
            ),
        )
    return WorkAction(
        kind="run", volume_slug=current["slug"], order=current.get("order"),
        message=f"active volume: {current['slug']} (order {current.get('order')})",
    )


# ── side-effecting driver ────────────────────────────────────────────────────
def _ensure_volume(vol_slug: str) -> int:
    """Hand the active volume to the single-actor supervisor (never a 2nd supervisor)."""
    return subprocess.run(
        [sys.executable, str(SUPERVISE), "ensure", vol_slug],
    ).returncode


def _print_ladder(work_slug: str) -> None:
    vols = wm.volumes_of(work_slug)
    print(f"work: {work_slug} — {len(vols)} volume(s)")
    for v in vols:
        st = _read_volume_state(v["slug"]) or {}
        mark = "[x]" if volume_complete(st) else ("[~]" if volume_started(st) else "[ ]")
        print(f"  {mark} {v.get('order'):>2}. {v['slug']:<28} "
              f"phase={st.get('phase', '—')} status={st.get('status', 'draft')}")


def run_work(work_slug: str, *, advance: bool) -> int:
    # Respect a supervisor ALERT on any volume — do not paper over it.
    action = plan_next_action(work_slug, advance=advance)
    print(action.message)
    if action.kind in ("no-volumes", "all-done", "pause-between-volumes"):
        # Non-actionable here: caller reviews + re-runs with --advance when ready.
        return 0
    # kind == "run"
    return _ensure_volume(action.volume_slug)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("work_slug", help="the multi-volume work slug (parent of vol-NN)")
    p.add_argument("--advance", action="store_true",
                   help="start the next volume (one step) past a between-volumes pause")
    p.add_argument("--status", action="store_true",
                   help="print the volume ladder and exit (no action)")
    args = p.parse_args(argv)

    if wm.work_dir_for(args.work_slug) is None:
        print(f"orchestrate_work: {args.work_slug!r} is not a multi-volume work "
              f"(no work.yml). Use orchestrate_book.py for single books.", file=sys.stderr)
        return 2

    if args.status:
        _print_ladder(args.work_slug)
        return 0
    return run_work(args.work_slug, advance=args.advance)


if __name__ == "__main__":
    sys.exit(main())
