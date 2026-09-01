"""The record of which chapters came off the tape, and what the tape said.

Split out of `ingest.py` on 2026-08-15, alongside the read-along lane step,
when the read-along pass's own module pushed `ingest.py` over the DR-005 line
cap. A real seam: everything here is about the SPOKEN RECORD — what the
recording said, in paragraphs, and which chapter keys are backed by one — and
three modules read it: `ingest.py` writes it at ingest time, `articulate.py`
consults it to know which chapters must not be rewritten, and `read_along.py`
consults it to know which chapters to correct and time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from _align_paragraphs import align
from spoken_lane import scaffold as _scaffold

#: Chapters whose prose is a transcription of a recording, by chapter key.
SPOKEN_CHAPTERS_NAME = "sessions-spoken-chapters.json"


#: Moved to `spoken_lane.scaffold` on 2026-09-01: it reads the LANE's transcript
#: contract, not anything KSESSIONS-specific, and the audiobook adapter needed it
#: without importing a private name out of this module. Re-exported so every
#: existing caller here is unchanged.
_heard_text = _scaffold.heard_text


def spoken_chapters_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / SPOKEN_CHAPTERS_NAME


def write_spoken_chapters(book_dir: Path, chapters: dict[str, dict]) -> None:
    spoken_chapters_path(book_dir).write_text(
        json.dumps(
            {"schema": "podcast.sessions-spoken-chapters/v1", "chapters": chapters}, indent=2, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )


def spoken_chapters(book_dir: Path) -> dict[str, dict]:
    """Chapter key -> ``{title, sequence, episode}`` for chapters taken off the tape.

    Empty for every book that is not a Sessions book, and empty for a Sessions
    book ingested before this file existed — both of which mean the same thing
    to a caller, which is why the absent file is not an error.
    """
    path = spoken_chapters_path(book_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    chapters = data.get("chapters")
    return chapters if isinstance(chapters, dict) else {}


_IMAGE_BLOCK_RE = re.compile(r"^!\[[^\]]*\]\([^)]+\)$")


def _carry_images(heard: str, notes: str) -> str:
    """Put the notes' illustrations into the spoken text, at the passage they illustrate.

    The two texts are the same lecture told twice — once written down, once said
    aloud — so an image's place in the notes is evidence about where it belongs
    in the transcription, and `_align_paragraphs` is the machinery this repo
    already uses to carry a position across two tellings of one thing.

    A picture whose paragraph cannot be placed goes to the END of the chapter
    rather than to a guessed position. An illustration under the wrong passage
    of a religious lecture is worse than one a reader has to scroll for, and the
    Book Composer is where a human moves it.
    """
    blocks = [b.strip() for b in notes.split("\n\n") if b.strip()]
    images = [i for i, b in enumerate(blocks) if _IMAGE_BLOCK_RE.match(b)]
    if not images:
        return heard

    prose = [i for i, b in enumerate(blocks) if not _IMAGE_BLOCK_RE.match(b)]
    heard_blocks = [b.strip() for b in heard.split("\n\n") if b.strip()]
    placed: dict[int, list[str]] = {}
    trailing: list[str] = []

    alignments = align([blocks[i] for i in prose], heard_blocks) if prose else []
    # Inverted: the alignment answers "which note paragraph is this spoken
    # paragraph from", and the question here is the other way round.
    first_for_source: dict[int, int] = {}
    for a in alignments:
        first_for_source.setdefault(a.source_index, a.index)

    for image in images:
        before = [p for p in prose if p < image]
        target = first_for_source.get(prose.index(before[-1])) if before else None
        if target is None:
            trailing.append(blocks[image])
        else:
            placed.setdefault(target, []).append(blocks[image])

    out: list[str] = []
    for i, block in enumerate(heard_blocks):
        out.append(block)
        out.extend(placed.get(i, ()))
    out.extend(trailing)
    return "\n\n".join(out)


def derive_spoken_chapters(book_dir: Path, chapters: list[tuple[str, str, str]]) -> dict[str, dict]:
    """Work out which recording each chapter was spoken in, from the transcripts.

    `chapters` is (key, title, prose) in reading order. Returns the record
    `write_spoken_chapters` stores.

    WHY THIS IS DERIVED RATHER THAN DECLARED. A book ingested by this lane learns
    the pairing from the folders it was delivered in, and folders stay
    authoritative wherever they exist. `purification-of-the-heart` reached
    Sessions down the ORCHESTRATED route instead: twenty-four chapters cut from
    two ten-hour recordings, with nothing on disk saying which chapter belongs to
    which. Splitting that by hand is a guess typed into a file that later reads
    as a fact, so it is measured instead — every chapter is aligned against every
    recording and assigned to the one that actually carries its words.

    The evidence is legible afterwards: on that book the split came out as
    chapters 1-16 in the first recording and 17-24 in the second, contiguous, in
    order, with 2h16m at the head of the first matching no chapter at all — which
    is exactly the material the book's contents page opens with and this chapter
    set deliberately begins after.
    """
    from _align_paragraphs import SELF_SUPPORT
    from _narration_plan import chapter_blocks
    from _transcript import from_vtt

    blocks: list[str] = []
    owner: list[int] = []
    for index, (_key, _title, prose) in enumerate(chapters):
        for _block_index, text in chapter_blocks(prose):
            blocks.append(text)
            owner.append(index)
    if not blocks:
        return {}

    support: dict[int, dict[int, int]] = {}
    for path in sorted((book_dir / "transcripts").glob("ep*.vtt")):
        try:
            episode = int(path.stem[2:])
        except ValueError:
            continue
        said = [c for c in from_vtt(path.read_text(encoding="utf-8")) if c.text.strip()]
        if not said:
            continue
        for alignment in align(blocks, [c.text for c in said]):
            if alignment.score >= SELF_SUPPORT:
                support.setdefault(owner[alignment.source_index], {})[episode] = (
                    support.setdefault(owner[alignment.source_index], {}).get(episode, 0) + 1
                )

    out: dict[str, dict] = {}
    for index, (key, title, prose) in enumerate(chapters):
        votes = support.get(index)
        if not votes:
            # No recording claims it. Left out rather than assigned to a
            # neighbour's tape, which would time it against someone else's words.
            continue
        out[key] = {
            "title": title,
            "sequence": str(index + 1),
            "episode": str(max(votes, key=lambda ep: votes[ep])),
            "base": prose,
        }
    return out
