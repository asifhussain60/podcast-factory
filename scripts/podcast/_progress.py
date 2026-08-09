#!/usr/bin/env python3
"""_progress.py — atomic state-file writer for orchestrate_book.py.

The state file at `<BOOK_DIR>/_system/orchestrator-state.json` is the
**single source of truth** for the autonomous orchestrator. Per the v2
spec (docs/architecture/index.html#phases), there is no committed
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
      "cost": { "azure_usd": 0.0, "anthropic_usd": 0.0, "slide_deck_usd": 0.0 },
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
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure scripts/podcast/ is importable when this module is loaded from within
# a package directory (mirrors _authoring/_core.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))

# DR-005 re-exports — the run-log block moved verbatim to _runlog.py when it
# pushed this module past the 600-line limit; the names stay importable here.
# One line each: the parenthesised form costs a dozen lines and says no more.
from _runlog import RUN_LOG_RETENTION as RUN_LOG_RETENTION
from _runlog import RUN_LOG_TAIL_CHARS as RUN_LOG_TAIL_CHARS
from _runlog import current_run_id as current_run_id
from _runlog import init_run_log as init_run_log
from _runlog import log_event as log_event
from _runlog import mint_run_id as mint_run_id
from _runlog import read_run_events as read_run_events
from _runlog import reset_run_log as reset_run_log
from _runlog import run_log_enabled as run_log_enabled
from _runlog import run_log_path as run_log_path
from _runlog import runs_dir as runs_dir
from _runlog import tail as tail
from _runlog import write_failure_dump as write_failure_dump

ORCHESTRATOR_VERSION = "1.2"  # 2026-05-19: chunked 0b/0c + unit_mode (chapter|section|auto) + --retry-phase
SCHEMA_VERSION = 1

# Phase identifiers in canonical order. THIS TUPLE IS THE SINGLE SOURCE OF TRUTH
# for the orchestrator phase sequence — orchestrate_book.CANONICAL_PHASES and the
# resume dispatcher both import it (do not re-declare a parallel list anywhere).
# Every phase id passed to update_phase() MUST appear here or it raises ValueError.
PHASES = (
    "pre-flight",
    "branch",
    "scaffold",
    "0a",  # Azure OCR + Translation (deterministic)
    "0b",  # English refinement (LLM)
    "0c",  # Arabic phonetic pass (LLM)
    "0ci",  # Book intelligence: gap analysis + corpus cross-reference (LLM); Islamic-content halt
    "0d",  # Chapter design (LLM)
    "0e",  # Enrichment (LLM)
    "0literary",  # 08b literary transformation (Gemini); after enrichment, emitted by initial_driver
    "06a",  # Wave I — source review gate (human approval before series plan)
    "0f",  # Series plan halt (deterministic write + human gate)
    "0g",  # Register series (deterministic)
    "per-chapter",  # iterated across the chapter list on --resume
    "per-chapter-optimize",  # Wave I — Sonnet arc/format check per chapter
    "per-chapter-slides",  # optional; gated by series.enable_slide_decks. Per-chapter slide-deck authoring + slide-deck-challenger convergence. Skipped (status="skipped") when flag is false.
    "audio-script",  # Audio Engine v2 — per-chapter dialogue-script authorship + pre-synthesis gate convergence (API engines only; skipped for notebooklm)
    "audio-render",  # Audio Engine v2 — H1 spend halt (exact credit estimate) then ElevenLabs render into canonical m4a layout (API engines only; skipped for notebooklm)
    "finalize",  # G1-G7 quality gates + human review halt — podcast-only; book branch has not run yet
    "audio-ingest",  # NotebookLM path — self-correcting normalize + Azure-transcribe of dropped m4a (skipped for API/ElevenLabs books); halts cleanly until audio is dropped, then re-enters idempotently on --resume
    "0book-design",  # PDF path — book-craft re-segmentation -> book/book-toc.json (gated by series.enable_book_branch; runs post-finalize so book is built from reviewed podcast content)
    "0book-compose",  # PDF path — whole-book revoice -> book/book.md (modern author voice, Arabic script + English)
    "0book-illustrate",  # PDF path — teaching diagrams injected -> book/book-illustrated.md
    "0book-slide-import",  # PDF path — NotebookLM-exported deck PDFs (slide-decks/chNN-*.pdf) -> LLM anchor manifests -> book/book-slides.md; HALTS when framed chapters lack dropped PDFs (.SKIP exempts)
    "0book-render",  # PDF path — book-slides.md (or book-illustrated.md / book.md) -> book.pdf (Playwright); non-blocking on the podcast ship
    "publish",  # copy drafts → published/ catalog (publish_driver)
    "trainer",
    "merge",
    "done",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Stale-resume threshold. A phase_status="running" older than this almost
# certainly belongs to a crashed/killed orchestrator (no live process updates
# its state on resume — the book lock guards against a genuinely concurrent
# run). Generous on purpose: legitimate in-process phases never reach --resume.
STALE_RUNNING_SEC = 900


def is_phase_stale(state: dict[str, Any], max_age_sec: int = STALE_RUNNING_SEC) -> bool:
    """True when phase_status is 'running' but ts_updated is older than max_age_sec.

    Used by the resume path to auto-recover the documented orchestrator-resume
    bug: an unclean shutdown freezes state at 'running', which the early-phase
    handlers refuse to re-enter. Detecting staleness lets us downgrade to
    'failed' so the existing per-phase resume handlers pick it up — the same
    recovery the shell watchdog performs via --retry-phase.
    """
    if state.get("phase_status") != "running":
        return False
    ts = state.get("ts_updated") or ""
    try:
        # Stored as "...Z"; treat as UTC.
        updated = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # Unparseable timestamp on a 'running' state → treat as stale.
        return True
    age = (datetime.now(timezone.utc) - updated).total_seconds()
    return age > max_age_sec


def state_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "orchestrator-state.json"


# In-process guard for the read-modify-write cycle on orchestrator-state.json.
#
# `write_state` is already atomic at the filesystem level (temp file + rename),
# which is enough while one thread owns the state. It is NOT enough once a phase
# fans out: every writer does read_state() -> mutate -> write_state(), and two
# workers interleaving on that sequence means the later write is computed from a
# snapshot taken before the earlier one landed, so the earlier worker's result is
# silently dropped. The file is never corrupt — it is just missing a verdict,
# which is worse, because nothing reports an error.
#
# Re-entrant: update_phase() may be called from inside a caller that already
# holds the lock. Guards THIS process only; cross-process exclusion is the job of
# the fcntl book lock in orchestrate_book.py.
_STATE_LOCK = threading.RLock()


def state_transaction() -> threading.RLock:
    """Hold this around any read_state -> mutate -> write_state sequence.

    Used as a context manager::

        with state_transaction():
            state = read_state(book_dir) or {}
            state["..."] = ...
            write_state(book_dir, state)

    Mandatory for any code path that can run in a worker thread.
    """
    return _STATE_LOCK


def read_state(book_dir: Path) -> dict[str, Any] | None:
    """Return the current state dict or None if no state file exists."""
    p = state_path(book_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


UNATTENDED_KEY = "unattended"

#: Per-phase relaunch counts, keyed by phase id. Lives in the state file rather
#: than in the watchdog's shell, for the reason the watchdog could not solve on
#: its own: `watch_orchestrator.sh` counts attempts in a local variable, and
#: `orchestrate_book.py` spawns a FRESH watchdog on every bare `--resume`. Each
#: new watchdog therefore started counting from 1, so the documented
#: "--max-retries 20" ceiling never bound across respawns. One real run
#: (`orchestrator-the-master-and-the-disciple.log`) reached 201 attempts while
#: every one of them reported itself as "attempt N/20".
#:
#: A count survives a respawn because it is on disk, and is cleared the moment
#: the phase actually reaches `completed` (see `_update_phase_locked`) — so the
#: budget bounds *failure to progress*, never total work. A book that legitimately
#: advances through all 29 phases never accumulates a count at all.
ATTEMPTS_KEY = "phase_attempts"


def attempts_for(state: dict[str, Any], phase: str) -> int:
    """How many times `phase` has been attempted without completing."""
    return int((state.get(ATTEMPTS_KEY) or {}).get(phase, 0))


def record_attempt(book_dir: Path, phase: str) -> int:
    """Increment and persist `phase`'s attempt count. Returns the new count.

    Called by the watchdog immediately before each relaunch, so the count
    reflects attempts actually made even if the orchestrator dies without ever
    writing state itself — which is the exact case the shell counter lost.
    """
    with _STATE_LOCK:
        state = read_state(book_dir)
        if state is None:
            return 0
        counts = dict(state.get(ATTEMPTS_KEY) or {})
        counts[phase] = int(counts.get(phase, 0)) + 1
        state[ATTEMPTS_KEY] = counts
        write_state(book_dir, state)
        return counts[phase]


def clear_attempts(book_dir: Path, phase: str) -> None:
    """Forget `phase`'s attempt count — it made progress, so the budget resets."""
    with _STATE_LOCK:
        state = read_state(book_dir)
        if state is None:
            return
        counts = dict(state.get(ATTEMPTS_KEY) or {})
        if counts.pop(phase, None) is not None:
            state[ATTEMPTS_KEY] = counts
            write_state(book_dir, state)


