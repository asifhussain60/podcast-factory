"""phases/chapter_driver.py — _drive_per_chapter_and_after.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Drives the per-chapter convergence loop, Phase 0g, slide decks, and the
finalize halt. Called by resume_dispatcher after Phase 0f approval.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import read_state, update_phase  # noqa: E402
from _convergence import ChapterOutcome, render_outcome  # noqa: E402
from phases.preflight import _sweep_orphan_episode_drafts  # noqa: E402
from phases.per_chapter import per_chapter_pass  # noqa: E402
from phases.series_plan import _series_numeric, _series_flag, _chapter_cost_so_far  # noqa: E402
from phases.series_plan import phase_0g_register  # noqa: E402
from phases.bundle_audit import phase_0g_audit_bundles  # noqa: E402
from phases.scaffold import phase_git_commit  # noqa: E402


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _phase_boundary_gate(book_dir: Path, boundary_name: str,
                         projected_cost_usd: float | None = None) -> None:
    _info(
        f"[phased_rollout] phase boundary: {boundary_name}"
        + (f" (projected cost: ${projected_cost_usd:.2f})" if projected_cost_usd else "")
    )


def _drive_per_chapter_and_after(book_dir: Path) -> int:
    """After Phase 0f approval: drive per-chapter loop → 0g → finalize halt."""
    book_slug = book_dir.name
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

    for slug in chapter_slugs:
        if slug in completed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · already shipped, skipping")
            continue
        if slug in failed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · prior FAILED, skipping (use --retry-chapter to re-attempt)")
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
        outcome = per_chapter_pass(book_dir, slug)
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
        if outcome.final_verdict == "FAILED":
            failed_chapter_slugs.add(slug)
            update_phase(
                book_dir,
                phase="per-chapter",
                status="running",
                extras={
                    "completed_slugs": sorted(completed_chapter_slugs),
                    "failed_slugs": sorted(failed_chapter_slugs),
                    "chapter_timings": chapter_timings,
                },
            )
            _err(f"chapter {slug} failed; continuing to next chapter (F33-second graceful-degrade).")
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
    _info("When satisfied, authorize publish + trainer + merge:")
    _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
    _info("─" * 72)
    return 0
