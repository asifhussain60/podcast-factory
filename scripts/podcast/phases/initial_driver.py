"""phases/initial_driver.py — run_initial + _drive_authoring_through_0f.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import initial_state, read_state, update_phase, write_state  # noqa: E402
from _authoring import AuthoringError, author_phase_0b, author_phase_0c, author_phase_0d, author_phase_0e  # noqa: E402
from phases.preflight import preflight_initial  # noqa: E402
from phases.scaffold import phase_branch, phase_scaffold, phase_0a_ingest, phase_git_commit  # noqa: E402
from phases.series_plan import phase_0f_write_series_plan  # noqa: E402
from phases.preflight import _run_chapter_set_check  # noqa: E402
from phases.source_review_gate import run_source_review_gate  # noqa: E402


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def derive_slug(pdf_path: Path) -> str:
    """Stem of the PDF, lowercased, non-alphanumeric → hyphen, collapsed."""
    import re
    stem = pdf_path.stem.lower()
    s = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return re.sub(r"-+", "-", s)


def _drive_authoring_through_0f(book_dir: Path, title: str) -> int:
    """Run Phases 0b → 0c → 0d → 0e → 0f-halt. Used by run_initial AND --resume."""
    book_slug = book_dir.name
    state = read_state(book_dir) or {}
    config = state.get("config", {})
    length_tier = config.get("length_tier", "extended")
    unit_mode = config.get("unit_mode", "auto")

    def _run_0b(bd: Path) -> None:
        author_phase_0b(bd, log=_info)

    def _run_0c(bd: Path) -> None:
        author_phase_0c(bd, log=_info)

    def _run_0d(bd: Path) -> None:
        author_phase_0d(bd, length_tier=length_tier, unit_mode=unit_mode, log=_info)

    def _run_0e(bd: Path) -> None:
        author_phase_0e(bd, log=_info)

    phase_map = [
        ("0b", _run_0b, "phase 0b English refinement (chunked)"),
        ("0c", _run_0c, "phase 0c phonetic pass (chunked)"),
        ("0d", _run_0d, f"phase 0d chapter design (tier={length_tier}, unit={unit_mode})"),
        ("0e", _run_0e, "phase 0e enrichment"),
    ]
    completed = {
        p for p, blk in state.get("phases", {}).items()
        if blk.get("status") == "completed"
    }

    for phase_id, fn, subject in phase_map:
        if phase_id in completed:
            _info(f"phase: {phase_id} · already completed, skipping")
            continue
        _info(f"phase: {phase_id} · {subject} (LLM shellout)")
        update_phase(book_dir, phase=phase_id, status="running")
        try:
            fn(book_dir)
        except AuthoringError as e:
            update_phase(book_dir, phase=phase_id, status="failed",
                         error=str(e), extras={"manual_fallback": e.manual_fallback})
            _err(f"phase {phase_id} failed: {e}")
            if e.manual_fallback:
                _err("manual fallback:")
                for line in e.manual_fallback.splitlines():
                    _err(f"  {line}")
            return 3
        update_phase(book_dir, phase=phase_id, status="completed")
        phase_git_commit(book_dir, f"podcast({book_slug}): {subject}")

        if phase_id == "0d":
            _run_chapter_set_check(book_dir, log=_info)

    # Phase 06a — source review gate (Wave I). Runs after 0e, before 0f.
    _06a_done = "06a" in completed
    if _06a_done:
        _info("phase: 06a · already completed, skipping")
    else:
        _info("phase: 06a · source review gate (Haiku companion-source review)")
        update_phase(book_dir, phase="06a", status="running")
        try:
            gate = run_source_review_gate(book_dir)
        except Exception as e:  # noqa: BLE001
            update_phase(book_dir, phase="06a", status="failed", error=str(e))
            _err(f"phase 06a failed: {e}")
            return 2
        if gate.approved:
            # Gate file already carried approved=True — mark done and fall through
            update_phase(book_dir, phase="06a", status="completed")
            _info("phase: 06a · already approved, advancing to series plan")
        else:
            # Halt for human review. update_phase stores the block with status=halted;
            # we then patch the top-level phase_status to the R4-guard sentinel value.
            update_phase(
                book_dir,
                phase="06a",
                status="halted",
                extras={"gate_warnings": len(gate.warnings)},
            )
            raw_state = read_state(book_dir) or {}
            raw_state["phase_status"] = "awaiting_human_review"
            write_state(book_dir, raw_state)
            phase_git_commit(book_dir, f"podcast({book_slug}): phase 06a source review gate — awaiting human review")
            _info("")
            _info("─" * 72)
            _info("Phase 06a complete · halted for human review.")
            _info(f"  {len(gate.warnings)} warning(s) in review-gate.json")
            _info("  Review and approve via:")
            _info(f"    http://localhost:4322/book-review/{book_slug}")
            _info(f"    python3 scripts/podcast/approve_book.py {book_slug}")
            _info("  Then resume:")
            _info(f"    python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
            _info("─" * 72)
            return 3

    _info("phase: 0f · assembling series-plan.md for human review")
    update_phase(book_dir, phase="0f", status="running")
    try:
        plan_path = phase_0f_write_series_plan(book_dir, title)
    except RuntimeError as e:
        update_phase(book_dir, phase="0f", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(
        book_dir,
        phase="0f",
        status="halted",
        extras={"series_plan_path": str(plan_path.relative_to(REPO_ROOT))},
    )
    phase_git_commit(book_dir, f"podcast({book_slug}): phase 0f series plan written; awaiting human review")

    _info("")
    _info("─" * 72)
    _info(f"Phase 0f complete · halted for human review.")
    _info("")
    _info(f"Review the series plan:")
    _info(f"  {plan_path.relative_to(REPO_ROOT)}")
    _info("")
    _info(f"Resume when approved:")
    _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
    _info("─" * 72)
    return 0


def run_initial(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf_path).resolve()
    slug = args.slug or derive_slug(pdf_path)
    category = args.category
    title = args.title or pdf_path.stem.replace("-", " ").replace("_", " ").title()
    author = args.author

    _info(f"orchestrate_book: initial run — slug={slug} · category={category}")
    fails = preflight_initial(pdf_path, slug, category)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    _info("pre-flight: OK")
    from _branching import branch_name as _branch_name
    _expected = _branch_name(category, slug)
    _info(f"phase: branch · creating {_expected}")
    try:
        phase_branch(slug, category)
    except RuntimeError as e:
        _err(str(e))
        return 2

    _info(f"phase: scaffold · {category}/{slug}")
    try:
        book_dir = phase_scaffold(category, slug, title, author)
    except RuntimeError as e:
        _err(str(e))
        return 2

    state = initial_state(slug, category)
    state["config"] = {
        "length_tier": args.length_tier,
        "unit_mode": args.unit_mode,
    }
    write_state(book_dir, state)
    update_phase(book_dir, phase="pre-flight", status="completed")
    update_phase(book_dir, phase="branch",     status="completed")
    update_phase(book_dir, phase="scaffold",   status="completed",
                 extras={"book_dir": str(book_dir.relative_to(REPO_ROOT))})
    phase_git_commit(book_dir, f"podcast({slug}): scaffold book directory")

    _info(f"phase: 0a · Azure OCR + Translation on {pdf_path.name}")
    update_phase(book_dir, phase="0a", status="running")
    try:
        phase_0a_ingest(book_dir, pdf_path, category, slug)
    except RuntimeError as e:
        update_phase(book_dir, phase="0a", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="0a", status="completed")
    phase_git_commit(book_dir, f"podcast({slug}): phase 0a Azure ingest")

    return _drive_authoring_through_0f(book_dir, title)
