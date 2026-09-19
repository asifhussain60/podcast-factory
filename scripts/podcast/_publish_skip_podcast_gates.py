"""publish_to_library.py's G1 gate, for a skip_podcast book.

A `skip_podcast: true` book (`_content_profile.skip_podcast`, series-config.yaml
per-book override — see docs/standards/book-series-setup.md) never produces an
`episodes/` upload bundle: its deliverable is `chapters/*.txt` + slide decks +
the reading edition + its read-aloud narration, never a two-host NotebookLM
conversation. G1's normal `chapters/*.txt AND episodes/*.txt` requirement
therefore always fails it — not because anything is missing, but because it
checks for a folder this book was never going to have. G2 (chapter/episode
pairs), G3 (episode sequential numbering) and G4 (episode build-clean) are all
specifically about that same podcast upload bundle, so they are n/a here too,
exactly as they already are for the Sessions lane (_publish_sessions_gates.py)
and the reading-edition-only lane (_publish_reading_edition_gates.py) — this
module is the third sibling in that family, added because neither existing
lane fit: Sessions/reading-edition-only books never carry `chapters/*.txt`
either, while a skip_podcast book does (they source the slide decks and the
NotebookLM-independent narration), just never `episodes/*.txt`.

Unlike the reading-edition-only lane, this gate does NOT require book/book.md,
book/*.pdf or a narration manifest to already exist: in the standard
orchestrator flow the book-compose/render/narration lane (`0book-*`) runs
AFTER the finalize gates pass (see `_book_preview.maybe_build_reading_edition_
early`, called from `phases/post_chapter_driver.py` only once `finalize`
reaches SHIP-READY). Requiring those artifacts here would make G1
unsatisfiable on a book's very first pass through finalize. G1 checks the one
deliverable that genuinely is complete by the time finalize runs: the
chapters/*.txt cohort itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def is_skip_podcast_lane(workspace: Path) -> bool:
    """True when this book's own series-config.yaml sets `skip_podcast: true`."""
    from _content_profile import skip_podcast

    return skip_podcast(workspace)


def gate_g1_skip_podcast_structure(workspace: Path, *, fail, ok) -> tuple[bool, int]:
    """This lane's own G1: chapters/*.txt exist and are non-empty. No episodes/
    requirement — that folder is never created for a skip_podcast book by design.
    Returns (passed, chapter_count) — chapter_count substitutes for G1's normal
    episode count in the caller's catalog/log lines.
    """
    chap_dir = workspace / "chapters"
    if not chap_dir.is_dir():
        fail("G1", f"missing chapters/ under {workspace}")
        return False, 0
    chapters = sorted(p for p in chap_dir.glob("ch*.txt") if p.is_file())
    if not chapters:
        fail("G1", f"no chapters/ content under {workspace}")
        return False, 0
    ok("G1", f"skip_podcast lane: {len(chapters)} chapters present (no podcast episodes by design)")
    return True, len(chapters)
