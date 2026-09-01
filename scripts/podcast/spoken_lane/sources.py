"""What the spoken lane has to know about WHERE a book came from.

`spoken_lane/scaffold.py` says the lane's sources are adapters and that adding one
means "writing an adapter and touching nothing else". `sessions/read_along.py` had
not followed: three KSESSIONS assumptions were built into it, and the first
audiobook to reach that step hit each of them in turn — argparse rejected the slug,
the timing pass looked for `.mp3` and found none of eight `.m4a` files, and the
state writer raised `KeyError` after the manifest had already been written.

The three answers live here rather than there, because none of them is about
reading along; each is about the lane carrying more than one kind of recording.
`sessions/read_along.py` imports them under its old private names, so nothing that
already called them moved.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sessions.ingest import READ_ALONG_STEP as _READ_ALONG_STEP  # noqa: E402
from sessions.ingest import _write_state as _ksessions_write_state  # noqa: E402
from sessions.series import SERIES as _SERIES  # noqa: E402

#: Recording formats the lane accepts, in preference order. `.mp3` was the whole
#: rule until 2026-09-01 and it was written for KSESSIONS lectures, which are
#: delivered as mp3. Audiobooks are m4a, so the first one through this step timed
#: nothing at all and reported "recording ep01.mp3 is not on disk" eight times
#: over — for eight files that were sitting right there under other extensions.
AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".m4a", ".m4b", ".wav")


def recording(book_dir: Path, episode: int) -> Path | None:
    """The audio file for one episode, whatever container it was delivered in."""
    for ext in AUDIO_EXTENSIONS:
        candidate = book_dir / "m4a" / "Episodes" / f"ep{episode:02d}{ext}"
        if candidate.exists():
            return candidate
    return None


def articulation_not_applicable(book_dir: Path, *, timing_only: bool) -> bool:
    """May this book be timed without `sessions-articulate` having completed?

    The gate above exists because this module REWRITES prose, and rewriting after
    a timing pass would leave the manifest pointing at sentences the book no
    longer contains. Two things have to be true for that reasoning not to apply.

    IT MUST BE A TIMING-ONLY RUN. Under `--timing-only` no model is called and no
    chapter is written; the prose is read exactly as it stands. There is nothing
    for a later articulation to invalidate because this run changes nothing.

    AND ARTICULATION MUST BE A STEP THIS BOOK NEVER TAKES. An audiobook is a
    published book read aloud by a narrator: its prose is the narrator's words,
    timed against the narrator's recording, and `book_voice: faithful` is what
    says so. Rearticulating it is the single thing this module's own opening
    paragraph says must never happen — "rewriting a sentence breaks the only
    thing that makes the pairing honest". Waiting for a step that must not run
    is waiting forever, which is exactly where `white-nights` sat: transcribed,
    edited to READY-WITH-NOTES by the book-editor, and unable to be timed.

    A Sessions lecture is NOT exempt. There articulation is real, pending means
    not yet, and timing first would time prose that is about to change.
    """
    if not timing_only:
        return False
    try:
        from _content_profile import resolve_content_profile
        from _pipeline_flags import book_voice
    except Exception:
        return False
    try:
        return (
            str(resolve_content_profile(book_dir) or "").strip().lower() == "audiobook"
            and book_voice(book_dir) == "faithful"
        )
    except Exception:
        return False


def record_progress(book_dir: Path, slug: str) -> None:
    """Record the lane's progress through read-along, whatever the source was.

    `_SERIES[slug]` was the whole of this, and it is a registry of KSESSIONS
    lectures — so the first audiobook to reach this step raised `KeyError` after
    the work was already done and the manifest already written. The lane's own
    writer takes the branch and category instead, which is what its docstring
    asks callers to do precisely so a bucket and its branch cannot drift.

    `sessions-articulate` is CARRIED OVER by that writer rather than derived from
    position, so an audiobook that legitimately skipped it is not recorded as
    having done it. The state ends up saying the true thing: transcribed, not
    articulated, timed.
    """
    from _branching import branch_name

    from spoken_lane import scaffold as lane

    if slug in _SERIES:
        _ksessions_write_state(book_dir, _SERIES[slug], done_through=_READ_ALONG_STEP)
        return
    from _content_profile import resolve_content_profile

    profile = str(resolve_content_profile(book_dir) or "audiobook").strip().lower()
    category = "lectures" if profile == "sessions" else "books"
    lane.write_state(
        book_dir,
        slug=slug,
        branch=branch_name(category, slug, profile=profile),
        category=category,
        done_through=_READ_ALONG_STEP,
    )
