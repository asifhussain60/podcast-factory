"""phases/chapter_driver.py — _drive_per_chapter_and_after.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Drives the per-chapter convergence loop, Phase 0g, slide decks, and the
finalize halt. Called by resume_dispatcher after Phase 0f approval.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _chapter_breaker import BreakerTripped, ChapterBreaker, failure_signature
from _chapter_cost_caps import admit, read_caps
from _convergence import ChapterOutcome, render_outcome
from _paths import REPO_ROOT
from _progress import read_state, update_phase
from _subprocess import err as _err
from _subprocess import info as _info
from _subprocess import run as _run

from phases.bundle_audit import phase_0g_audit_bundles
from phases.per_chapter import per_chapter_pass
from phases.preflight import _sweep_orphan_episode_drafts
from phases.preflight_chapter import smoke_check_book
from phases.scaffold import phase_git_commit
from phases.series_plan import (
    _book_cost_so_far,
    _chapter_cost_so_far,
    _series_flag,
    phase_0g_register,
)
from phases.slide_cohort import is_bad_slide_outcome, run_slide_cohort

# Moved to phases/slide_cohort.py with the rest of Phase 11b (2026-07-31).
# Re-exported here because importers still reach for it at this path.
_is_bad_slide_outcome = is_bad_slide_outcome


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
    for slug in chapter_slugs:
        if slug in completed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · already shipped, skipping")
            continue
        if slug in failed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · prior FAILED, skipping (--retry-phase per-chapter re-attempts it)")
            continue
        # ADMISSION CONTROL on the per-book ceiling — refuse to START a chapter once the
        # cap is reached. See `_chapter_cost_caps.admit` for why this is admission rather
        # than a budget reservation.
        admit(book_dir, book_cost_cap_usd, breaker)

        # THE PRE-START GATE. Asking the breaker here — before any work — is what makes
        # its economics survive workers: a chapter that has not begun can still decline
        # to begin. Serially this can only fire if a previous chapter tripped it or the
        # ceiling check above just did, so behaviour today is unchanged.
        try:
            _ordinal = breaker.begin(slug)
        except BreakerTripped as _t:
            _info(f"phase: per-chapter[{slug}] · not started — book is halting ({_t.reason[:80]})")
            _pre_start_halt = _t.reason
            continue
        _info(f"phase: per-chapter[{slug}] · extract → frame → build → converge")
        _t_start = datetime.now(timezone.utc)
        _cost_at_start = _chapter_cost_so_far(book_dir, slug)
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
            extras={
                "current_chapter": slug,
                "last_beat": _t_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_slugs": sorted(completed_chapter_slugs),
                "failed_slugs": sorted(failed_chapter_slugs),
                "chapter_timings": chapter_timings,
            },
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
            chapter_timings[slug]["error"] = outcome.systemic_halt
            failed_chapter_slugs.add(slug)
            update_phase(
                book_dir,
                phase="per-chapter",
                status="failed",
                error=outcome.systemic_halt,
                extras={
                    "completed_slugs": sorted(completed_chapter_slugs),
                    "failed_slugs": sorted(failed_chapter_slugs),
                    "chapter_timings": chapter_timings,
                },
            )
            _err(f"{outcome.systemic_halt} — halting book (no relaunch).")
            _commit_chapter_batch()  # chapters that shipped before the halt are finished work
            return 2
        if outcome.final_verdict == "FAILED":
            failed_chapter_slugs.add(slug)
            # C1: capture the real reason into durable state (was swallowed —
            # only outcome.notes held it, and render_outcome dropped it).
            _reason = outcome.notes[-1].strip().splitlines()[0][:300] if outcome.notes else "no reason captured"
            chapter_timings[slug]["error"] = _reason

            # C3 circuit breaker: is this a SYSTEMIC failure (halt) or a genuine
            # per-chapter content failure (graceful-degrade)? The two signals, the
            # signature normalisation and the shared state all live in
            # `_chapter_breaker` now — `_ordinal` is what `begin()` handed back, passed
            # in rather than re-read because under workers "was this the first attempt"
            # is a fact about when this chapter STARTED, not about the counter now.
            _systemic = breaker.record_failure(
                slug,
                _reason,
                chapter_timings[slug].get("duration_sec") or 0.0,
                _ordinal,
            )

            if _systemic:
                update_phase(
                    book_dir,
                    phase="per-chapter",
                    status="failed",
                    error=f"CIRCUIT-BREAKER: {_systemic}",
                    extras={
                        "completed_slugs": sorted(completed_chapter_slugs),
                        "failed_slugs": sorted(failed_chapter_slugs),
                        "chapter_timings": chapter_timings,
                    },
                )
                _err(f"CIRCUIT-BREAKER halt: {_systemic}")
                _err("Not grinding through remaining chapters — fix the root cause, then --resume.")
                _commit_chapter_batch()  # chapters that shipped before the halt are finished work
                return 2

            # Genuine per-chapter content failure → graceful-degrade (F33-second).
            update_phase(
                book_dir,
                phase="per-chapter",
                status="running",
                error=f"[{slug}] {_reason}",
                extras={
                    "completed_slugs": sorted(completed_chapter_slugs),
                    "failed_slugs": sorted(failed_chapter_slugs),
                    "chapter_timings": chapter_timings,
                },
            )
            _err(f"chapter {slug} failed: {_reason}")
            _err(f"chapter {slug} — continuing to next chapter (F33-second graceful-degrade).")
            continue

        completed_chapter_slugs.add(slug)
        # Recorded now, COMMITTED after the loop (see the batched commit below).
        # `phase_git_commit` runs a repo-wide `git status --porcelain`, so doing it
        # per chapter meant N of those on a repo carrying a 30 MB mirror database —
        # and it is the first of the three things that made this loop impossible to
        # parallelise, because two threads would contend on .git/index.lock and each
        # commit the other's staged files under its own message.
        #
        # Deferring is safe against a crash: the chapter's OUTPUT is already on disk
        # and `completed_slugs` is already in the state file by the time we get here,
        # so a resume skips it and the batched commit simply happens later. It is also
        # safe against the clean-tree gate, which already allowlists every directory
        # this loop writes (chapters/, episodes/, chapter-contracts/, episode-drafts/,
        # per-chapter-reports/, slide-decks/) — verified in phases/preflight.py.
        committed_chapter_lines.append(
            f"  {slug}: {outcome.final_verdict} "
            f"(iter={outcome.outer_iterations} · P0={outcome.p0_remaining} · P1={outcome.p1_remaining})"
        )
        update_phase(
            book_dir,
            phase="per-chapter",
            status="running",
            extras={
                "completed_slugs": sorted(completed_chapter_slugs),
                "chapter_timings": chapter_timings,
            },
        )

    # ONE commit for the whole loop, before the failure handling below — a book where
    # 18 of 20 chapters shipped must still commit those 18.
    _commit_chapter_batch()

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
            extras={
                "completed_slugs": sorted(completed_chapter_slugs),
                "failed_slugs": sorted(failed_chapter_slugs),
                "chapter_timings": chapter_timings,
            },
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
            extras={
                "completed_slugs": sorted(completed_chapter_slugs),
                "failed_slugs": sorted(failed_chapter_slugs),
                "chapter_timings": chapter_timings,
            },
        )
        _err(
            f"per-chapter loop: {len(failed_chapter_slugs)} failed, "
            f"{len(completed_chapter_slugs)} completed. Halting for triage."
        )
        return 2

    update_phase(
        book_dir,
        phase="per-chapter",
        status="completed",
        extras={
            "completed_slugs": sorted(completed_chapter_slugs),
            "failed_slugs": [],
            "chapter_timings": chapter_timings,
        },
    )

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

    # Phase 0g — register + dual-auditor bundle sweep.
    _0g_done = (read_state(book_dir) or {}).get("phases", {}).get("0g", {}).get("status") == "completed"
    if _0g_done:
        _info("phase: 0g · already completed, skipping")
    else:
        _info("phase: 0g · register series + dual-auditor bundle sweep")
        update_phase(book_dir, phase="0g", status="running")
        try:
            phase_0g_register(book_dir)
            _info("phase: 0g · register done; starting per-chapter audit sweep")
            audit_outcomes = phase_0g_audit_bundles(book_dir, sorted(completed_chapter_slugs))
        except RuntimeError as e:
            update_phase(book_dir, phase="0g", status="failed", error=str(e))
            _err(str(e))
            return 2
        update_phase(
            book_dir,
            phase="0g",
            status="completed",
            extras={"audit_outcomes": audit_outcomes},
        )
        phase_git_commit(
            book_dir,
            f"podcast({book_slug}): phase 0g register series + dual-auditor bundle sweep",
        )

    # Phase 11b — slide-deck cohort.
    enable_slide_decks = _series_flag(book_dir, "enable_slide_decks", default=True)
    _slides_already_done = (read_state(book_dir) or {}).get("phases", {}).get("per-chapter-slides", {}).get(
        "status"
    ) in ("completed", "skipped")
    if _slides_already_done:
        _info("phase: per-chapter-slides · already completed/skipped, advancing to finalize")
    elif enable_slide_decks:
        run_slide_cohort(book_dir, completed_chapter_slugs)
        phase_git_commit(book_dir, f"podcast({book_slug}): phase 11b slide-deck cohort")
    else:
        update_phase(
            book_dir, phase="per-chapter-slides", status="skipped", extras={"reason": "enable_slide_decks=false"}
        )

    # Audio Engine v2 phases — autonomous (API) engines author + gate dialogue
    # scripts, halt ONCE at H1 with the exact credit estimate, then render
    # into the canonical m4a layout. NotebookLM books mark both phases
    # skipped and continue to the manual finalize halt unchanged.
    from phases.audio_driver import drive_audio_phases

    _audio_outcome, _audio_rc = drive_audio_phases(book_dir, approve_render=approve_audio_render)
    if _audio_outcome == "halted":
        return 0  # clean stop at the H1 spend gate; --resume approves
    if _audio_outcome == "failed":
        return _audio_rc

    # Finalize phase — run G1-G7 gates, halt for human review before publish.
    # NOTE: the PDF companion-book path (0book-*) runs AFTER this halt, inside
    # publish_driver._drive_publish_through_done, so that any issues caught at
    # the podcast review gate are fixed before the book branch is generated.
    _phase_boundary_gate(book_dir, "per-chapter→finalize")
    _info("phase: finalize · run G1-G7 gates via validate_ship_ready.py")
    update_phase(book_dir, phase="finalize", status="running")

    # P3 (Stage 4): auto-run the zero-LLM Arabic-script restoration for
    # audio-sourced Islamic books before the gate. repair_glossary is idempotent
    # and free — it recovers any misassigned Arabic into arabic_script so the
    # reader "Show Arabic" toggle has content. The deterministic canonical/passage
    # restoration (steps 2b/3) and the reader-rendering feature are deferred;
    # until they land the G13 ship-gate only REPORTS coverage, it does not block.
    try:
        import json as _json

        from _content_profile import is_islamic_scholarly

        _state_p = book_dir / "_system" / "orchestrator-state.json"
        _st = _json.loads(_state_p.read_text()) if _state_p.exists() else {}
        if _st.get("source_kind") == "audio" and is_islamic_scholarly(book_dir):
            from restore_arabic import repair_glossary

            _rep = repair_glossary(book_dir)
            _info(f"phase: finalize · auto Arabic-restore (audio Islamic): {_rep}")
    except Exception as _e:  # never block finalize on a best-effort restore
        _err(f"finalize: Arabic auto-restore skipped (non-fatal): {_e}")

    validate_script = Path(__file__).resolve().parents[1] / "validate_ship_ready.py"
    rc, vout, verr = _run([sys.executable, str(validate_script), book_slug])
    print(vout)
    if rc != 0:
        update_phase(
            book_dir,
            phase="finalize",
            status="failed",
            error="G1-G7 gates failed; see stdout for the failing gate",
            extras={"validator_stdout": vout[-2000:], "validator_stderr": verr[-1000:]},
        )
        _err(
            "finalize halt — at least one G1-G7 gate failed. "
            "Fix the cause, then re-invoke `orchestrate_book.py --resume`."
        )
        return 2
    update_phase(book_dir, phase="finalize", status="halted", extras={"verdict": "SHIP-READY"})

    # The reading edition, built HERE rather than only after publish. Its input is
    # _system/source/text/refined-english.md, which has existed since 0b — it never
    # depended on the audio, only sat after it in the phase order. Building it now
    # means the articulated book.md and its PDF are in the Composer at the same
    # stopping point as the chapters and the slide-deck prompts, which is what a
    # human actually reviews. Self-skips unless the book lane can complete without
    # a human artifact; the publish-time call remains the path for the rest.
    from _book_preview import maybe_build_reading_edition_early

    maybe_build_reading_edition_early(book_dir, log=_info)

    # Non-blocking advisories. Emitters live in `_halt_advisories` so this file
    # (grandfathered by the line-count gate) stays their caller, not their home.
    from _halt_advisories import emit_decision_ledger, emit_transcription_advisories

    emit_transcription_advisories(book_dir, _info)
    emit_decision_ledger(book_dir, _info)

    _info("")
    _info("─" * 72)
    _info("Phase finalize complete · halted for human review (SHIP-READY).")
    _info("")
    _info("Review the clean version in the Podcast Factory Astro Site:")
    _info("  cd plan-dashboard && npm run dev")
    _info("  open http://localhost:4321/develop/" + book_slug + "/")
    _info("")
    # Engine-aware halt card. Per-episode routing: a book may be autonomous
    # (ElevenLabs) yet flip individual episodes to NotebookLM via
    # episode_engine_overrides — so the card may show BOTH an "already rendered"
    # note (for the API episodes) AND the NotebookLM upload ritual (for the
    # overridden ones). The no-overrides path is byte-identical to before (the
    # golden-test latch): pure-NotebookLM books print the full unfiltered table,
    # pure-ElevenLabs books print only the rendered note.
    # Shared filter: the SAME `notebooklm_episode_filter` the audio-ingest phase
    # uses, so the halt card and the phase agree on which episodes need the ritual.
    # None = pure-NotebookLM (all episodes); empty set = pure-API (none); a subset
    # = mixed-engine book.
    try:
        from _audio_engines import notebooklm_episode_filter

        _all_eps = [e["episode"] for e in _discover_episode_mapping(book_dir)]
        _nlm_filter: set[str] | None = notebooklm_episode_filter(book_dir, _all_eps)
    except Exception:
        _all_eps, _nlm_filter = [], None

    if _nlm_filter is None:
        _has_api = False
    elif not _nlm_filter:
        _has_api = True
    else:
        _has_api = any(ep not in _nlm_filter for ep in _all_eps)

    if _has_api:
        _info("Audio engine: elevenlabs — those episodes are ALREADY rendered into")
        _info("m4a/ with script-derived transcripts (no NotebookLM step, no")
        _info("normalize/transcribe needed). Review the audio with the reader.")
        _info("")
    # NotebookLM upload ritual: for a pure-NotebookLM book (_nlm_filter is None)
    # or any episode overridden to NotebookLM (non-empty set).
    if _nlm_filter is None or _nlm_filter:
        try:
            _print_notebooklm_table(book_dir, filter_episode_ids=_nlm_filter)
        except Exception as _tbl_exc:
            _info(f"  [notebooklm table error: {_tbl_exc}]")
        _info("")
        _info("After downloading the generated .m4a files, drop them anywhere under")
        _info("m4a/ — names don't matter. The next --resume normalizes them to canonical")
        _info("chapter order and transcribes via Azure Speech automatically (the")
        _info("audio-ingest phase) — no manual CLI step needed.")
        _info("")
        # Durable worklist file — the operator works ONE checklist across sessions
        # (it survives terminal scroll); audio-ingest + 0book-slide-import consume
        # the drops automatically on --resume.
        try:
            from _notebooklm_table import build_worklist_lines
            from assemble_bundle import build_upload_rows

            _wl_rows = build_upload_rows(book_dir, _discover_episode_mapping(book_dir), filter_episode_ids=_nlm_filter)
            _resume_cmd = f"python3 scripts/podcast/orchestrate_book.py --resume {book_slug}"
            _wl_path = book_dir / "_system" / "notebooklm-worklist.md"
            _wl_path.parent.mkdir(parents=True, exist_ok=True)
            _wl_path.write_text(
                "\n".join(build_worklist_lines(book_dir, upload_rows=_wl_rows, resume_cmd=_resume_cmd)) + "\n",
                encoding="utf-8",
            )
            _info(f"Durable worklist written: {_wl_path.relative_to(REPO_ROOT)}")
            _info("")
        except Exception as _wl_exc:
            _info(f"  [worklist file skipped: {_wl_exc}]")
    # Slide-deck generation always runs through NotebookLM's Slide-deck tool,
    # independent of the audio engine — print the card on EVERY path (it
    # self-skips when no chapter has a converged deck).
    try:
        _print_slide_deck_card(book_dir)
    except Exception as _card_exc:
        _info(f"  [slide-deck card error: {_card_exc}]")
    _info("")
    _info("When satisfied, authorize publish + trainer + merge:")
    _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
    _info("─" * 72)
    return 0


def _print_slide_deck_card(book_dir: Path) -> None:
    """Print the slide-deck generation card at the finalize halt.

    One row per chapter with a converged deck pair in slide-decks/ — the human
    generates each deck in NotebookLM's Slide deck tool during the SAME visit
    as the episode uploads, then drops the exported PDFs at the printed paths
    so 0book-slide-import can weave them into the reading edition on --resume.
    Prints nothing when no chapter participates (deck-less books)."""
    parent = Path(__file__).resolve().parents[1]
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    from _notebooklm_table import build_slide_deck_card

    lines = build_slide_deck_card(book_dir)
    if not lines:
        return
    _info("")
    for line in lines:
        _info(line)


def _discover_episode_mapping(book_dir: Path) -> list[dict]:
    """[{episode, chapter, n}] for every episode, in order.

    Prefers the Phase-0g episode map; falls back to discovering directly from
    episodes/ for books where the map isn't generated yet. Shared by the
    NotebookLM table and the per-episode engine routing at finalize so both see
    the SAME episode set.
    """
    parent = Path(__file__).resolve().parents[1]
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    from assemble_bundle import _load_episode_map

    mapping = _load_episode_map(book_dir)
    if mapping:
        return mapping
    import re as _re

    ep_pat = _re.compile(r"^(EP(\d+)-(.*))\.txt$")
    ep_dir = book_dir / "episodes"
    if not ep_dir.exists():
        return []
    out: list[dict] = []
    for ep_file in sorted(ep_dir.glob("EP*.txt")):
        m = ep_pat.match(ep_file.name)
        if not m:
            continue
        ep_slug, ep_num_str, ch_slug = m.group(1), m.group(2), m.group(3)
        out.append({"episode": ep_slug, "chapter": f"ch{ep_num_str}-{ch_slug}", "n": int(ep_num_str)})
    return out


def _print_notebooklm_table(book_dir: Path, filter_episode_ids: set[str] | None = None) -> None:
    """Print the NotebookLM upload table at finalize halt.

    Reuses discovery + formatting helpers from assemble_bundle.py.
    Prints per-episode rows: EP | Title | Upload source | Customize paste |
    NotebookLM Format setting | Length setting.

    *filter_episode_ids*: when None (the default), ALL episodes are listed —
    byte-identical to the pre-override behavior (the golden-test latch). When a
    set is given (mixed-engine books), only those episode ids are listed, so the
    operator uploads exactly the per-episode NotebookLM overrides.
    """
    try:
        # Import helpers from sibling script (same scripts/podcast/ parent).
        parent = Path(__file__).resolve().parents[1]
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        from _notebooklm_table import render_upload_table_lines
        from assemble_bundle import build_upload_rows
    except ImportError as exc:
        _info(f"  [notebooklm table skipped — import error: {exc}]")
        return

    mapping = _discover_episode_mapping(book_dir)
    if not mapping:
        _info("  [notebooklm table skipped — no episodes found]")
        return

    # SINGLE row constructor — shared with the durable worklist so both render
    # from identical data (byte-identical to the prior inline loop: the latch).
    rows = build_upload_rows(book_dir, mapping, filter_episode_ids=filter_episode_ids)

    _info("─" * 72)
    _info("NOTEBOOKLM UPLOAD TABLE")
    _info("")
    _info("Per row: click the CHAPTER cell to open the SOURCE to upload, and the")
    _info("EPISODE cell to open the FRAMING to paste into NotebookLM's Customize box.")
    _info("")
    for line in render_upload_table_lines(rows):
        _info(f"  {line}")
