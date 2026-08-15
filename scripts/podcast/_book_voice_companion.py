"""_book_voice_companion.py — the author-companion re-voice pass.

Split out of `_book_voice.py` purely to stay under the DR-005 600-line cap
(the same seam that already produced `_book_voice_gates.py` and
`_book_voice_windows.py`) — `apply_author_companion_voice` and its default
LLM adapter `_revoice_chapter` are self-contained and only depend on
`_run_pass` from `_book_voice`, so they can live here without the rest of
`_book_voice.py` needing to know. Re-exported from `_book_voice` so every
existing `from _book_voice import apply_author_companion_voice` keeps
working.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _authoring._core import AuthoringError, _run_claude_p_with_retry, pure_text_call_options
from _book_edits import edited_chapter_keys
from _book_pass_reports import load_prior_records, merge_records, restamp_counts
from _book_voice_prompts import _voice_prompt
from _pipeline_flags import narrative_frame, narrator_subject

_VOICE_TIMEOUT = 900


def _revoice_chapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns re-voiced prose or ''."""
    rc, out, err = _run_claude_p_with_retry(
        _voice_prompt(title, base_text, previous_tail, frame=frame, narrator=narrator),
        timeout=_VOICE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-voice",
        step=label,
        log=log,
        **pure_text_call_options(),
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-voice",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run 0book-voice; each chapter is idempotent.",
        )
    return (out or "").strip()


def apply_author_companion_voice(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    revoicer: Callable[..., str] | None = None,
    only: Sequence[int] | None = None,
) -> Path:
    """Re-voice each chapter of ``book/book.md`` into author-companion register.

    ``revoicer`` defaults to the real LLM call; tests inject a fake. A window that
    fails any fidelity gate is reverted to its faithful base; chapters longer than
    ``_LONG_CHAPTER_WORDS`` are split into windows first, so one bad passage no
    longer reverts a whole chapter. ``only`` restricts the pass to the given 1-based
    section numbers — use it to re-run a chapter without re-voicing (and thereby
    degrading) the ones already done. Editorial asides are preserved untouched, as
    are chapters authored in the Book Composer unless ``force``. Returns the
    book.md path.
    """
    from _book_voice import _run_pass  # deferred: _book_voice imports this module too

    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-voice",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before 0book-voice.",
        )
    frame = narrative_frame(book_dir)
    subject = narrator_subject(book_dir)
    log(f"    0book-voice: narrative frame = {frame}")
    new_text, records = _run_pass(
        book_md,
        revoicer or _revoice_chapter,
        log=log,
        noun="voice",
        label_prefix="voice",
        only=only,
        frame=frame,
        narrator_subject=subject,
        force=force,
    )
    book_md.write_text(new_text, encoding="utf-8")
    report_path = book_dir / "_system" / "book-voice-report.json"
    records = merge_records(load_prior_records(report_path), records, edited_keys=edited_chapter_keys(book_dir))
    # Same single counter as the fluency report — see restamp_counts().
    report = {
        "schema": "",
        "narrative_frame": frame,
        "revoiced": 0,
        "reverted": 0,
        "overwritten_by_replay": 0,
        "chapters": records,
    }
    restamp_counts(report, records, schema="podcast.book-voice/v5", count_key="revoiced")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"    0book-voice: {report['revoiced']} chapters re-voiced, {report['reverted']} reverted to base")
    return book_md
