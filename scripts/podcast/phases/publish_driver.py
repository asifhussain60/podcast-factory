"""phases/publish_driver.py — _drive_publish_through_done.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Fires after the finalize halt: 0book-* (PDF path) → publish → trainer → merge → done.

The PDF companion-book path (0book-design → 0book-compose → 0book-illustrate →
0book-render) runs HERE, after the finalize halt, not before it. This ensures that
any podcast quality issues caught and fixed at the finalize review gate are already
resolved before the book branch is generated. The two deliverables (podcast +
reading edition) stay in sync because the book is always built from reviewed,
finalize-approved chapter content.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import update_phase  # noqa: E402
from _authoring import AuthoringError, invoke_trainer  # noqa: E402
from phases.scaffold import phase_git_commit  # noqa: E402
from phases.merge import phase_merge_to_develop  # noqa: E402
from phases.book_driver import _drive_book_branch  # noqa: E402


from _subprocess import run as _run, err as _err, info as _info  # noqa: E402


def _drive_publish_through_done(book_dir: Path) -> int:
    """Run 0book-* → publish → trainer → merge → done after the finalize halt is cleared.

    Phase order: PDF companion-book generation first (so the book is built from
    finalize-approved content), then publish both deliverables together.
    Failure at any step halts with state pointing at the failing phase. Each
    step is idempotent enough to resume from the last failure point.
    """
    book_slug = book_dir.name

    # PDF path — companion book (gated by series.enable_book_branch, non-blocking).
    # Runs here, AFTER the finalize halt, so the book is always generated from
    # podcast content that has already passed the quality review gate. A book-branch
    # failure is non-blocking and never prevents the podcast from publishing.
    _drive_book_branch(book_dir)

    _info("phase: publish · copy clean chapters + episodes to published/")
    update_phase(book_dir, phase="publish", status="running")
    publish_script = Path(__file__).resolve().parents[1] / "publish_to_library.py"
    rc, pout, perr = _run([sys.executable, str(publish_script), book_slug])
    print(pout)
    if rc != 0:
        update_phase(book_dir, phase="publish", status="failed",
                     error="publish_to_library.py rc != 0; gates re-ran defensively",
                     extras={"publisher_stdout": pout[-2000:], "publisher_stderr": perr[-1000:]})
        _err("publish failed — defensive gate re-run blocked the copy. "
             "Investigate and re-invoke `orchestrate_book.py --resume`.")
        return 2
    update_phase(book_dir, phase="publish", status="completed")
    phase_git_commit(book_dir, f"podcast({book_slug}): published to library")

    _info("phase: trainer · invoke podcast-trainer on the book branch")
    update_phase(book_dir, phase="trainer", status="running")
    try:
        invoke_trainer(book_dir)
    except AuthoringError as e:
        update_phase(
            book_dir, phase="trainer", status="failed",
            error=str(e),
            extras={"manual_fallback": e.manual_fallback},
        )
        _err(f"trainer pass failed (non-fatal): {e}")
    else:
        update_phase(book_dir, phase="trainer", status="completed")

    _info("phase: merge · book branch → develop")
    update_phase(book_dir, phase="merge", status="running")
    try:
        phase_merge_to_develop(book_slug)
    except RuntimeError as e:
        update_phase(book_dir, phase="merge", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="merge", status="completed")
    update_phase(book_dir, phase="done", status="completed")

    _info("")
    _info("─" * 72)
    _info(f"Book {book_slug}: SHIPPED.")
    _info("─" * 72)
    return 0
