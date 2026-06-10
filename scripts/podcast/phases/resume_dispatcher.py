"""phases/resume_dispatcher.py — run_resume: resume an in-flight orchestrator run.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import read_state, write_state, update_phase, is_phase_stale, STALE_RUNNING_SEC, PHASES  # noqa: E402
from cost_guard import cost_ceiling_check  # noqa: E402
from phases.preflight import preflight_resume  # noqa: E402
from phases.initial_driver import _drive_authoring_through_0f, _drive_source_ready_through_0f  # noqa: E402
from phases.chapter_driver import _drive_per_chapter_and_after  # noqa: E402
from phases.publish_driver import _drive_publish_through_done  # noqa: E402


from _subprocess import err as _err, info as _info  # noqa: E402


def _book_dir(book_slug: str) -> Path | None:
    from _paths import find_content as _find
    found = _find(book_slug)
    return found[2] if found else None


def _read_book_title_local(book_dir: Path) -> str | None:
    """Best-effort title extraction from BOOK_DIR/_README.md."""
    readme = book_dir / "_README.md"
    if not readme.exists():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# Podcast — "):
            return line[len("# Podcast — "):].strip()
    return None


def _clear_downstream_phases(state: dict, retry_phase: str, log=_info) -> None:
    """Reset retry_phase + every canonical phase after it to 'pending'.

    A retried phase invalidates all later artifacts; a stale "completed"
    block (e.g. per-chapter on a finished book) would make the re-run skip
    re-authoring downstream and silently no-op. per-chapter additionally
    gets its completion ledgers emptied.
    """
    block = state["phases"][retry_phase]
    block["status"] = "pending"
    block.pop("ts_completed", None)
    block.pop("manual_fallback", None)
    state["phase"] = retry_phase
    state["phase_status"] = "pending"
    if retry_phase in PHASES:
        idx = PHASES.index(retry_phase)
        for later in PHASES[idx + 1:]:
            lb = state["phases"].get(later)
            if not isinstance(lb, dict):
                continue
            if lb.get("status") in ("completed", "failed", "halted", "skipped"):
                log(f"  --retry-phase: clearing downstream {later} (was {lb.get('status')})")
                lb["status"] = "pending"
                lb.pop("ts_completed", None)
                lb.pop("manual_fallback", None)
            if later == "per-chapter":
                for key in ("completed_slugs", "failed_slugs"):
                    if lb.get(key):
                        lb[key] = []
                if lb.get("chapter_timings"):
                    lb["chapter_timings"] = {}
        i = PHASES.index(retry_phase)
        state["last_completed_phase"] = PHASES[i - 1] if i > 0 else None


def run_resume(args: argparse.Namespace) -> int:
    slug = args.resume
    _info(f"orchestrate_book: resume — slug={slug}")
    book_dir, fails = preflight_resume(slug)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    assert book_dir is not None
    state = read_state(book_dir)
    if state is None:
        _err("state file missing despite pre-flight pass — abort")
        return 2

    stop_after = getattr(args, "stop_after", None)
    retry_phase = getattr(args, "retry_phase", None)
    if retry_phase:
        if retry_phase not in state.get("phases", {}):
            _err(f"--retry-phase: unknown phase {retry_phase!r}. Known: {sorted(state.get('phases', {}).keys())}")
            return 1
        _info(f"  --retry-phase {retry_phase}: resetting status to 'pending'")
        _clear_downstream_phases(state, retry_phase)
        write_state(book_dir, state)
        state = read_state(book_dir) or state

    last = state.get("last_completed_phase") or ""
    current_phase = state.get("phase") or ""
    current_status = state.get("phase_status") or ""

    _info(f"  last completed:  {last or '(none)'}")
    _info(f"  current phase:   {current_phase}  [{current_status}]")

    # Stale-resume auto-recovery: an unclean shutdown freezes phase_status at
    # "running", which the early-phase handlers (0a/0f/06a) refuse to re-enter,
    # deadlocking --resume. If the running state is older than the staleness
    # threshold it belongs to a dead process (the book lock guards against a
    # genuinely concurrent run), so downgrade to "failed" — the same recovery
    # the shell watchdog performs via --retry-phase — and persist it so the
    # existing per-phase resume handlers pick it up.
    if is_phase_stale(state):
        _info(
            f"  stale 'running' state detected (older than {STALE_RUNNING_SEC}s) "
            f"— auto-recovering: downgrading {current_phase!r} to 'failed'."
        )
        state["phase_status"] = "failed"
        block = state.get("phases", {}).get(current_phase)
        if isinstance(block, dict) and block.get("status") == "running":
            block["status"] = "failed"
        write_state(book_dir, state)
        current_status = "failed"

    # 2026-05-28 R4 guard: any phase halted at a human-review gate must not be
    # re-entered by the hourly launchd tick.  The Source Review Gate (Phase 06a,
    # Wave I) sets phase_status="awaiting_human_review".  Return exit-code 3
    # (same as the 0f manual-resume convention) so the caller knows to wait.
    if current_status == "awaiting_human_review":
        gate_file = book_dir / "_system" / "review-gate.json"
        approved = False
        if gate_file.exists():
            try:
                import json as _json
                gate = _json.loads(gate_file.read_text())
                approved = bool(gate.get("approved"))
            except Exception:
                pass
        if not approved:
            _info(
                f"Phase {current_phase!r} is awaiting human review. "
                f"Approve via the astro site Book Review view or "
                f"CLI: python3 scripts/podcast/approve_book.py <slug>"
            )
            return 3
        # Approval flag is set — clear the status and fall through to normal
        # resume logic so the phase's completion handler picks up.
        state["phase_status"] = "pending"
        write_state(book_dir, state)
        _info(f"Phase {current_phase!r} human review approved — resuming.")
        current_status = "pending"

    # C4: per-book REAL-MONEY ceiling. Checked on every resume before dispatching
    # the next (possibly Azure/Gemini) phase. Max/claude -p spend is excluded, so
    # all-Max authoring never trips it. Hard cap halts; soft cap warns.
    _cc = cost_ceiling_check(book_dir)
    if _cc["action"] == "halt":
        update_phase(
            book_dir,
            phase=current_phase or "per-chapter",
            status="failed",
            error=(
                f"COST-CEILING: real spend ${_cc['real_spend_usd']:.2f} >= hard cap "
                f"${_cc['hard']:.2f}. Raise config.cost_cap_hard (or set 0 to disable)."
            ),
        )
        _err(
            f"COST-CEILING halt: real spend ${_cc['real_spend_usd']:.2f} >= hard cap "
            f"${_cc['hard']:.2f}. Raise state.config.cost_cap_hard and --resume."
        )
        return 2
    if _cc["action"] == "warn":
        _err(
            f"COST-CEILING warning: real spend ${_cc['real_spend_usd']:.2f} >= soft cap "
            f"${_cc['soft']:.2f} (hard ${_cc['hard']:.2f})."
        )

    # ── source-ready: pre-written English sources (explainers, sites) ───────────
    # Handles books whose source material was written directly as .md files rather
    # than ingested from a PDF via Azure OCR. Category must be in SKIP_OCR_CATEGORIES.
    if current_phase == "source-ready" and current_status in ("pending", "failed"):
        category = state.get("category", "")
        from _authoring._core import SKIP_OCR_CATEGORIES
        if not category:
            _err(
                "orchestrator-state.json is missing 'category' field. "
                "Add: \"category\": \"explainers\"  (or \"sites\") and retry."
            )
            return 2
        if category not in SKIP_OCR_CATEGORIES:
            _err(
                f"phase 'source-ready' requires category in SKIP_OCR_CATEGORIES "
                f"{sorted(SKIP_OCR_CATEGORIES)} (got {category!r}). "
                f"For PDF-sourced books use the standard initial path."
            )
            return 2
        _info(f"phase: source-ready · ingesting pre-written .md sources (category={category!r})")
        return _drive_source_ready_through_0f(book_dir, state)

    # Phase 06a approved — drive into 0f.
    if current_phase == "06a" and current_status in ("pending", "failed"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        _info("Phase 06a cleared — resuming to 0f series plan.")
        return _drive_authoring_through_0f(book_dir, title, stop_after=stop_after)

    if current_phase == "0f" and current_status in ("pending", "failed"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        _info("Phase 0f pending — writing series plan.")
        return _drive_authoring_through_0f(book_dir, title, stop_after=stop_after)

    if current_phase == "0f" and current_status == "halted":
        plan = book_dir / "_system" / "series-plan.md"
        if not plan.exists() or plan.stat().st_size == 0:
            _err(f"series-plan.md missing at {plan} — cannot resume after 0f.")
            return 2
        _info("Phase 0f gate cleared (human approved by re-invoking --resume).")
        return _drive_per_chapter_and_after(book_dir)

    if current_phase == "0a" and current_status in ("failed", "pending"):
        from phases.scaffold import phase_0a_ingest, phase_git_commit
        category = state.get("category", "books")
        source_dir = book_dir / "_system" / "source"
        pdfs = sorted(source_dir.glob("*.pdf"))
        if not pdfs:
            _err(f"No PDF found in {source_dir.relative_to(REPO_ROOT)} — cannot retry 0a.")
            return 2
        if len(pdfs) > 1:
            _err(
                f"Multiple PDFs in {source_dir.relative_to(REPO_ROOT)}: "
                f"{[p.name for p in pdfs]}. Keep one and retry."
            )
            return 2
        pdf_path = pdfs[0]
        _info(f"phase: 0a · re-running Azure ingest on {pdf_path.name}")
        update_phase(book_dir, phase="0a", status="running")
        try:
            phase_0a_ingest(book_dir, pdf_path, category, slug)
        except RuntimeError as e:
            update_phase(book_dir, phase="0a", status="failed", error=str(e))
            _err(str(e))
            return 2
        update_phase(book_dir, phase="0a", status="completed")
        phase_git_commit(book_dir, f"podcast({slug}): phase 0a Azure ingest (retry)")
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        return _drive_authoring_through_0f(book_dir, title)

    if current_phase in ("0b", "0c", "0ci", "0d", "0e", "0literary") and current_status in ("failed", "halted", "pending"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        _info(f"resuming LLM-authoring phases from {current_phase} (status={current_status})")
        return _drive_authoring_through_0f(book_dir, title, stop_after=stop_after)

    if last in ("0a",) or (last in ("0b", "0c", "0ci", "0d", "0e", "0literary") and current_status == "completed"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        return _drive_authoring_through_0f(book_dir, title, stop_after=stop_after)

    if current_phase == "per-chapter" and current_status in (
        "failed", "halted", "running", "pending"
    ):
        return _drive_per_chapter_and_after(book_dir)

    if current_phase == "per-chapter-slides" and current_status in (
        "failed", "running", "pending"
    ):
        return _drive_per_chapter_and_after(book_dir)

    if current_phase == "per-chapter-slides" and current_status == "completed":
        _info("Phase per-chapter-slides already completed — advancing to finalize.")
        return _drive_per_chapter_and_after(book_dir)

    if current_phase in ("0book-design", "0book-compose", "0book-illustrate",
                         "0book-render"):
        _info(f"Phase {current_phase} (PDF path book) — re-entering the publish driver; "
              f"the 0book phases run post-finalize and are artifact-idempotent.")
        return _drive_publish_through_done(book_dir)

    if current_phase == "0book-slide-import":
        # halted = NotebookLM deck PDFs were missing; the human has (presumably)
        # dropped them now. Re-enter the publish driver — design/compose/illustrate
        # skip on existing artifacts, slide-import re-runs its gate.
        _info(f"Phase 0book-slide-import status={current_status!r} — re-entering "
              f"the publish driver (upstream 0book phases are idempotent).")
        return _drive_publish_through_done(book_dir)

    if current_phase == "0g" and current_status == "completed":
        _info("Phase 0g already completed — advancing to finalize.")
        return _drive_per_chapter_and_after(book_dir)

    if current_phase == "0g" and current_status in ("failed", "running", "pending"):
        _info(f"Phase 0g status={current_status!r} — re-entering per-chapter-and-after driver.")
        return _drive_per_chapter_and_after(book_dir)

    if current_phase == "finalize" and current_status == "halted":
        _info("Phase finalize gate cleared (human approved by re-invoking --resume).")
        return _drive_publish_through_done(book_dir)
    if current_phase == "finalize" and current_status in ("failed", "pending"):
        return _drive_per_chapter_and_after(book_dir)

    if current_phase in ("publish", "trainer", "merge") and current_status in (
        "failed", "running", "pending"
    ):
        return _drive_publish_through_done(book_dir)

    if current_phase == "done":
        _info("This book has already shipped. Nothing to resume.")
        return 0

    _info("")
    _info(f"  No automated action for current phase '{current_phase}'. State file:")
    _info(f"    {(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}")
    return 3
