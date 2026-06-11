"""phases/chapter_driver.py — _drive_per_chapter_and_after.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Drives the per-chapter convergence loop, Phase 0g, slide decks, and the
finalize halt. Called by resume_dispatcher after Phase 0f approval.
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import read_state, update_phase  # noqa: E402
from _convergence import ChapterOutcome, render_outcome  # noqa: E402
from phases.preflight import _sweep_orphan_episode_drafts  # noqa: E402
from phases.preflight_chapter import smoke_check_book  # noqa: E402
from phases.per_chapter import per_chapter_pass  # noqa: E402
from phases.series_plan import _series_numeric, _series_flag, _chapter_cost_so_far, _book_cost_so_far  # noqa: E402
from phases.series_plan import phase_0g_register  # noqa: E402
from phases.bundle_audit import phase_0g_audit_bundles  # noqa: E402
from phases.scaffold import phase_git_commit  # noqa: E402


from _subprocess import run as _run, err as _err, info as _info  # noqa: E402


def _phase_boundary_gate(book_dir: Path, boundary_name: str,
                         projected_cost_usd: float | None = None) -> None:
    _info(
        f"[phased_rollout] phase boundary: {boundary_name}"
        + (f" (projected cost: ${projected_cost_usd:.2f})" if projected_cost_usd else "")
    )


def _failure_signature(reason: str) -> str:
    """Normalize a failure reason so the same root cause across chapters matches.

    Collapses digits and slug-like tokens to a stable shape: "word count 2
    outside band" and "word count 5000 outside band" share a signature, while
    two genuinely different findings stay distinct. Used by the C3 circuit
    breaker to detect a systemic failure repeating across chapters.
    """
    s = reason.lower()
    s = re.sub(r"[0-9]+", "#", s)
    s = re.sub(r"[^a-z#\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]


def _drive_per_chapter_and_after(book_dir: Path) -> int:
    """After Phase 0f approval: drive per-chapter loop → 0g → finalize halt."""
    # Use the slug from state — book_dir.name gives only the leaf (e.g. "vol-01")
    # which breaks validate_ship_ready for nested-series books.
    _state = read_state(book_dir) or {}
    book_slug = _state.get("book_slug") or book_dir.name
    _phase_boundary_gate(book_dir, "0f→per-chapter")

    contracts_dir = book_dir / "chapter-contracts"
    chapter_slugs = sorted(p.stem for p in contracts_dir.glob("*.yml"))
    if not chapter_slugs:
        _err(
            f"no chapter contracts under {contracts_dir} — "
            "Phase 0d should have produced them. Cannot proceed."
        )
        return 2

    n_swept = _sweep_orphan_episode_drafts(book_dir)
    if n_swept:
        _info(f"per-chapter sweep: removed {n_swept} orphan episode-drafts/ subdir(s)")

    state = read_state(book_dir) or {}
    completed_chapter_slugs = set(
        state.get("phases", {}).get("per-chapter", {}).get("completed_slugs", [])
    )

    # C2: $0 pre-flight smoke gate. Validate every not-yet-shipped chapter's
    # deterministic prerequisites (chapter file present, contract parses + has
    # required keys, word count in hard band) BEFORE the loop spends a cent on
    # framing/convergence. A deterministic bug in chapter N halts here, at $0,
    # instead of after authoring chapter 1.
    _pending = [s for s in chapter_slugs if s not in completed_chapter_slugs]
    _smoke_failures = smoke_check_book(book_dir, _pending)
    if _smoke_failures:
        _reason = "; ".join(f"{s}: {r}" for s, r in _smoke_failures)
        _err(
            f"pre-flight smoke gate ($0) failed for {len(_smoke_failures)} "
            f"chapter(s) — halting before any LLM spend:"
        )
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
    chapter_timings.update(
        prior_state.get("phases", {}).get("per-chapter", {}).get("chapter_timings", {})
    )
    failed_chapter_slugs: set[str] = set(
        prior_state.get("phases", {}).get("per-chapter", {}).get("failed_slugs", [])
    )
    per_chapter_cost_cap_usd = _series_numeric(
        book_dir, "per_chapter_cost_cap_usd", default=5.0,
    )
    if per_chapter_cost_cap_usd > 0:
        _info(f"per-chapter cost cap: ${per_chapter_cost_cap_usd:.2f} (per series-plan)")
    # F35: per-BOOK hard ceiling, checked mid-loop (default 0 = disabled, so
    # existing books are unaffected unless they opt in via series-plan).
    book_cost_cap_usd = _series_numeric(book_dir, "book_cost_cap_usd", default=0.0)
    if book_cost_cap_usd > 0:
        _info(f"per-book cost ceiling: ${book_cost_cap_usd:.2f} (per series-plan)")

    # C3 circuit breaker state: count chapters actually attempted this run and
    # group failures by normalized signature, to halt on a systemic failure
    # instead of grinding through every chapter with the same root cause.
    attempted = 0
    failure_signatures: dict[str, list[str]] = {}

    for slug in chapter_slugs:
        if slug in completed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · already shipped, skipping")
            continue
        if slug in failed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · prior FAILED, skipping (use --retry-chapter to re-attempt)")
            continue
        attempted += 1
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
                _bd, phase="per-chapter", status="running",
                extras={
                    "current_chapter": _slug,
                    "last_beat": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "convergence_iter": outer,
                },
            )

        outcome = per_chapter_pass(
            book_dir, slug,
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
            cost_msg = (
                f"COST-CAPPED: chapter spent ${_chapter_cost:.2f} > cap "
                f"${per_chapter_cost_cap_usd:.2f}"
            )
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
                book_dir, phase="per-chapter", status="failed",
                error=outcome.systemic_halt,
                extras={
                    "completed_slugs": sorted(completed_chapter_slugs),
                    "failed_slugs": sorted(failed_chapter_slugs),
                    "chapter_timings": chapter_timings,
                },
            )
            _err(f"{outcome.systemic_halt} — halting book (no relaunch).")
            return 2
        if outcome.final_verdict == "FAILED":
            failed_chapter_slugs.add(slug)
            # C1: capture the real reason into durable state (was swallowed —
            # only outcome.notes held it, and render_outcome dropped it).
            _reason = (
                outcome.notes[-1].strip().splitlines()[0][:300]
                if outcome.notes else "no reason captured"
            )
            chapter_timings[slug]["error"] = _reason

            # C3 circuit breaker: is this a SYSTEMIC failure (halt) or a genuine
            # per-chapter content failure (graceful-degrade)? Two systemic signals:
            #   (a) the FIRST attempted chapter failed in <5s — a deterministic
            #       crash (path/contract/template bug), not content; or
            #   (b) the SAME normalized failure has now hit >=2 chapters — paying
            #       for the same lesson again is waste (archetype-over-rerun rule).
            _sig = _failure_signature(_reason)
            _sig_slugs = failure_signatures.setdefault(_sig, [])
            if slug not in _sig_slugs:
                _sig_slugs.append(slug)
            _dur = chapter_timings[slug].get("duration_sec") or 0.0
            _systemic: str | None = None
            if attempted == 1 and _dur < 5.0:
                _systemic = (
                    f"first attempted chapter '{slug}' failed in {_dur:.1f}s — "
                    f"deterministic/systemic (not content): {_reason}"
                )
            elif len(_sig_slugs) >= 2:
                _systemic = (
                    f"same failure across {len(_sig_slugs)} chapters "
                    f"({', '.join(_sig_slugs)}) — systemic, not per-chapter: {_reason}"
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
                _err(
                    "Not grinding through remaining chapters — fix the root cause, "
                    "then --resume."
                )
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
        phase_git_commit(
            book_dir,
            f"podcast({book_slug})[{slug}]: {outcome.final_verdict} "
            f"(iter={outcome.outer_iterations} · P0={outcome.p0_remaining} "
            f"P1={outcome.p1_remaining})",
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
    _opt_done = (
        (read_state(book_dir) or {})
        .get("phases", {})
        .get("per-chapter-optimize", {})
        .get("status") in ("completed", "skipped")
    )
    if _opt_done:
        _info("phase: per-chapter-optimize · already completed/skipped, skipping")
    else:
        from phases.per_chapter_optimize import run_book_optimize  # noqa: E402
        _info("phase: per-chapter-optimize · Sonnet arc/format/host-role check")
        update_phase(book_dir, phase="per-chapter-optimize", status="running")
        try:
            opt_results = run_book_optimize(book_dir)
        except Exception as e:  # noqa: BLE001
            update_phase(book_dir, phase="per-chapter-optimize", status="failed", error=str(e))
            _err(f"phase per-chapter-optimize failed: {e}")
            return 2
        if opt_results.get("skipped"):
            update_phase(book_dir, phase="per-chapter-optimize", status="skipped",
                         extras={"reason": opt_results.get("reason", "optimize_enabled=false")})
            _info(f"  per-chapter-optimize: skipped ({opt_results.get('reason', '')})")
        elif opt_results.get("blocked", 0):
            update_phase(book_dir, phase="per-chapter-optimize", status="failed",
                         error=f"{opt_results['blocked']} chapter(s) blocked by P0 findings")
            _err(f"per-chapter-optimize: {opt_results['blocked']} chapter(s) blocked. Fix P0s and --resume.")
            return 2
        else:
            update_phase(book_dir, phase="per-chapter-optimize", status="completed",
                         extras={"chapters": opt_results.get("chapters", 0),
                                  "warn": opt_results.get("warn", 0)})
            phase_git_commit(book_dir, f"podcast({book_slug}): phase per-chapter-optimize ({opt_results.get('chapters', 0)} chapters, {opt_results.get('warn', 0)} warnings)")
            _info(f"  per-chapter-optimize: {opt_results.get('chapters', 0)} chapters checked, {opt_results.get('warn', 0)} warnings.")

    # Phase 0g — register + dual-auditor bundle sweep.
    _0g_done = (
        (read_state(book_dir) or {})
        .get("phases", {})
        .get("0g", {})
        .get("status") == "completed"
    )
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
            book_dir, phase="0g", status="completed",
            extras={"audit_outcomes": audit_outcomes},
        )
        phase_git_commit(
            book_dir,
            f"podcast({book_slug}): phase 0g register series + dual-auditor bundle sweep",
        )

    # Phase 11b — slide-deck cohort.
    enable_slide_decks = _series_flag(book_dir, "enable_slide_decks", default=True)
    _slides_already_done = (
        (read_state(book_dir) or {})
        .get("phases", {})
        .get("per-chapter-slides", {})
        .get("status") in ("completed", "skipped")
    )
    if _slides_already_done:
        _info("phase: per-chapter-slides · already completed/skipped, advancing to finalize")
    elif enable_slide_decks:
        _info("phase: per-chapter-slides · slide-deck cohort authoring + slide-deck-challenger")
        update_phase(book_dir, phase="per-chapter-slides", status="running")
        try:
            from _slide_convergence import run_slide_convergence  # optional module
        except ImportError as e:
            _err(f"slide-deck integration missing: {e}; skipping phase")
            update_phase(book_dir, phase="per-chapter-slides", status="skipped",
                         extras={"reason": "module-not-available"})
        else:
            slide_outcomes: dict[str, str] = {}
            from _content_profile import slide_deck_mode
            if slide_deck_mode(book_dir) == "book":
                # Book mode (2026-06-10): ONE deck pair for the whole book —
                # one NotebookLM generation instead of one per chapter. The
                # pair is deterministically validated by author_book_deck_pair;
                # the slide-deck-challenger can be invoked at book scope for a
                # semantic pass, and the human reviews the exported deck at the
                # 0book-slide-import drop gate.
                _info("phase: per-chapter-slides · slide_deck_mode=book → single book-level pair")
                try:
                    from _slide_authoring import author_book_deck_pair
                    result = author_book_deck_pair(book_dir)
                    slide_outcomes["book"] = (
                        "AUTHORED" if result.success
                        else f"FAILED: {'; '.join(result.validation_findings[:3])}"
                    )
                except Exception as e:  # noqa: BLE001
                    _err(f"book-level slide-deck authoring failed (non-fatal): {e}")
                    slide_outcomes["book"] = "ERROR"
            else:
                for slug in completed_chapter_slugs:
                    _info(f"phase: per-chapter-slides[{slug}] · density gauge → author → challenge")
                    try:
                        result = run_slide_convergence(book_dir, slug)
                        slide_outcomes[slug] = result.verdict
                    except Exception as e:  # noqa: BLE001
                        _err(f"slide-deck convergence failed for {slug} (non-fatal): {e}")
                        slide_outcomes[slug] = "ERROR"
            update_phase(
                book_dir, phase="per-chapter-slides", status="completed",
                extras={"outcomes": slide_outcomes},
            )
            phase_git_commit(book_dir, f"podcast({book_slug}): phase 11b slide-deck cohort")
    else:
        update_phase(book_dir, phase="per-chapter-slides", status="skipped",
                     extras={"reason": "enable_slide_decks=false"})

    # Finalize phase — run G1-G7 gates, halt for human review before publish.
    # NOTE: the PDF companion-book path (0book-*) runs AFTER this halt, inside
    # publish_driver._drive_publish_through_done, so that any issues caught at
    # the podcast review gate are fixed before the book branch is generated.
    _phase_boundary_gate(book_dir, "per-chapter→finalize")
    _info("phase: finalize · run G1-G7 gates via validate_ship_ready.py")
    update_phase(book_dir, phase="finalize", status="running")
    validate_script = Path(__file__).resolve().parents[1] / "validate_ship_ready.py"
    rc, vout, verr = _run([sys.executable, str(validate_script), book_slug])
    print(vout)
    if rc != 0:
        update_phase(book_dir, phase="finalize", status="failed",
                     error="G1-G7 gates failed; see stdout for the failing gate",
                     extras={"validator_stdout": vout[-2000:], "validator_stderr": verr[-1000:]})
        _err("finalize halt — at least one G1-G7 gate failed. "
             "Fix the cause, then re-invoke `orchestrate_book.py --resume`.")
        return 2
    update_phase(book_dir, phase="finalize", status="halted",
                 extras={"verdict": "SHIP-READY"})
    _info("")
    _info("─" * 72)
    _info("Phase finalize complete · halted for human review (SHIP-READY).")
    _info("")
    _info("Review the clean version in the Podcast Factory Astro Site:")
    _info("  cd plan-dashboard && npm run dev")
    _info("  open http://localhost:4321/develop/" + book_slug + "/")
    _info("")
    # ── NotebookLM upload instructions (mandatory per standing rule) ──────────
    try:
        _print_notebooklm_table(book_dir)
    except Exception as _tbl_exc:
        _info(f"  [notebooklm table error: {_tbl_exc}]")
    # ── Slide-deck generation card (same NotebookLM visit) ───────────────────
    try:
        _print_slide_deck_card(book_dir)
    except Exception as _card_exc:
        _info(f"  [slide-deck card error: {_card_exc}]")
    # ─────────────────────────────────────────────────────────────────────────
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
    from _notebooklm_table import build_slide_deck_card  # noqa: PLC0415

    lines = build_slide_deck_card(book_dir)
    if not lines:
        return
    _info("")
    for line in lines:
        _info(line)


def _print_notebooklm_table(book_dir: Path) -> None:
    """Print the NotebookLM upload table at finalize halt.

    Reuses discovery + formatting helpers from assemble_bundle.py.
    Prints per-episode rows: EP | Title | Upload source | Customize paste |
    NotebookLM Format setting | Length setting.
    """
    try:
        # Import helpers from sibling script (same scripts/podcast/ parent).
        parent = Path(__file__).resolve().parents[1]
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        from assemble_bundle import (  # noqa: PLC0415
            _load_episode_map,
            _load_contract,
            _resolve_chapter_file,
            _resolve_framing_file,
        )
        from _notebooklm_table import (  # noqa: PLC0415
            UploadRow, render_upload_table_lines, repo_rel_href,
            load_density_lengths, length_for_episode,
        )
    except ImportError as exc:
        _info(f"  [notebooklm table skipped — import error: {exc}]")
        return

    # Per-episode Length from the density plan when one exists (else "Long").
    _density_lengths = load_density_lengths(book_dir)

    mapping = _load_episode_map(book_dir)
    if not mapping:
        # Fallback: discover directly from episodes/ + chapters/ directories.
        # Covers books where Phase 0g hasn't generated the map yet (e.g.
        # manually authored episodes outside the orchestrator flow).
        import re as _re
        ep_pat = _re.compile(r"^(EP(\d+)-(.*))\.txt$")
        ep_dir = book_dir / "episodes"
        if not ep_dir.exists():
            _info("  [notebooklm table skipped — no episodes/ directory found]")
            return
        for ep_file in sorted(ep_dir.glob("EP*.txt")):
            m = ep_pat.match(ep_file.name)
            if not m:
                continue
            ep_slug, ep_num_str, ch_slug = m.group(1), m.group(2), m.group(3)
            mapping.append({"episode": ep_slug, "chapter": f"ch{ep_num_str}-{ch_slug}",
                            "n": int(ep_num_str)})
    if not mapping:
        _info("  [notebooklm table skipped — no episodes found]")
        return

    rows: list[UploadRow] = []
    for entry in mapping:
        episode_slug = entry["episode"]
        chapter_slug = entry["chapter"]
        ep_num = entry["n"]
        contract = _load_contract(book_dir, chapter_slug)
        episode_format = contract.get("episode_format", "deep_dive")
        title = contract.get("title", episode_slug).strip("\"'")
        chapter_path = _resolve_chapter_file(book_dir, chapter_slug)
        framing_path = _resolve_framing_file(book_dir, episode_slug)
        _si = contract.get("session_index")
        rows.append(UploadRow(
            n=ep_num,
            chapter_title=title,
            episode_title=title,
            episode_format=episode_format,
            length=length_for_episode(book_dir, ep_num, _density_lengths),
            chapter_href=repo_rel_href(chapter_path, book_dir),
            episode_href=repo_rel_href(framing_path, book_dir),
            session_index=_si if isinstance(_si, int) else None,
            session_title=contract.get("session_title")
                if isinstance(contract.get("session_title"), str) else None,
        ))

    _info("─" * 72)
    _info("NOTEBOOKLM UPLOAD TABLE")
    _info("")
    _info("Per row: click the CHAPTER cell to open the SOURCE to upload, and the")
    _info("EPISODE cell to open the FRAMING to paste into NotebookLM's Customize box.")
    _info("")
    for line in render_upload_table_lines(rows):
        _info(f"  {line}")
