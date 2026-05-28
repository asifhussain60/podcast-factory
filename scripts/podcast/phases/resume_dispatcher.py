"""phases/resume_dispatcher.py — run_resume: resume an in-flight orchestrator run.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import read_state, write_state, update_phase  # noqa: E402
from phases.preflight import preflight_resume  # noqa: E402
from phases.initial_driver import _drive_authoring_through_0f  # noqa: E402
from phases.chapter_driver import _drive_per_chapter_and_after  # noqa: E402
from phases.publish_driver import _drive_publish_through_done  # noqa: E402


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


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

    retry_phase = getattr(args, "retry_phase", None)
    if retry_phase:
        if retry_phase not in state.get("phases", {}):
            _err(f"--retry-phase: unknown phase {retry_phase!r}. Known: {sorted(state.get('phases', {}).keys())}")
            return 1
        _info(f"  --retry-phase {retry_phase}: resetting status to 'pending'")
        block = state["phases"][retry_phase]
        block["status"] = "pending"
        block.pop("ts_completed", None)
        block.pop("manual_fallback", None)
        state["phase"] = retry_phase
        state["phase_status"] = "pending"
        order = ("0b", "0c", "0d", "0e")
        if retry_phase in order:
            idx = order.index(retry_phase)
            for later in order[idx + 1:]:
                lb = state["phases"].get(later, {})
                if lb.get("status") == "completed":
                    _info(f"  --retry-phase: clearing downstream {later} (was completed)")
                    lb["status"] = "pending"
                    lb.pop("ts_completed", None)
        canonical = ("pre-flight", "branch", "scaffold", "0a", "0b", "0c", "0d", "0e",
                     "0f", "0g", "per-chapter", "per-chapter-slides", "finalize",
                     "publish", "trainer", "merge", "done")
        if retry_phase in canonical:
            i = canonical.index(retry_phase)
            state["last_completed_phase"] = canonical[i - 1] if i > 0 else None
        write_state(book_dir, state)
        state = read_state(book_dir) or state

    last = state.get("last_completed_phase") or ""
    current_phase = state.get("phase") or ""
    current_status = state.get("phase_status") or ""

    _info(f"  last completed:  {last or '(none)'}")
    _info(f"  current phase:   {current_phase}  [{current_status}]")

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

    if current_phase in ("0b", "0c", "0d", "0e") and current_status in ("failed", "halted", "pending"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        _info(f"resuming LLM-authoring phases from {current_phase} (status={current_status})")
        return _drive_authoring_through_0f(book_dir, title)

    if last in ("0a",) or (last in ("0b", "0c", "0d", "0e") and current_status == "completed"):
        title = _read_book_title_local(book_dir) or slug.replace("-", " ").title()
        return _drive_authoring_through_0f(book_dir, title)

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
