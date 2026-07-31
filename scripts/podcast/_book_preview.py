"""_book_preview.py — build the reading edition at the finalize halt, not after publish.

The book lane has always run inside ``publish_driver``, after the finalize halt and
after ``audio-ingest``. The comment there says it runs late "so the book is always
generated from podcast content that has already passed the quality review gate" —
but its actual input is ``_system/source/text/refined-english.md``, written back at
phase 0b. The lane never depended on the audio; it was only ORDERED after it.

The cost of that ordering is that a human reviewing a book at the finalize halt sees
the chapters and the slide-deck prompts but an empty ``book/`` folder, and the
Composer — the one place figures may be placed — has nothing to open. The articulated
PDF only appears after a NotebookLM round trip that has nothing to do with it.

So: build it here, when it can be built without waiting on a human artifact.

The guard is exactly that condition, not a flag. Under ``book_visuals=manual_only``
(the default since 2026-07-31) the illustrate and slide-import phases are skipped
outright, so the lane has no halt in it and runs clean to a PDF. Under an explicit
``book_visuals: pipeline`` the lane WILL stop for dropped NotebookLM decks, so this
declines and leaves it where it has always been — the late call in ``publish_driver``
is untouched and still runs for every book.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pipeline_flags import BOOK_VISUALS_MANUAL_ONLY, book_visuals
from _progress import read_state

_BOOK_LANE_PHASES = ("0book-design", "0book-compose", "0book-illustrate", "0book-slide-import", "0book-render")


def reading_edition_is_built(book_dir: Path) -> bool:
    """True when a previous run already took the lane to a rendered PDF.

    Keeps the publish-time call from paying for a whole-book re-compose over a
    book that already has one — the expensive half of this lane is model time, and
    re-running it would also discard nothing but cost hours.
    """
    state = read_state(book_dir) or {}
    phases = state.get("phases", {})
    render = phases.get("0book-render") or {}
    return render.get("status") == "completed" and (book_dir / "book" / "book.pdf").exists()


def can_build_without_human_artifact(book_dir: Path) -> bool:
    """True when the book lane can reach a PDF with nothing dropped by hand.

    The only halts inside the lane wait on files a human supplies: NotebookLM deck
    exports (0book-slide-import) and curated visual placement (0book-render's
    awaiting-layout). Both live behind the pipeline visual policy, so the question
    reduces to the policy — asked through the same resolver the lane itself uses,
    never re-derived here.
    """
    try:
        return book_visuals(book_dir) == BOOK_VISUALS_MANUAL_ONLY
    except ValueError:
        # A bad knob value must fail where the lane fails, loudly and once — not
        # here, silently, by declining to build.
        return False


def maybe_build_reading_edition_early(book_dir: Path, *, log: Callable[[str], None] = print) -> bool:
    """Run the book lane at the finalize halt when it can complete unattended.

    Returns True when the lane ran (whatever it concluded), False when declined.
    Never raises: a reading edition is a companion deliverable and must not cost
    the podcast its halt card.
    """
    if reading_edition_is_built(book_dir):
        log("  reading edition: already built — not re-composing")
        return False
    if not can_build_without_human_artifact(book_dir):
        log("  reading edition: deferred — book_visuals=pipeline needs dropped NotebookLM decks first")
        return False
    log("")
    log("  reading edition: building now so the Composer has a book to open")
    try:
        from phases.book_driver import _drive_book_branch

        rc = _drive_book_branch(book_dir)
    except Exception as exc:  # pragma: no cover - companion deliverable, never fatal
        log(f"  reading edition: build failed (continuing): {type(exc).__name__}: {exc}")
        return False
    if rc == 3:
        # Should be unreachable under manual_only; if the lane grows a new halt,
        # say so rather than letting the halt card claim a PDF that is not there.
        log("  reading edition: the lane halted — see the book phases in state")
    return True
