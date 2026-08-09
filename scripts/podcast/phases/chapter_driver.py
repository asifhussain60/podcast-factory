"""phases/chapter_driver.py — _drive_per_chapter_and_after.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Drives the per-chapter convergence loop, Phase 0g, slide decks, and the
finalize halt. Called by resume_dispatcher after Phase 0f approval.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _chapter_breaker import BreakerTripped, ChapterBreaker, failure_signature
from _chapter_cost_caps import BookCeiling, read_caps
from _convergence import ChapterOutcome, render_outcome
from _progress import read_state, update_phase
from _subprocess import err as _err
from _subprocess import info as _info

from phases.per_chapter import per_chapter_pass
from phases.preflight import _sweep_orphan_episode_drafts
from phases.preflight_chapter import smoke_check_book
from phases.scaffold import phase_git_commit
from phases.series_plan import (
    _book_cost_so_far,
    _chapter_cost_so_far,
)
from phases.slide_cohort import is_bad_slide_outcome

# Moved to phases/slide_cohort.py with the rest of Phase 11b (2026-07-31).
# Re-exported here because importers still reach for it at this path.
_is_bad_slide_outcome = is_bad_slide_outcome


def _discover_episode_mapping(book_dir: Path):
    """Re-export — the implementation moved to `post_chapter_driver` (2026-08-08).

    `phases/audio_ingest_driver` imports it from THIS path, and its failure mode when the
    import broke was quiet in the worst way: the import sat inside a `try` whose except
    reported "could not resolve audio engine", so a moved function looked like a book
    with a broken engine config. A function rather than an alias, so the import stays
    lazy and the two modules do not become mutually dependent at import time.
    """
    from phases.post_chapter_driver import _discover_episode_mapping as _impl

    return _impl(book_dir)


def _phase_boundary_gate(book_dir: Path, boundary_name: str, projected_cost_usd: float | None = None) -> None:
    _info(
        f"[phased_rollout] phase boundary: {boundary_name}"
        + (f" (projected cost: ${projected_cost_usd:.2f})" if projected_cost_usd else "")
    )


# The C3 breaker's own logic moved to `_chapter_breaker` (2026-08-08) so its state can
# be shared safely once this loop gains workers. Re-exported because importers and tests
# still reach for the signature helper at this path.
_failure_signature = failure_signature


def _drive_per_chapter_and_after(book_dir: Path, *, approve_audio_render: bool = False) -> int:
    """After Phase 0f approval: drive per-chapter loop → 0g → slides →
    audio phases (Audio Engine v2; skipped for notebooklm books) → finalize halt.

    *approve_audio_render* is set by the resume dispatcher when the human has
    cleared the audio-render H1 spend halt by re-invoking --resume."""
    # Use the slug from state — book_dir.name gives only the leaf (e.g. "vol-01")
    # which breaks validate_ship_ready for nested-series books.
    _state = read_state(book_dir) or {}
    book_slug = _state.get("book_slug") or book_dir.name
    _phase_boundary_gate(book_dir, "0f→per-chapter")

    contracts_dir = book_dir / "chapter-contracts"
    chapter_slugs = sorted(p.stem for p in contracts_dir.glob("*.yml"))
    if not chapter_slugs:
        _err(f"no chapter contracts under {contracts_dir} — Phase 0d should have produced them. Cannot proceed.")
        return 2

    n_swept = _sweep_orphan_episode_drafts(book_dir)
    if n_swept:
        _info(f"per-chapter sweep: removed {n_swept} orphan episode-drafts/ subdir(s)")

    state = read_state(book_dir) or {}
    completed_chapter_slugs = set(state.get("phases", {}).get("per-chapter", {}).get("completed_slugs", []))

    # C2: $0 pre-flight smoke gate. Validate every not-yet-shipped chapter's
    # deterministic prerequisites (chapter file present, contract parses + has
    # required keys, word count in hard band) BEFORE the loop spends a cent on
    # framing/convergence. A deterministic bug in chapter N halts here, at $0,
    # instead of after authoring chapter 1.
    _pending = [s for s in chapter_slugs if s not in completed_chapter_slugs]
    _smoke_failures = smoke_check_book(book_dir, _pending)
    if _smoke_failures:
        _reason = "; ".join(f"{s}: {r}" for s, r in _smoke_failures)
        _err(f"pre-flight smoke gate ($0) failed for {len(_smoke_failures)} chapter(s) — halting before any LLM spend:")
        for s, r in _smoke_failures:
            _err(f"  {s}: {r}")
        update_phase(
            book_dir,
            phase="per-chapter",
            status="failed",
            error=f"pre-flight smoke gate failed: {_reason}",
        )
        return 2

    update_phase(book_dir, phase="per-chapter", status="running")
    outcomes: list[ChapterOutcome] = []
    chapter_timings: dict[str, dict] = {}
    prior_state = read_state(book_dir) or {}
    chapter_timings.update(prior_state.get("phases", {}).get("per-chapter", {}).get("chapter_timings", {}))
    failed_chapter_slugs: set[str] = set(prior_state.get("phases", {}).get("per-chapter", {}).get("failed_slugs", []))
    # Both spend limits, and the admission check below, live in `_chapter_cost_caps` —
    # they are different in KIND (one fails a chapter, one halts the book) and reading
    # either without the other invites the wrong conclusion about a halt.
    per_chapter_cost_cap_usd, book_cost_cap_usd = read_caps(book_dir, log=_info)

    #: Owns the admission decision AND the count of chapters currently in flight, both
    #: under one lock — see `BookCeiling` for why those cannot be separated. `_book_cost_so_far`
    #: is passed in rather than imported there so this module's binding is the one used.
    ceiling = BookCeiling(book_cost_cap_usd, per_chapter_cost_cap_usd, _book_cost_so_far)

    # C3 circuit breaker: halt on a systemic failure instead of grinding through every
    # chapter with the same root cause. State is behind a lock and the verdict is asked
    # BEFORE a chapter starts as well as after one fails — see `_chapter_breaker`.
    # Decisions are identical to the previous inline version under a single worker.
    breaker = ChapterBreaker()

    #: One line per chapter that shipped this run, committed as a single commit after
    #: the loop rather than one commit per chapter. See the note at the append site.
    committed_chapter_lines: list[str] = []

    #: Set when the loop DECLINED to start a chapter because the book is halting. Kept
    #: because a run that stops this way must record WHY: without it the phase would
    #: fall out of the loop looking like a book whose chapters were simply all done, and
    #: the supervisor would relaunch straight into the same ceiling.
    _pre_start_halt: str | None = None

    #: A systemic halt recorded by any chapter. Handled once after dispatch rather than
    #: by an in-loop return, so one writer owns the exit however many chapters are
    #: finishing as it lands. First reason wins — it is the diagnosis a human reads.
    _halt_reason: str | None = None

    #: Guards every collection above. `update_phase` has its own lock for the state FILE,
    #: but these are this function's own mutable state and nothing else protects them.
    _shared = threading.Lock()

    def _snapshot() -> dict:
        """A consistent view of the shared collections, for a state write.

        Taken under the lock and deep-ish copied: `update_phase` serialises these into
        JSON, and handing it a dict a worker is still mutating is how you get a state
        file describing a moment that never existed.
        """
        with _shared:
            return {
                "completed_slugs": sorted(completed_chapter_slugs),
                "failed_slugs": sorted(failed_chapter_slugs),
                "chapter_timings": {k: dict(v) for k, v in chapter_timings.items()},
            }

    def _final_extras() -> dict:
        """`_snapshot()` plus the clearing of the in-flight markers.

        `update_phase` MERGES extras into the phase block, so `current_chapter` and
        `convergence_iter` — written by every progress beat — survive into the terminal
        record unless something clears them. A finished book otherwise still reports the
        last chapter as the one it is working on, which is what a supervisor or status
        card reads to answer exactly that question.
        """
        return {**_snapshot(), "current_chapter": None, "convergence_iter": None}

    # How many chapters run at once. ONE by default, so this change is inert until a book
    # opts in — the measured prize is 732 min of serial chapters becoming ~185 at four
    # workers, but the first book to try it should be one Asif chose.
    _requested_workers = max(1, int(os.environ.get("PER_CHAPTER_MAX_WORKERS", "1")))
    #: Clamped by the ceiling: a book with a per-book cap but NO per-chapter cap has no
    #: bound on what an in-flight chapter may still spend, so admission cannot be made
    #: safe concurrently and the only honest width is one. Refusing to widen is the
    #: correct direction to be wrong — the alternative is overshooting a spend limit.
    _max_workers = ceiling.concurrency_limit(_requested_workers)
    if _max_workers < _requested_workers:
        _info(
            f"per-chapter: {_requested_workers} workers requested but this book sets a per-book "
            f"ceiling with no per-chapter cap — running serially so the ceiling stays enforceable"
        )

    def _commit_chapter_batch() -> None:
        """Commit every chapter that shipped this run, as one commit.

        Called on EVERY exit from the loop — normal completion, the circuit-breaker
        halt and the systemic halt — because chapters that shipped before a halt are
        finished work and must not be left uncommitted just because a later one broke.
        Safe to call more than once and safe to call with nothing pending:
        `phase_git_commit` already no-ops when `git status` comes back empty.
        """
        if not committed_chapter_lines:
            return
        n = len(committed_chapter_lines)
        subject = f"podcast({book_slug}): per-chapter — {n} chapter(s) shipped"
        phase_git_commit(book_dir, subject + "\n\n" + "\n".join(committed_chapter_lines))
        committed_chapter_lines.clear()

    # THIS LOOP IS SERIAL, but is now SAFE TO PARALLELISE — all three blockers found on
    # 2026-08-08 are cleared (full record in git history). It is the biggest wall-clock
    # lever in the pipeline: 732 min for 20 chapters, measured.
    #
    #   1. commits are batched after the loop      (`_commit_chapter_batch`)
    #   2. the C3 breaker is locked and asked BEFORE a chapter starts, so a worker that
    #      has not begun can still decline        (`_chapter_breaker`)
    #   3. the per-book ceiling admits or refuses a chapter before it spends
    #                                             (`_chapter_cost_caps.admit`)
    #
    # When workers are added: the compose loop in `_translation_edition` must stay serial
    # regardless — it threads an 80-word continuity tail between chapters — and
    # `test_loops_stay_serial` should be narrowed to cover that loop alone.
    def _run_one_chapter(slug: str) -> None:
        """Everything one chapter needs, safe to call from a worker thread.

        Mutates the shared collections only under `_shared`, and NEVER returns early
        with a decision of its own: a halt is RECORDED (`_halt_reason`) and the breaker
        is tripped, so chapters that have not begun decline at their own pre-start gate
        and the single post-dispatch handler owns the exit. Under one worker the outcome
        is identical to the previous in-loop `return 2`, reached a few cheap iterations
        later.
        """
        nonlocal _pre_start_halt

        # ADMISSION CONTROL on the per-book ceiling — refuse to START a chapter once the
        # cap is reached. The refusal is RETURNED and acted on here: it used to be
        # communicated only by tripping the breaker, which meant the ceiling was enforced
        # by `breaker.begin()` re-reading that flag below, and any reordering of these two
        # calls would have disabled it silently.
        _refusal = ceiling.admit(book_dir)
        if _refusal is not None:
            breaker.trip(_refusal)
            _info(f"phase: per-chapter[{slug}] · not started — book is halting ({_refusal[:80]})")
            with _shared:
                _pre_start_halt = _refusal
            return

        # Admitted, so this chapter is counted in flight until it finishes — however it
        # finishes. Releasing only on the success path would leak the count and make the
        # ceiling refuse everything after the first failure.
        try:
            _run_admitted_chapter(slug)
        finally:
            ceiling.release()

    def _run_admitted_chapter(slug: str) -> None:
        """The body of a chapter that has already passed admission control."""
        nonlocal _halt_reason, _pre_start_halt

        # THE PRE-START GATE. Asking the breaker here — before any work — is what makes
        # its economics survive workers: a chapter that has not begun can still decline.
        try:
            _ordinal = breaker.begin(slug)
        except BreakerTripped as _t:
            _info(f"phase: per-chapter[{slug}] · not started — book is halting ({_t.reason[:80]})")
            with _shared:
                _pre_start_halt = _t.reason
            return
        _info(f"phase: per-chapter[{slug}] · extract → frame → build → converge")
        _t_start = datetime.now(timezone.utc)
        _cost_at_start = _chapter_cost_so_far(book_dir, slug)
        with _shared:
            chapter_timings[slug] = {
                "started_ts": _t_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_ts": None,
                "duration_sec": None,
                "verdict": None,
                "cost_usd": None,
            }
        # C5: per-chapter progress beat. Refreshes ts_updated and records the
        # chapter in flight so a supervisor can tell "moved to a new chapter"
        # from "stuck on the same one" without guessing PIDs. (Intra-chapter
        # liveness — during a long convergence — is judged by the supervisor via
        # cost-ledger / challenger-report mtime growth, not this beat.)
        update_phase(
            book_dir,
            phase="per-chapter",
            status="running",
            extras={"current_chapter": slug, "last_beat": _t_start.strftime("%Y-%m-%dT%H:%M:%SZ"), **_snapshot()},
        )

        # Phase 3: thread the mid-loop safety rails. Closures read the live ledger
        # so the convergence loop can check ceilings at each iteration boundary; the
        # heartbeat refreshes state so the supervisor's hang detection stays accurate.
        def _chapter_cost_fn(_bd=book_dir, _slug=slug, _start=_cost_at_start) -> float:
            return _chapter_cost_so_far(_bd, _slug) - _start

        def _book_cost_fn(_bd=book_dir) -> float:
            return _book_cost_so_far(_bd)

        def _heartbeat(outer: int, note: str, _bd=book_dir, _slug=slug) -> None:
            update_phase(
                _bd,
                phase="per-chapter",
                status="running",
                extras={
                    "current_chapter": _slug,
                    "last_beat": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "convergence_iter": outer,
                },
            )

        outcome = per_chapter_pass(
            book_dir,
            slug,
            per_chapter_cost_cap=per_chapter_cost_cap_usd,
            book_cost_cap=book_cost_cap_usd,
            chapter_cost_fn=_chapter_cost_fn,
            book_cost_fn=_book_cost_fn,
            heartbeat=_heartbeat,
        )
        _t_end = datetime.now(timezone.utc)
        _cost_end = _chapter_cost_so_far(book_dir, slug)
        _chapter_cost = round(_cost_end - _cost_at_start, 4)
        with _shared:
            chapter_timings[slug]["completed_ts"] = _t_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            chapter_timings[slug]["duration_sec"] = round((_t_end - _t_start).total_seconds(), 1)
            chapter_timings[slug]["verdict"] = outcome.final_verdict
            chapter_timings[slug]["cost_usd"] = _chapter_cost
            if per_chapter_cost_cap_usd > 0 and _chapter_cost > per_chapter_cost_cap_usd:
                cost_msg = f"COST-CAPPED: chapter spent ${_chapter_cost:.2f} > cap ${per_chapter_cost_cap_usd:.2f}"
                _err(f"  [{slug}] {cost_msg}")
                outcome.notes.append(cost_msg)
                outcome.final_verdict = "FAILED"
                chapter_timings[slug]["verdict"] = "FAILED-COST-CAPPED"
            outcomes.append(outcome)
        _info(render_outcome(outcome))
        if outcome.episode_rebuild_failed:
            _err(f"  [{slug}] episode.txt rebuild failed during convergence — review framing/build")
        # F35: a per-BOOK ceiling breach is SYSTEMIC — halt the whole book with a
        # COST-CEILING marker so supervise_run.py does NOT relaunch (it would just
        # burn through the ceiling again). Distinct from a per-chapter cap (below),
        # which only fails the one chapter and degrades to the next.
        if outcome.systemic_halt:
            with _shared:
                chapter_timings[slug]["error"] = outcome.systemic_halt
                failed_chapter_slugs.add(slug)
                if _halt_reason is None:
                    _halt_reason = outcome.systemic_halt
            # Trip the breaker so chapters that have not begun decline at their own
            # pre-start gate; the post-dispatch handler owns the exit.
            breaker.trip(outcome.systemic_halt)
            _err(f"{outcome.systemic_halt} — halting book (no relaunch).")
            return
        if outcome.final_verdict == "FAILED":
            # C1: capture the real reason into durable state (was swallowed —
            # only outcome.notes held it, and render_outcome dropped it).
            _reason = outcome.notes[-1].strip().splitlines()[0][:300] if outcome.notes else "no reason captured"
            with _shared:
                failed_chapter_slugs.add(slug)
                chapter_timings[slug]["error"] = _reason
                # Read UNDER the lock and passed by value below. Reading it at the call
                # site instead took it from a dict other workers are inserting into, and
                # the breaker uses this duration to decide systemic-vs-content — the one
                # access in this function that escaped the discipline the rest follows.
                _duration_sec = chapter_timings[slug].get("duration_sec") or 0.0

            # C3 circuit breaker: is this a SYSTEMIC failure (halt) or a genuine
            # per-chapter content failure (graceful-degrade)? The two signals, the
            # signature normalisation and the shared state all live in
            # `_chapter_breaker` now — `_ordinal` is what `begin()` handed back, passed
            # in rather than re-read because under workers "was this the first attempt"
            # is a fact about when this chapter STARTED, not about the counter now.
            _systemic = breaker.record_failure(slug, _reason, _duration_sec, _ordinal)

            if _systemic:
                with _shared:
                    if _halt_reason is None:
                        _halt_reason = f"CIRCUIT-BREAKER: {_systemic}"
                _err(f"CIRCUIT-BREAKER halt: {_systemic}")
                _err("Not grinding through remaining chapters — fix the root cause, then --resume.")
                return

            # Genuine per-chapter content failure → graceful-degrade (F33-second).
            update_phase(
                book_dir,
                phase="per-chapter",
                status="running",
                error=f"[{slug}] {_reason}",
                extras=_snapshot(),
            )
            _err(f"chapter {slug} failed: {_reason}")
            _err(f"chapter {slug} — continuing to next chapter (F33-second graceful-degrade).")
            return

        # Both mutations under ONE acquisition: a reader taking `_snapshot()` between them
        # would see a chapter marked complete that the batched commit does not yet name.
        #
        # The commit LINE is recorded here and committed after the loop. Per-chapter
        # commits ran a repo-wide `git status` each time, and under workers two threads
        # would contend on .git/index.lock and commit each other's staged files. Deferring
        # is crash-safe: the chapter's output is on disk and `completed_slugs` is in the
        # state file, so a resume skips it and the commit happens later. It is also safe
        # against the clean-tree gate, which allowlists every directory this loop writes
        # — verified in phases/preflight.py.
        with _shared:
            completed_chapter_slugs.add(slug)
            committed_chapter_lines.append(
                f"  {slug}: {outcome.final_verdict} "
                f"(iter={outcome.outer_iterations} · P0={outcome.p0_remaining} · P1={outcome.p1_remaining})"
            )
        update_phase(book_dir, phase="per-chapter", status="running", extras=_snapshot())

    # ── dispatch ────────────────────────────────────────────────────────────
    # Serial by DEFAULT (one worker), so merging this changed nothing about how a book
    # runs. Set PER_CHAPTER_MAX_WORKERS to opt a book in; the three blockers that made
    # concurrency unsafe are cleared (see the comment above `_run_one_chapter`).
    #
    # The one-worker path deliberately does NOT go through the executor: a pool of one is
    # not quite the same thing (exception timing, thread identity, and the ordering of
    # interleaved log lines), and the default path should be the one that has been
    # running for months rather than a new arrangement of it.
    _pending_slugs = [s for s in chapter_slugs if s not in completed_chapter_slugs and s not in failed_chapter_slugs]
    for _s in chapter_slugs:
        if _s in completed_chapter_slugs:
            _info(f"phase: per-chapter[{_s}] · already shipped, skipping")
        elif _s in failed_chapter_slugs:
            _info(f"phase: per-chapter[{_s}] · prior FAILED, skipping (--retry-phase per-chapter re-attempts it)")

    def _record_chapter_crash(slug: str, exc: BaseException) -> None:
        """A chapter that died of an unexpected exception becomes this phase's halt.

        ONE handler for both dispatch paths. It used to exist only inside the executor
        loop, so the DEFAULT (serial) path let an exception escape the whole phase —
        taking the batched commit below with it and leaving every chapter that had
        already shipped uncommitted. Per-chapter commits used to make that harmless; the
        batched commit made it lossy, and only the path nobody runs was protected.
        """
        nonlocal _halt_reason
        _err(f"chapter {slug} raised {type(exc).__name__}: {exc}")
        with _shared:
            failed_chapter_slugs.add(slug)
            if _halt_reason is None:
                _halt_reason = f"chapter {slug} raised {type(exc).__name__}: {exc}"

    def _dispatch_one(slug: str) -> None:
        """Run one chapter, converting an unexpected exception into a recorded halt."""
        try:
            _run_one_chapter(slug)
        except Exception as _e:  # noqa: BLE001 - recorded, then the phase decides
            _record_chapter_crash(slug, _e)

    if _max_workers <= 1:
        for _s in _pending_slugs:
            _dispatch_one(_s)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        _info(f"per-chapter: running {len(_pending_slugs)} chapter(s) with {_max_workers} workers")
        with ThreadPoolExecutor(max_workers=_max_workers) as _ex:
            _futures = {_ex.submit(_dispatch_one, _s): _s for _s in _pending_slugs}
            for _f in as_completed(_futures):
                # `_dispatch_one` already caught anything an ordinary chapter can raise;
                # this is the backstop for what it deliberately does not catch (a
                # BaseException such as a worker killed mid-flight), which would otherwise
                # vanish into the future object unread.
                try:
                    _f.result()
                except BaseException as _e:  # noqa: BLE001 - recorded, then the phase decides
                    _record_chapter_crash(_futures[_f], _e)

    # ONE commit for the whole loop, before the failure handling below — a book where
    # 18 of 20 chapters shipped must still commit those 18.
    _commit_chapter_batch()

    # A systemic halt recorded by any chapter. Handled HERE, once, rather than by an
    # in-loop return: under workers several chapters may be finishing as the halt lands,
    # and a single writer keeps the recorded state consistent. Under one worker this is
    # the same outcome the old in-loop `return 2` produced, reached a few cheap
    # iterations later.
    if _halt_reason:
        update_phase(
            book_dir,
            phase="per-chapter",
            status="failed",
            error=_halt_reason,
            extras=_final_extras(),
        )
        _err(f"per-chapter halted: {_halt_reason}")
        return 2

    # A halt that stopped chapters from STARTING is recorded before the per-chapter
    # failure handling below, and returns 2 so the supervisor does not relaunch into the
    # same wall. The reason carries its own marker (COST-CEILING for the ceiling), which
    # is what supervise_run.py reads to decide that.
    if _pre_start_halt and any(s not in completed_chapter_slugs for s in chapter_slugs):
        update_phase(
            book_dir,
            phase="per-chapter",
            status="failed",
            error=_pre_start_halt,
            extras=_final_extras(),
        )
        _err(f"per-chapter halted before starting further chapters: {_pre_start_halt}")
        return 2

    if failed_chapter_slugs:
        update_phase(
            book_dir,
            phase="per-chapter",
            status="failed",
            error=(
                f"{len(failed_chapter_slugs)} chapter(s) failed: "
                f"{', '.join(sorted(failed_chapter_slugs))}. "
                f"{len(completed_chapter_slugs)} chapter(s) completed. "
                f"Triage failures or raise per_chapter_cost_cap_usd and --resume."
            ),
            extras=_final_extras(),
        )
        _err(
            f"per-chapter loop: {len(failed_chapter_slugs)} failed, "
            f"{len(completed_chapter_slugs)} completed. Halting for triage."
        )
        return 2

    # `_snapshot()` rather than an inline dict, like every other write in this phase.
    # `failed_slugs` used to be hardcoded `[]` here, which is the same value — the
    # branch above returns when any chapter failed — but two ways of building the
    # same extras is how the two drift.
    update_phase(book_dir, phase="per-chapter", status="completed", extras=_final_extras())

    # Phase per-chapter-optimize (Wave I) — Sonnet arc/format/host-role check.
    # Guarded by optimize_enabled flag in meta.yml (default False — backward compat).
    _opt_done = (read_state(book_dir) or {}).get("phases", {}).get("per-chapter-optimize", {}).get("status") in (
        "completed",
        "skipped",
    )
    if _opt_done:
        _info("phase: per-chapter-optimize · already completed/skipped, skipping")
    else:
        from phases.per_chapter_optimize import run_book_optimize

        _info("phase: per-chapter-optimize · Sonnet arc/format/host-role check")
        update_phase(book_dir, phase="per-chapter-optimize", status="running")
        try:
            opt_results = run_book_optimize(book_dir)
        except Exception as e:
            update_phase(book_dir, phase="per-chapter-optimize", status="failed", error=str(e))
            _err(f"phase per-chapter-optimize failed: {e}")
            return 2
        if opt_results.get("skipped"):
            update_phase(
                book_dir,
                phase="per-chapter-optimize",
                status="skipped",
                extras={"reason": opt_results.get("reason", "optimize_enabled=false")},
            )
            _info(f"  per-chapter-optimize: skipped ({opt_results.get('reason', '')})")
        elif opt_results.get("blocked", 0):
            update_phase(
                book_dir,
                phase="per-chapter-optimize",
                status="failed",
                error=f"{opt_results['blocked']} chapter(s) blocked by P0 findings",
            )
            _err(f"per-chapter-optimize: {opt_results['blocked']} chapter(s) blocked. Fix P0s and --resume.")
            return 2
        else:
            update_phase(
                book_dir,
                phase="per-chapter-optimize",
                status="completed",
                extras={"chapters": opt_results.get("chapters", 0), "warn": opt_results.get("warn", 0)},
            )
            phase_git_commit(
                book_dir,
                f"podcast({book_slug}): phase per-chapter-optimize ({opt_results.get('chapters', 0)} chapters, {opt_results.get('warn', 0)} warnings)",
            )
            _info(
                f"  per-chapter-optimize: {opt_results.get('chapters', 0)} chapters checked, {opt_results.get('warn', 0)} warnings."
            )

    # Everything after the chapter loop — 0g, slides, audio, finalize — lives in
    # `post_chapter_driver`. It shares no mutable state with the loop above: it needs
    # only the slug, which chapters completed, their outcomes, and the audio-render
    # approval, so it takes those four as arguments.
    from phases.post_chapter_driver import drive_post_chapter

    return drive_post_chapter(
        book_dir,
        book_slug=book_slug,
        completed_chapter_slugs=completed_chapter_slugs,
        outcomes=outcomes,
        approve_audio_render=approve_audio_render,
    )
