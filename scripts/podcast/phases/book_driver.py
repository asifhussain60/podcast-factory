"""phases/book_driver.py — _drive_book_branch (PDF path).

Runs the companion-book phases (0book-design → 0book-compose → 0book-render)
AFTER the finalize halt, inside publish_driver._drive_publish_through_done.
This ensures the book is always generated from podcast content that has already
passed the finalize quality review gate — any issues fixed at review are already
resolved before the book branch runs. Gated on meta.yml `series.enable_book_branch`
(opt-in). NON-BLOCKING: a book-phase failure is recorded but never aborts the
podcast ship — the book is a companion deliverable, not a gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _progress import update_phase  # noqa: E402
from _authoring import AuthoringError  # noqa: E402
from _authoring._book_design import author_phase_book_design  # noqa: E402
from _book_compose import author_phase_book_compose  # noqa: E402
from _book_illustrate import author_phase_book_illustrate  # noqa: E402
from phases.scaffold import phase_git_commit  # noqa: E402

_BOOK_PHASES = ("0book-design", "0book-compose", "0book-illustrate", "0book-render")


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _book_branch_enabled(book_dir: Path) -> bool:
    meta = book_dir / "meta.yml"
    if not meta.exists():
        return False
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        return bool(data.get("series", {}).get("enable_book_branch", False))
    except Exception:  # noqa: BLE001
        return False


def _drive_book_branch(book_dir: Path) -> int:
    """Design → compose → render the companion book. Always returns 0 (non-blocking):
    the podcast pipeline continues to finalize regardless of book-branch outcome."""
    book_dir = Path(book_dir).resolve()
    slug = book_dir.name

    if not _book_branch_enabled(book_dir):
        for ph in _BOOK_PHASES:
            update_phase(book_dir, phase=ph, status="skipped")
        _info("book branch: series.enable_book_branch is false — skipped")
        return 0

    # 0book-design
    update_phase(book_dir, phase="0book-design", status="running")
    try:
        author_phase_book_design(book_dir, log=_info)
    except AuthoringError as e:
        update_phase(book_dir, phase="0book-design", status="failed", error=str(e),
                     extras={"manual_fallback": e.manual_fallback})
        _err(f"0book-design failed (non-blocking): {e}")
        return 0
    update_phase(book_dir, phase="0book-design", status="completed")
    phase_git_commit(book_dir, f"book({slug}): 0book-design — book-toc.json")

    # 0book-compose
    update_phase(book_dir, phase="0book-compose", status="running")
    try:
        author_phase_book_compose(book_dir, log=_info)
    except AuthoringError as e:
        update_phase(book_dir, phase="0book-compose", status="failed", error=str(e),
                     extras={"manual_fallback": e.manual_fallback})
        _err(f"0book-compose failed (non-blocking): {e}")
        return 0
    update_phase(book_dir, phase="0book-compose", status="completed")
    phase_git_commit(book_dir, f"book({slug}): 0book-compose — book.md")

    # 0book-illustrate: teaching diagrams -> book-illustrated.md (non-blocking on failure)
    update_phase(book_dir, phase="0book-illustrate", status="running")
    try:
        author_phase_book_illustrate(book_dir, log=_info)
    except AuthoringError as e:
        update_phase(book_dir, phase="0book-illustrate", status="failed", error=str(e),
                     extras={"manual_fallback": e.manual_fallback})
        _err(f"0book-illustrate failed (non-blocking): {e}")
        # Continue to render even without illustrations — book.md still renders fine.
    else:
        update_phase(book_dir, phase="0book-illustrate", status="completed")
        phase_git_commit(book_dir, f"book({slug}): 0book-illustrate — book-illustrated.md")

    # 0book-render (PDF + reader HTML) — task 5 module; degrade gracefully until present.
    update_phase(book_dir, phase="0book-render", status="running")
    try:
        from build_book_pdf import build_book  # lazy: render module lands in task 5
    except ImportError:
        update_phase(book_dir, phase="0book-render", status="pending",
                     error="render module (build_book_pdf) not yet available")
        _info("0book-render: build_book_pdf pending — book.md ready, PDF deferred")
        return 0
    try:
        build_book(book_dir, log=_info)
    except (AuthoringError, RuntimeError) as e:
        update_phase(book_dir, phase="0book-render", status="failed", error=str(e))
        _err(f"0book-render failed (non-blocking): {e}")
        return 0
    update_phase(book_dir, phase="0book-render", status="completed")
    phase_git_commit(book_dir, f"book({slug}): 0book-render — book.pdf")
    return 0
