"""_halt_advisories.py — what the finalize halt tells a human, and nothing else.

The finalize halt is the one moment a person reads a book before it goes out, so
it has become the place every non-blocking signal wants to surface. Each of those
blocks is the same shape — read a sidecar, print a heading, print lines, never
fail the halt over its own advisory — and each was being written inline in
``phases/chapter_driver.py``, a file the line-count gate has grandfathered and
which may shrink but never grow. That constraint is doing real work here: it
forces the halt to stay a caller of advisory emitters rather than becoming their
container.

Every function is failure-swallowing on purpose. A halt that dies while printing
an optional note has turned a passing book into a failed run, which is strictly
worse than the note going unread.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def emit_transcription_advisories(book_dir: Path, info: Callable[[str], None]) -> None:
    """Flags ``transcribe_audio_book.py`` records but nothing used to read.

    Duplicate ratio, empty/short segments, native-script leakage, normalization
    substitutions. They were written into orchestrator state and never surfaced,
    so a reviewer never saw them.
    """
    try:
        state = Path(book_dir) / "_system" / "orchestrator-state.json"
        flags = json.loads(state.read_text(encoding="utf-8")).get("transcription_flags") if state.exists() else None
        if not isinstance(flags, dict) or not flags:
            return
        info("")
        info("Transcription advisories (audio path — review, non-blocking):")
        for key, value in flags.items():
            info(f"  · {key}: {value}")
    except Exception:
        pass


def emit_decision_ledger(book_dir: Path, info: Callable[[str], None]) -> None:
    """The forks the run settled on the author's behalf.

    An autonomous pipeline that never stops to ask has to disclose instead. See
    ``_book_decisions`` for why these are kept apart from findings: a finding is
    something wrong, a decision is something settled, and mixing them drowns the
    defects.
    """
    try:
        from _book_decisions import render_decisions

        rendered = render_decisions(Path(book_dir))
        if not rendered:
            return
        info("")
        info("Calls the edition made for you (review, non-blocking):")
        for line in rendered.splitlines():
            info(f"  {line}" if line else "")
    except Exception:
        pass
