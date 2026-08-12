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
  * ETA from OBSERVED velocity, never from a fixed start time. The state file's
    ``ts_started`` is set once at intake and is routinely weeks stale by the time
    a book is mid-run — extrapolating from it produces a confidently wrong
    number. Instead a small checkpoint file tracks percent_complete across calls
    and estimates from the rate actually observed, self-correcting toward "later"
    on its own if the run stalls, and returning no estimate at all until there
    are two real checkpoints to compare.

Pure: reads state, returns a dict, renders a string. Writes only its own small
velocity checkpoint file. No LLM, no network — so it is safe to call from a
heartbeat as often as you like.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_status_subphase import chunk_fraction as _chunk_fraction  # noqa: E402
from _book_status_subphase import sessions_articulate_fraction as _sessions_articulate_fraction  # noqa: E402
from _paths import find_content  # noqa: E402
from _pending_work import open_items  # noqa: E402
from _phase_vocabulary import _PHASE_NAMES, _PHASE_WEIGHTS  # noqa: E402
from _progress import PHASES, read_state  # noqa: E402


def step_name(phase: str | None) -> str:
    """The human name for a phase id, falling back to the id when one is unmapped."""
    return _PHASE_NAMES.get(str(phase), str(phase))


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


def _fraction_done(phase: str, block: dict[str, Any], book_dir: Path | None = None) -> float:
    """How much of ONE phase is complete, 0.0-1.0, using sub-phase credit if recorded."""
    status = str(block.get("status") or "pending")
    # sessions-articulate is checked BEFORE the flag short-circuits below, not
    # after — unlike 0b/0d, whose "running" flag is trustworthy for the whole
    # phase and only needs a real number WHILE it is running, this phase's own
    # `completed` flag was once written after keeping 2 of 23 chapters (a driver
    # bug, fixed at the source, but the state files it already wrote are still on
    # disk). A ledger that disagrees with a `completed` flag is what actually
    # happened; a flag that agrees costs nothing extra to confirm.
    if status in _DONE_STATUSES:
        sessions_fraction = _sessions_articulate_fraction(phase, book_dir)
        return sessions_fraction if sessions_fraction is not None else 1.0
    if status != "running":
        return 0.0
    # The per-chapter loop is the only phase that publishes its own progress
    # directly into the state file.
    completed = block.get("completed_slugs")
    if isinstance(completed, list) and completed:
        total = len(completed) + len(block.get("failed_slugs") or [])
        current = block.get("current_chapter")
        if current:
            total += 1
        return min(0.95, len(completed) / total) if total else 0.0
    # 0b and 0d checkpoint per source-chunk on disk even though the state file
    # itself stays a flat "running" the whole time — read that instead of
    # guessing. (2026-08-06: the flat guess below starved the ETA of any real
    # signal on a multi-hour chunked phase, and it drifted to a wrong number
    # a day out — see _chunk_fraction.)
    chunk_fraction = _chunk_fraction(phase, book_dir)
    if chunk_fraction is not None:
        return chunk_fraction
    sessions_fraction = _sessions_articulate_fraction(phase, book_dir)
    if sessions_fraction is not None:
        # Capped here, not inside the helper: a `completed` flag that genuinely
        # earned it (kept == total) must reach the full 1.0 through the SAME
        # helper the `completed` branch above uses uncapped — capping inside the
        # helper would freeze a truly finished phase at 95% forever.
        return min(0.95, sessions_fraction)
    # A running phase with nothing else to go on counts as half — honest about
    # being underway without claiming knowledge the state file does not have.
    return 0.5


# Phases that do not wait on a machine — they wait on a person. `audio-ingest`
# sits until the human uploads to NotebookLM, generates the audio, and drops the
# .m4a files back. Extrapolating a machine rate across one of these produced the
# 2026-07-31 "eleven hours left" reading on a book that had ~two hours of compute
# and then an indefinite human pause; a rate measured from compute says nothing
# about how long someone takes to come back to their desk.
_HUMAN_GATED_PHASES = frozenset({"audio-ingest"})