def unattended_run(book_dir: Path) -> bool:
    """True when this book was launched with ``--unattended``.

    A property of the RUN, not of the book, so it lives in the state file rather
    than series-config.yaml — and it persists there precisely because the
    watchdog re-invokes ``--resume`` in a fresh process that never saw the flag.

    It clears the human-approval gates that exist to pace an attended run (the
    06a source review). It does NOT clear a halt that waits on an ARTIFACT only a
    human can supply — dropped audio, curated visuals — because no amount of
    authorization makes a missing file appear.
    """
    state = read_state(book_dir) or {}
    return bool(state.get(UNATTENDED_KEY))


def initial_state(book_slug: str, category: str, *, content_profile: str | None = None) -> dict[str, Any]:
    """Build the initial state dict for a new orchestrator run.

    ``content_profile`` (when known) selects the branch bucket; otherwise the
    branch bucket falls back to the legacy ``category`` map — symmetric with how
    the content folder is resolved at scaffold time.
    """
    now = _utc_now()
    # Best-effort challenger version stamp.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _rules import CHALLENGER_VERSION as _cv  # type: ignore

        challenger_version = _cv
    except Exception:
        challenger_version = "unknown"

    # Branch is <Bucket>/<slug> — bucket-grouped per content profile (2026-06-07).
    # See _branching.py.
    from _branching import branch_name as _branch_name

    return {
        "schema_version": SCHEMA_VERSION,
        "book_slug": book_slug,
        "category": category,
        "branch": _branch_name(category, book_slug, profile=content_profile),
        # Publication status (2026-06-04): draft|published|archived. Replaces the
        # drafts/published FOLDER split — publish_to_library.py flips this to
        # 'published' after gates pass. Default draft keeps un-shipped content
        # out of the audience catalog.
        "status": "draft",
        "phase": "pre-flight",
        "phase_status": "running",
        "last_completed_phase": None,
        "next_phase": "branch",
        "last_error": None,
        "phases": {p: {"status": "pending"} for p in PHASES},
        # AU-S3-001 fix: `slide_deck_usd` carries Phase 11b spend separately so
        # the orchestrator's cost view can break out slide-deck cost. State
        # files written before this field was added remain readable — readers
        # MUST use `.get("slide_deck_usd", 0.0)` for backward compatibility.
        # The authoritative cost source is still `<book>/_system/cost-ledger.jsonl`
        # (summed by `orchestrate_book.py:book_cost_usd()`); this dict is a
        # convenience surface for `--status` rendering.
        "cost": {"azure_usd": 0.0, "anthropic_usd": 0.0, "slide_deck_usd": 0.0},
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
    # Don't mutate the caller's dict — stamp a copy. (A shallow copy is enough:
    # we only replace the top-level ts_updated key, never nested values.)
    state = {**state, "ts_updated": _utc_now()}

    # tmpfile in the same directory so rename is atomic on the same filesystem.
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".orchestrator-state.", suffix=".tmp", dir=p.parent)
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

    with _STATE_LOCK:
        return _update_phase_locked(book_dir, phase=phase, status=status, error=error, extras=extras)


