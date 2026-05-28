"""phases/publish_driver.py — _drive_publish_through_done.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Fires after the finalize halt: publish → trainer → merge → done.
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


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _drive_publish_through_done(book_dir: Path) -> int:
    """Run publish → trainer → merge → done after the finalize halt is cleared.

    Failure at any step halts with state pointing at the failing phase. Each
    step is idempotent enough to resume from the last failure point.
    """
    book_slug = book_dir.name

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
