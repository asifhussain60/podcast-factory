"""Driver for reader-narration, after the reading edition exists and before publish."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _progress import update_phase
from _subprocess import err as _err
from _subprocess import info as _info
from reader_narration import render_reader_narration

from phases.scaffold import phase_git_commit


def drive_reader_narration(book_dir: Path) -> tuple[str, int]:
    book_dir = Path(book_dir).resolve()
    update_phase(book_dir, phase="reader-narration", status="running")
    try:
        result = render_reader_narration(book_dir)
    except Exception as exc:
        update_phase(book_dir, phase="reader-narration", status="failed", error=str(exc))
        _err(f"reader narration failed: {exc}")
        return "failed", 2

    extras = {
        "rendered": result.rendered,
        "skipped": result.skipped,
        "chars": result.chars,
        "failed": result.failed,
    }
    if result.outcome == "skipped":
        update_phase(
            book_dir,
            phase="reader-narration",
            status="skipped",
            extras={**extras, "reason": result.reason},
        )
        _info(f"reader narration skipped: {result.reason}")
        return "skipped", 0

    # A chapter that could not be synthesised now fails ITS OWN chapter rather
    # than raising out of the whole render, so the chapters already recorded are
    # kept and the run is resumable. For the orchestrator that must still be a
    # FAILED phase: this is the unattended pipeline, and a book that publishes
    # with a chapter silently unnarrated is exactly what the halt is for. The
    # Composer's publish makes the opposite call deliberately — see
    # publish_to_production.narrate.
    if result.failed:
        update_phase(
            book_dir,
            phase="reader-narration",
            status="failed",
            error=f"{len(result.failed)} chapter(s) could not be synthesised: {', '.join(result.failed)}",
            extras=extras,
        )
        _err(f"reader narration failed for {len(result.failed)} chapter(s): {', '.join(result.failed)}")
        return "failed", 2

    update_phase(book_dir, phase="reader-narration", status="completed", extras=extras)
    if result.rendered:
        phase_git_commit(book_dir, f"podcast({book_dir.name}): render reader narration")
    _info(f"reader narration ready: {len(result.rendered)} rendered, {len(result.skipped)} already current")
    return "completed", 0
