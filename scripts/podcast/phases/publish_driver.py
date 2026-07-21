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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _authoring import AuthoringError, invoke_trainer
from _progress import update_phase
from _subprocess import err as _err
from _subprocess import info as _info
from _subprocess import run as _run

from phases.book_driver import _drive_book_branch
from phases.merge import phase_merge_to_develop
from phases.scaffold import phase_git_commit


def _drive_publish_through_done(book_dir: Path) -> int:
    """Run 0book-* → publish → trainer → merge → done after the finalize halt is cleared.

    Phase order: PDF companion-book generation first (so the book is built from
    finalize-approved content), then publish both deliverables together.
    Failure at any step halts with state pointing at the failing phase. Each
    step is idempotent enough to resume from the last failure point.
    """
    book_slug = book_dir.name

    # Audio ingest — self-correcting normalize + Azure-transcribe of dropped
    # NotebookLM audio. No-op `skipped` for autonomous/ElevenLabs books; a clean
    # HALT (rc 3) when audio isn't dropped yet, mirroring the slide-import
    # convention (BEFORE the book branch so the book is built once audio exists).
    # --resume re-enters idempotently.
    from phases.audio_ingest_driver import drive_audio_ingest

    _ai_outcome, _ai_rc = drive_audio_ingest(book_dir)
    if _ai_outcome == "halted":
        return 0
    if _ai_outcome == "failed":
        return _ai_rc

    # PDF path — companion book (gated by series.enable_book_branch, non-blocking).
    # Runs here, AFTER the finalize halt, so the book is always generated from
    # podcast content that has already passed the quality review gate. A book-branch
    # FAILURE is non-blocking and never prevents the podcast from publishing —
    # but a slide-import HALT (rc=3: NotebookLM deck PDFs not yet dropped) stops
    # BEFORE publish, mirroring the finalize-halt convention; --resume re-enters.
    if _drive_book_branch(book_dir) == 3:
        return 0

    # Surface the reading-edition verdict before publish so a broken companion
    # book is visible at the one place a human reviews the ship — even though it
    # does not block the podcast (companion deliverable, by design).
    _bv_path = book_dir / "_system" / "book-validation-report.json"
    if _bv_path.exists():
        try:
            import json as _json

            _bv = _json.loads(_bv_path.read_text())
            if _bv.get("verdict") == "BOOK-BROKEN":
                _err(f"reading edition is BROKEN (podcast still ships): {_bv.get('summary')}")
            elif _bv.get("verdict") == "UNKNOWN":
                # Neither sound nor broken: the gate that would have said crashed.
                # Without this branch the loop printed nothing at all, which reads
                # exactly like a book that was never built.
                _err(f"reading edition is UNVERIFIED — the validation gate crashed: {_bv.get('error')}")
            elif _bv.get("verdict") == "BOOK-SOUND":
                _info(f"reading edition verdict: SOUND — {_bv.get('summary')}")
        except Exception:
            pass

    _info("phase: publish · copy clean chapters + episodes to published/")
    update_phase(book_dir, phase="publish", status="running")
    publish_script = Path(__file__).resolve().parents[1] / "publish_to_library.py"
    rc, pout, perr = _run([sys.executable, str(publish_script), book_slug])
    print(pout)
    if rc != 0:
        update_phase(
            book_dir,
            phase="publish",
            status="failed",
            error="publish_to_library.py rc != 0; gates re-ran defensively",
            extras={"publisher_stdout": pout[-2000:], "publisher_stderr": perr[-1000:]},
        )
        _err(
            "publish failed — defensive gate re-run blocked the copy. "
            "Investigate and re-invoke `orchestrate_book.py --resume`."
        )
        return 2
    update_phase(book_dir, phase="publish", status="completed")
    phase_git_commit(book_dir, f"podcast({book_slug}): published to library")

    _info("phase: trainer · invoke podcast-trainer on the book branch")
    update_phase(book_dir, phase="trainer", status="running")
    try:
        invoke_trainer(book_dir)
    except AuthoringError as e:
        update_phase(
            book_dir,
            phase="trainer",
            status="failed",
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