def _previous_completed(state: dict[str, Any], phase: str) -> str | None:
    """The last phase before `phase` that this book actually completed, or None.

    Used to walk `last_completed_phase` back when a phase's own review fails it, so the
    run points at the phase that needs fixing rather than at the one after it.
    """
    try:
        idx = PHASES.index(phase)
    except ValueError:
        return state.get("last_completed_phase")
    blocks = state.get("phases") or {}
    for earlier in reversed(PHASES[:idx]):
        blk = blocks.get(earlier)
        if isinstance(blk, dict) and blk.get("status") == "completed":
            return earlier
    return None


def _phase_review_for(book_dir: Path, phase: str, status: str) -> dict[str, Any] | None:
    """Review `phase` if it just completed and declares gates. Never raises.

    Returns the report, or None when there was nothing to review. Fully guarded for the
    same reason the reviewer's own gates are: a review is an OBSERVER, and a fault in
    the observing must not decide the fate of the phase it was watching. A crash here
    therefore yields None, which means the phase completes exactly as it did before this
    layer existed.

    `blocking_fail` is left set on the returned report ONLY when blocking is enabled, so
    the caller has one thing to test and the escape hatch cannot be half-applied.
    """
    if status != "completed":
        return None
    try:
        from _phase_review import blocking_enabled, phase_has_gates, review_phase

        if not phase_has_gates(phase):
            return None
        report = review_phase(book_dir, phase)
        if report.get("blocking_fail") and not blocking_enabled():
            report = {**report, "blocking_fail": None, "blocking_suppressed": True}
        return report
    except Exception:
        return None