def compute_progress(state: dict[str, Any], book_dir: Path | None = None) -> dict[str, Any]:
    """Per-phase status plus the weighted percentage. The single source of the number.

    ``book_dir`` is optional and used only to read real on-disk chunk progress
    for phases that have it (see ``_chunk_fraction``); every existing caller
    that passes state alone keeps its prior behavior unchanged.
    """
    blocks = state.get("phases") or {}
    # WHICH SEQUENCE THIS BOOK RUNS, from the book rather than from a constant.
    #
    # `PHASES` is the podcast orchestrator's twenty-nine, and for years it was
    # the only sequence there was. The Sessions lane runs five of its own and
    # shares none of them, so iterating the constant reported a finished lecture
    # series as 0% with twenty-nine steps left — every one of them a step it does
    # not run and never will.
    #
    # The constant still wins wherever it applies, and that matters: an
    # orchestrator book's state file lists only the phases it has REACHED, so
    # trusting its keys would shrink the denominator as the run progressed and
    # the percentage would climb for the wrong reason. The state's own order is
    # used only when it names a sequence the constant does not contain.
    order = PHASES if any(p in blocks for p in PHASES) or not blocks else tuple(blocks)
    rows: list[dict[str, Any]] = []
    earned = 0.0
    total = 0
    # Machine-only counterpart of earned/total: human-gated phases excluded, so
    # the ETA can be computed against work a rate actually predicts.
    machine_earned = 0.0
    machine_total = 0
    # Phases skipped because the book is MISCONFIGURED, not because the lane does
    # not apply. Both leave the denominator (a book that will never render slides
    # must still reach 100%), but only one of them means a deliverable is missing,
    # and conflating them let an empty book/ read as 95% complete on 2026-07-31.
    skipped_by_config: list[dict[str, str]] = []
    # The completed frontier: the furthest phase this book has actually finished.
    # Anything BEHIND it that is not itself finished was bypassed — an older
    # pipeline shape, a lane that does not apply (a NotebookLM book records no
    # audio-render), or a step the run simply never stamped. Those leave the
    # denominator, because counting them would report a shipped book as
    # permanently unfinished. They are not swallowed: any bypassed phase that
    # failed or halted is collected and surfaced on the card.
    # The frontier/bypass logic below assumes its order is MONOTONIC — that
    # reaching a later phase means every earlier one either finished or was
    # legitimately skipped. That is true of the orchestrator's PHASES, built
    # phase by phase in sequence, and false of a lane's own order: the Sessions
    # lane's `sessions-articulate` sits BEFORE `sessions-preface` in the
    # declared list but legitimately FINISHES after it (the introduction the
    # preface writes is apparatus articulation never touches). Applying the
    # bypass rule there silently DROPPED an in-progress `sessions-articulate`
    # from rows entirely the moment a later-listed step completed — not merely
    # undercounted, absent: missing from the denominator, from "remaining", and
    # from "Now" (2026-08-12). Scoped to the canonical sequence only; a lane's
    # own order counts every phase at its own real fraction, unconditionally.
    uses_canonical_order = order is PHASES
    frontier = (
        max(
            (i for i, p in enumerate(order) if str((blocks.get(p) or {}).get("status") or "") in _DONE_STATUSES),
            default=-1,
        )
        if uses_canonical_order
        # -1: "index < frontier" is then false for every index >= 0, so nothing
        # in a lane's own order is ever treated as bypassed.
        else -1
    )
    bypassed: list[dict[str, str]] = []
    for index, phase in enumerate(order):
        block = blocks.get(phase) or {}
        status = str(block.get("status") or "pending")
        if index < frontier and status not in _DONE_STATUSES:
            if status in ("failed", "halted"):
                bypassed.append({"phase": phase, "status": status})
            continue
        weight = _weight(phase)
        fraction = _fraction_done(phase, block, book_dir)
        # A skipped phase leaves the denominator entirely — a book that will never
        # render slides should still be able to reach 100%.
        if status == "skipped":
            if str(block.get("skipped_by") or "") == "config":
                skipped_by_config.append({"phase": phase, "reason": str(block.get("reason") or "")})
            continue
        total += weight
        earned += weight * fraction
        if phase not in _HUMAN_GATED_PHASES:
            machine_total += weight
            machine_earned += weight * fraction
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
    machine_pct = round(100 * machine_earned / machine_total, 1) if machine_total else pct
    # Done/remaining key on the FRACTION, not the status string. They agree for
    # every phase whose fraction comes from the flag alone (any _DONE_STATUSES
    # status IS 1.0, by the first line of `_fraction_done`) — the one case they
    # can disagree is exactly the bug this exists to close: a phase carrying a
    # `completed` flag that a real per-artifact count (chunk files, the Sessions
    # ledger) contradicts. Trusting the flag there is how "Left: 1 step" reported
    # a book with 21 of 23 chapters still unwritten as one step from done.
    done = [r for r in rows if r["fraction"] >= 1.0]
    remaining = [r for r in rows if r["fraction"] < 1.0]
    # "Now" comes from the row walk, not from the flat `state["phase"]` string,
    # whenever this book runs its OWN sequence rather than the orchestrator's.
    # `state["phase"]`/`phase_status` are kept live by the orchestrator's own
    # phase-transition code on every PHASES transition — correct to trust there.
    # A lane like Sessions has no such code: its scaffold step stamps those two
    # fields once and nothing later touches them, so trusting them here reported
    # a book mid-way through articulating its densest chapters as "Now: Writing
    # the introduction · completed" — the LAST thing the scaffold step did,
    # frozen, regardless of everything that ran after it (2026-08-12).
    if uses_canonical_order:
        current, current_status = state.get("phase"), state.get("phase_status")
    else:
        in_progress = next((r for r in remaining), None)
        if in_progress:
            current, current_status = in_progress["phase"], in_progress["status"]
        elif rows:
            current, current_status = rows[-1]["phase"], rows[-1]["status"]
        else:
            current, current_status = state.get("phase"), state.get("phase_status")
    return {
        "percent_complete": pct,
        "machine_percent_complete": machine_pct,
        "phases": rows,
        "done": [r["phase"] for r in done],
        "remaining": [r["phase"] for r in remaining],
        "human_gated_remaining": [r["phase"] for r in remaining if r["phase"] in _HUMAN_GATED_PHASES],
        "skipped_by_config": skipped_by_config,
        "bypassed_unresolved": bypassed,
        "current": current,
        "current_status": current_status,
        "last_error": state.get("last_error"),
    }


def _velocity_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "status-velocity.json"


_VELOCITY_WINDOW = 5  # trailing checkpoints kept — enough to smooth a noisy tick
_ETA_MAX_SECONDS = 30 * 86400  # beyond a month the estimate is noise, not a number


def _read_velocity(book_dir: Path) -> list[dict[str, Any]]:
    path = _velocity_path(book_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def estimate_eta(book_dir: Path, percent_complete: float, *, now: datetime | None = None) -> datetime | None:
    """A completion estimate from OBSERVED velocity, not a guess from a fixed start time.

    The state file's own ``ts_started`` is set once at intake and is frequently
    weeks stale by the time a book is mid-run (a book paused and resumed, or a
    direct re-run driver that never touches it) — extrapolating from it would
    produce a confidently wrong number. Instead this checkpoints percent_complete
    on every call where it has genuinely increased, and estimates from the
    trailing window of real checkpoints: work actually observed to happen, at the
    rate it actually happened. The first call on any run has nothing to compare
    against and returns ``None`` — an absent ETA is honest; a fabricated one from
    a single sample is not.

    Self-correcting for a stall: if percent stops advancing, the checkpoint stops
    advancing too, so every later call recomputes velocity over a widening span
    with no gain — the ETA recedes on its own rather than needing a reset.
    """
    now = now or datetime.now(timezone.utc)
    checkpoints = _read_velocity(book_dir)
    # Checkpoint on ANY change, not only an increase. Percent moves BACKWARDS
    # whenever a phase is retried (2026-07-31: 63.6% -> 56% on a slide re-run),
    # and recording only rises left a peak in the window the book had already
    # fallen back from — so the rate was computed against progress that no longer
    # existed and the projection stretched by hours. A regression also invalidates
    # everything before it as a velocity sample: drop the stale prefix and measure
    # forward from where the run actually is.
    if not checkpoints or checkpoints[-1]["pct"] != percent_complete:
        if checkpoints and checkpoints[-1]["pct"] > percent_complete:
            checkpoints = []  # regression — earlier samples describe a run that rewound
        checkpoints.append({"ts": now.isoformat(), "pct": percent_complete})
        checkpoints = checkpoints[-_VELOCITY_WINDOW:]
        try:
            _velocity_path(book_dir).parent.mkdir(parents=True, exist_ok=True)
            _velocity_path(book_dir).write_text(json.dumps(checkpoints), encoding="utf-8")
        except Exception:
            pass  # the estimate degrading gracefully matters more than the cache
    if len(checkpoints) < 2:
        return None
    try:
        first = datetime.fromisoformat(checkpoints[0]["ts"])
        elapsed = (now - first).total_seconds()
        gained = checkpoints[-1]["pct"] - checkpoints[0]["pct"]
    except Exception:
        return None
    if elapsed <= 0 or gained <= 0:
        return None
    remaining_seconds = (100 - percent_complete) / (gained / elapsed)
    if remaining_seconds <= 0 or remaining_seconds > _ETA_MAX_SECONDS:
        return None
    return now + timedelta(seconds=remaining_seconds)


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


def _title(book_dir: Path, slug: str) -> str:
    """The book's own title from meta.yml — Proper Case, never the slug, never caps.

    A standing rule: the title a human reads is the one printed on the book, not
    the folder name. Falls back to a de-slugged form only when meta.yml has none.
    """
    meta = Path(book_dir) / "meta.yml"
    if meta.exists():
        try:
            for line in meta.read_text(encoding="utf-8").splitlines():
                if line.startswith("title:"):
                    value = line.split(":", 1)[1].strip().strip("\"'")
                    if value:
                        return value
        except Exception:
            pass
    return slug.replace("-", " ").title()


def _to_est(dt: datetime) -> datetime:
    """Any timezone-aware instant, moved to US Eastern — the only zone this repo reports."""
    try:
        from zoneinfo import ZoneInfo

        return dt.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return dt


def _format_est(dt: datetime) -> str:
    """Bare wall clock in US Eastern 12-hour. Correct only for an instant that is TODAY."""
    return _to_est(dt).strftime("%-I:%M %p EST")


def _format_est_dated(dt: datetime, *, relative_to: datetime | None = None) -> str:
    """Wall clock, qualified by day when it does not fall on the same date as now.

    The bare form carries no date, so a completion estimate past midnight printed
    as e.g. "6:14 AM EST" beside a "Checked 6:49 PM EST" stamp and read as twelve
    hours in the PAST (2026-07-31). Any field that can land on another day — the
    ETA is the only one today — must go through this instead.
    """
    dt_est = _to_est(dt)
    now_est = _to_est(relative_to or datetime.now(timezone.utc))
    base = dt_est.strftime("%-I:%M %p EST")
    days = (dt_est.date() - now_est.date()).days
    if days == 0:
        return base
    if days == 1:
        return f"{base} tomorrow"
    if 2 <= days <= 6:
        return f"{base} {dt_est.strftime('%a')}"
    return f"{base} {dt_est.strftime('%b %-d')}"


def _est_now() -> str:
    """Wall clock in US Eastern, 12-hour — the only time format this repo reports."""
    return _format_est(datetime.now(timezone.utc))


def build_card(book_dir: Path) -> dict[str, Any]:
    """Everything the card shows, as data — so a caller can render it any way."""
    book_dir = Path(book_dir).resolve()
    state = read_state(book_dir) or {}
    progress = compute_progress(state, book_dir)
    # Estimate against MACHINE work only. Projecting a compute rate across a phase
    # that is waiting on a person answers a question the rate cannot answer.
    eta = estimate_eta(book_dir, progress["machine_percent_complete"])
    return {
        "slug": state.get("book_slug") or book_dir.name,
        "title": _title(book_dir, state.get("book_slug") or book_dir.name),
        "generated_at": _est_now(),
        "eta": _format_est_dated(eta) if eta else None,
        "spend_usd": _spend_usd(book_dir),
        "status": state.get("status"),
        "pending": open_items(state.get("book_slug") or book_dir.name),
        **progress,
    }


_CARD_WIDTH = 52  # inner width; narrow enough never to wrap in a chat panel
# Enough of the backlog to be actionable at a glance; the rest is one line away
# in the file. A card that scrolls stops being a card.
_PENDING_SHOWN = 5


def _row(label: str, value: str) -> str:
    """One card row, clipped so the frame can never be broken by a long value."""
    room = _CARD_WIDTH - 12  # frame(2) + padding(2) + label(8)
    value = value if len(value) <= room else value[: room - 1] + "…"
    return f"│ {label:<8}{value:<{room}} │"


def render_card(card: dict[str, Any], *, verbose: bool = False) -> str:
    """A compact framed card: title, progress bar, and four lines of state.

    Fixed width and box-drawn, because the value of a status card is that
    consecutive readings look identical except for what changed — a layout that
    reflows with its content makes you re-read it every time.
    """
    pct = card["percent_complete"]
    bar_width = _CARD_WIDTH - 10  # frame(2) + padding(2) + ' 100%'(6)
    filled = int(round(bar_width * pct / 100))
    bar = "█" * filled + "░" * (bar_width - filled)

    title = card.get("title") or card["slug"]
    remaining = [step_name(p) for p in card["remaining"]]
    left = f"{len(remaining)} steps · " + ", ".join(remaining[:3]) + ("…" if len(remaining) > 3 else "")

    top = "┌" + "─" * (_CARD_WIDTH - 2) + "┐"
    mid = "├" + "─" * (_CARD_WIDTH - 2) + "┤"
    bottom = "└" + "─" * (_CARD_WIDTH - 2) + "┘"

    lines = [
        top,
        f"│ {title[: _CARD_WIDTH - 4]:<{_CARD_WIDTH - 4}} │",
        f"│ {bar} {pct:>4.0f}% │",
        mid,
        _row("Now", f"{step_name(card['current'])} · {card['current_status']}"),
        _row("Left", left if remaining else "nothing — complete"),
        _row("Spend", f"${card['spend_usd']:.2f}" + ("  (flat-rate work not shown)" if not card["spend_usd"] else "")),
        _row("Checked", card["generated_at"]),
        _row("ETA", card["eta"] if card.get("eta") else "estimating (need 2 checks)"),
    ]
    # A phase waiting on a person is not a phase the ETA describes. Say so, or the
    # number reads as a finish time when it is only a "machine stops here" time.
    if card.get("human_gated_remaining"):
        gated = ", ".join(step_name(p) for p in card["human_gated_remaining"])
        lines.append(_row("", f"to next halt · then you: {gated}"))
    # A deliverable that never got built because the book is misconfigured. This
    # rides ABOVE the error row because it is the thing most likely to be missed:
    # the run reports success, the percentage climbs, and nothing was produced.
    if card.get("skipped_by_config"):
        missing = ", ".join(step_name(s["phase"]) for s in card["skipped_by_config"])
        lines.append(_row("Not run", f"{missing} — config"))
    if card.get("last_error"):
        lines.append(_row("Error", str(card["last_error"])))
    if card.get("bypassed_unresolved"):
        behind = ", ".join(f"{step_name(b['phase'])} ({b['status']})" for b in card["bypassed_unresolved"])
        lines.append(_row("Behind", behind))
    # The backlog. Progress answers "how far along"; this answers "what is still
    # owed" — work noticed in conversation that would otherwise live only there.
    pending = card.get("pending") or []
    if pending:
        lines.append(mid)
        lines.append(_row("Pending", f"{len(pending)} item(s)"))
        for item in pending[:_PENDING_SHOWN]:
            marker = "▸" if item.get("status") == "doing" else "·"
            lines.append(_row("", f"{marker} {item.get('title', '')}"))
        if len(pending) > _PENDING_SHOWN:
            lines.append(_row("", f"  +{len(pending) - _PENDING_SHOWN} more"))

    if verbose:
        lines.append(mid)
        # An emoji occupies TWO display columns while counting as ONE character, so
        # the step list is laid out directly rather than through the label field.
        name_width = _CARD_WIDTH - 7
        for row in card["phases"]:
            lines.append(f"│ {row['icon']} {step_name(row['phase'])[:name_width]:<{name_width}} │")
    lines.append(bottom)
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