def _update_phase_locked(
    book_dir: Path,
    *,
    phase: str,
    status: str,
    error: str | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """update_phase's body, with the state lock already held by the caller."""
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
        # The phase made real progress, so its relaunch budget resets — the
        # ceiling bounds failure-to-progress, not total work (see ATTEMPTS_KEY).
        # Mutated in place rather than via `clear_attempts` so this shares the
        # single `write_state` below instead of writing the file twice.
        _counts = state.get(ATTEMPTS_KEY)
        if isinstance(_counts, dict) and phase in _counts:
            _counts.pop(phase, None)

    if error is not None:
        state["last_error"] = {"phase": phase, "message": error, "ts": now}
    elif status == "completed":
        state["last_error"] = None

    # Run correlation (2026-07-31): stamp the run id into the checkpoint so
    # state.json and the timeline under _workspace/runs/ share one key. Lazily
    # mints a run id if nothing initialised one — a phase transition is proof a
    # run is under way, so there is no ordering requirement on main().
    run_id = current_run_id() or init_run_log(book_dir, slug=state.get("book_slug"))
    if run_id:
        state["run_id"] = run_id

    write_state(book_dir, state)

    # Phase review (2026-08-08; able to BLOCK since 2026-08-09). Hooked HERE, at the
    # single point every phase completion passes through, rather than at each driver's
    # own `update_phase(..., status="completed")` call site. That is deliberate: the
    # recurring defect in this repo is a gate that reports clean over a rule it never
    # ran, and a per-driver hook is one a new phase can be added without. From here it
    # cannot be forgotten.
    #
    # It runs AFTER the state is written, and that ordering is load-bearing: the gates
    # read the book's state from disk, and the extras of THIS call — `completed_slugs`
    # for the per-chapter lane, the publication status for publish — are how a phase
    # reports what it did. Reviewing before the write asked the gates about the previous
    # call's state and made them report a phase short of work it had just recorded.
    #
    # A blocking failure then rewrites the phase as failed. Only gates in
    # `BLOCKING_GATES` can do that, only when blocking is enabled, and the result is an
    # ordinary phase failure: `--resume <slug> --retry-phase <phase>` resets it and
    # everything downstream, so a gate can delay a book but never strand one.
    _review = _phase_review_for(book_dir, phase, status)
    if _review is not None:
        _blocking = _review.get("blocking_fail")
        if _blocking:
            status = "failed"
            error = f"phase review: {_blocking}"
            state["phase_status"] = status
            phase_block["status"] = status
            state["last_error"] = {"phase": phase, "message": error, "ts": now}
            # Undo the advancement the completed path had just recorded: a phase whose
            # own review says it did not do its job must not leave the run pointing at
            # the next one, or a resume walks straight past the problem.
            state["last_completed_phase"] = _previous_completed(state, phase)
            state["next_phase"] = phase
        phase_block["review"] = {
            "verdict": _review["verdict"],
            "failed": _review["counts"]["failed"],
            "crashed": _review["counts"]["crashed"],
            "total": _review["counts"]["total"],
            "blocking_fail": _review.get("blocking_fail"),
        }
        write_state(book_dir, state)

    # Timeline + failure dump. Both are internally guarded: observability must
    # never turn a working phase into a failed one.
    log_event(
        f"phase.{status}",
        book_dir=book_dir,
        level="error" if status == "failed" else "info",
        phase=phase,
        slug=state.get("book_slug"),
        msg=error or "",
    )
    if status in ("failed", "halted"):
        write_failure_dump(book_dir, state)
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
    azure_usd = cost.get("azure_usd", 0.0)
    anthropic_usd = cost.get("anthropic_usd", 0.0)
    # AU-S3-001 fix: pull slide-deck spend with `.get` default so state files
    # written before the field existed (no `slide_deck_usd` key) still render.
    slide_deck_usd = cost.get("slide_deck_usd", 0.0)
    total_usd = azure_usd + anthropic_usd + slide_deck_usd
    lines.append(
        f"cost so far:           Azure ${azure_usd:.2f}  "
        f"Anthropic ${anthropic_usd:.2f}  "
        f"Slide-deck ${slide_deck_usd:.2f}  "
        f"(total ${total_usd:.2f})"
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
            "pending": "·",
            "running": "›",
            "completed": "✓",
            "failed": "✗",
            "halted": "⏸",
            "skipped": "—",
        }.get(status, "?")
        ts = block.get("ts_completed") or block.get("ts_started") or ""
        lines.append(f"  {marker} {p:<14} {status:<10} {ts}")
    return "\n".join(lines) + "\n"
