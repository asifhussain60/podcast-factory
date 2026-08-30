#!/usr/bin/env python3
"""Timed transcripts somebody else produced, and what it takes to trust one.

WHY THIS IS NOT PART OF `_transcript.py`

    That module is the cue MODEL and the file we ship. Its reader says of itself
    that it is "only as tolerant as it needs to be", because it parses our own
    output — a claim that stops being true the moment it is pointed at a file a
    third party wrote. Ingestion is a different question from representation: it
    is about FORMAT (what did they hand us) and TRUST (does it belong to this
    recording), and neither belongs in the model.

WHY ADOPTING ONE IS WORTH THE CODE

    Measured on a 10m52s lecture from the Purification of the Heart series
    (2026-08-30): Azure and the hand-produced transcript agree on 96.1% of words,
    and the 3.9% they differ on is almost entirely this library's vocabulary.
    Azure dropped `Bismillah ar-Rahman ar-Rahim` and seven occurrences of
    `subhanahu wa ta'ala` outright, wrote `takwa` for taqwa, `toba` for tawbah,
    `comat` for karamat, `surgeons` for sojourns — and twice produced text that
    is not a mishearing but a change of meaning: `Allah subhanahu wa ta'ala
    anhum` came back as "beloved God on him", and "Know, may Allah give you and
    us success" as "No, may I give you and us success".

    Separately, Azure's fast-transcription endpoint returns nothing past roughly
    25 minutes and none of the callers on this route chunk. 21 of that series'
    41 recordings are longer than that. So for lecture audio the paid route is
    both less accurate AND unable to finish the job; the saving (about $5 for
    17 audio-hours) is the least interesting part.

WHAT IS REFUSED, AND WHY EACH CHECK EXISTS

    A dropped file is unverified input. Adopting the wrong one is worse than
    paying for a new transcription, because it is silent: the chapter reads
    plausibly and belongs to a different recording. So a candidate must survive
    every check in `problems()` before it is written, and a candidate that fails
    is reported by NAME with its reason rather than skipped quietly.

    The load-bearing check is COVERAGE. A truncated export, or a file paired with
    the wrong episode, almost always shows up as a transcript whose last cue ends
    nowhere near the end of the recording — or well past it. Nothing else catches
    that, and a human comparing 41 files by eye will not catch it either.

WHAT IS NEVER GUESSED

    Which episode a file belongs to. `episode_number_from` reads an episode
    number out of a filename using an explicit, ordered list of patterns and
    returns None when none of them match; two files claiming the same episode
    disqualify BOTH. The Sessions lane already states its audio-to-session
    pairing rather than inferring it (see `sessions/series.py`), and a fuzzy
    content match here would quietly contradict that — putting a scholar's words
    under the wrong session heading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _transcript import Cue, from_vtt

#: Extensions we will look at. Anything else in the drop folder is ignored
#: rather than reported — a `.DS_Store` is not a failed transcript.
TIMED_SUFFIXES = (".vtt", ".srt")

#: The transcript must reach at least this much of the recording. A lecture whose
#: transcript stops at 40% is truncated or belongs to a different file. The floor
#: is deliberately loose: a recording can legitimately end with silence, applause,
#: or an unmiked question, and refusing a good transcript costs a paid re-run.
COVERAGE_FLOOR = 0.80

#: ...and must not overrun the recording by more than this. An overrun cannot be
#: trailing silence; it means the file describes a LONGER recording than the one
#: it was matched to, which is the wrong-file case seen from the other side.
COVERAGE_CEILING = 1.05

#: Below this many cues a "timed" transcript is not usefully timed — it is a wall
#: of text with a clock bolted on. TurboScribe's plain-text export is exactly
#: this: 1,906 words under a single `(0:01 - 10:51)` marker. Adopting one would
#: publish a read-along that highlights the whole chapter at once.
MIN_CUES = 4


class UnreadableTranscript(ValueError):
    """The bytes are not a timed transcript in any format we read.

    Raised rather than returning an empty list, because empty is precisely how
    this used to fail: `from_vtt` on a SubRip file returns `[]` with no error,
    and `sessions/spoken.py` turns "no cues" into "" — so dropping an `.srt`
    produced an empty chapter and nothing anywhere said why.
    """


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

# SubRip: `00:00:05,120 --> 00:00:09,400`. The hour field is required by the
# format and the separator is a comma, which is the whole difference from the
# WebVTT stamp — and the reason a `.srt` sails past the VTT reader unrecognised.
_SRT_STAMP_RE = re.compile(r"^(\d+):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d+):(\d{2}):(\d{2}),(\d{3})")


def _srt_ms(h: str, m: str, s: str, ms: str) -> int:
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


def from_srt(text: str) -> list[Cue]:
    """Read SubRip into the same cue model WebVTT reads into.

    Speaker labels are not attempted. SubRip has no equivalent of the VTT voice
    span, and the conventions people use instead — a `- ` prefix, a name and a
    colon, italics — are ambiguous with ordinary dialogue punctuation. A cue with
    no speaker renders correctly everywhere in this repo; a cue with a WRONG
    speaker is a claim about who said something.
    """
    cues: list[Cue] = []
    block: list[str] = []

    def close() -> None:
        if not block:
            return
        timing = next((ln for ln in block if _SRT_STAMP_RE.match(ln)), None)
        if timing is None:
            return
        m = _SRT_STAMP_RE.match(timing)
        assert m is not None
        start = _srt_ms(*m.group(1, 2, 3, 4))
        end = _srt_ms(*m.group(5, 6, 7, 8))
        said = " ".join(block[block.index(timing) + 1 :]).strip()
        if said:
            cues.append(Cue(offset_ms=start, duration_ms=max(0, end - start), text=said))

    for raw in text.splitlines():
        if raw.strip() == "":
            close()
            block = []
            continue
        block.append(raw.strip())
    close()
    return cues


def parse_timed(text: str, *, name: str = "transcript") -> list[Cue]:
    """Read a timed transcript in whichever of the formats we accept it is in.

    Decided by CONTENT, never by the file extension: a file named `.vtt` that
    contains SubRip stamps is a thing exporters really produce, and honouring the
    name over the bytes would reject it for no reason.

    Tried in order rather than sniffed, because the two stamp formats are
    mutually exclusive — WebVTT separates the milliseconds with a `.` and SubRip
    with a `,` — so whichever reader returns cues is by construction the right
    one. An earlier version tested the format first AND kept this fallback; the
    test could not change any outcome, which a mutation run is what showed.
    """
    cues = from_vtt(text) or from_srt(text)
    if not cues:
        raise UnreadableTranscript(
            f"{name}: no timed cues found — expected WebVTT (`00:00:05.120 --> …`) "
            f"or SubRip (`00:00:05,120 --> …`). A plain-text export with one "
            f"timestamp for the whole recording is not a timed transcript."
        )
    return cues


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------


def problems(cues: list[Cue], *, audio_duration_s: float | None) -> list[str]:
    """Everything wrong with this transcript, in plain words. Empty means adopt.

    Returns ALL failures rather than the first, so a bad batch is diagnosed in
    one run instead of one re-run per defect.
    """
    found: list[str] = []

    if len(cues) < MIN_CUES:
        found.append(
            f"only {len(cues)} cue(s) — a timed transcript needs at least {MIN_CUES}; "
            "this looks like a plain-text export rather than a subtitle file"
        )

    if not any(c.text.strip() for c in cues):
        found.append("every cue is empty of text")

    # Monotonicity. Cues that start earlier than the one before them mean two
    # files were concatenated, or an exporter emitted overlapping speaker tracks;
    # either way the paragraph-to-audio alignment downstream would be nonsense.
    backwards = [i for i in range(1, len(cues)) if cues[i].offset_ms < cues[i - 1].offset_ms]
    if backwards:
        found.append(
            f"{len(backwards)} cue(s) start before the cue before them "
            f"(first at cue {backwards[0] + 1}) — the file is out of order or two files are concatenated"
        )

    negative = [i for i, c in enumerate(cues) if c.duration_ms < 0]
    if negative:
        found.append(f"{len(negative)} cue(s) end before they start (first at cue {negative[0] + 1})")

    # Coverage — the check that catches the wrong file. Skipped, and said to be
    # skipped, when the recording's length is unknown: a machine without ffprobe
    # must still be able to adopt, and silently dropping the strongest check
    # would make an unverified transcript indistinguishable from a verified one.
    if audio_duration_s and audio_duration_s > 0:
        ratio = (cues[-1].end_ms / 1000.0) / audio_duration_s if cues else 0.0
        if ratio < COVERAGE_FLOOR:
            found.append(
                f"covers only {ratio:.0%} of the {audio_duration_s / 60:.1f}-minute recording "
                f"(ends at {cues[-1].end_ms / 60000:.1f} min) — truncated export, or the wrong recording"
            )
        elif ratio > COVERAGE_CEILING:
            found.append(
                f"runs to {ratio:.0%} of the {audio_duration_s / 60:.1f}-minute recording "
                f"(ends at {cues[-1].end_ms / 60000:.1f} min) — this describes a longer recording than the one it is matched to"
            )

    return found


def coverage(cues: list[Cue], audio_duration_s: float | None) -> float | None:
    """How much of the recording the transcript reaches, or None if unknowable."""
    if not cues or not audio_duration_s or audio_duration_s <= 0:
        return None
    return round((cues[-1].end_ms / 1000.0) / audio_duration_s, 4)


# ---------------------------------------------------------------------------
# Which episode is this?
# ---------------------------------------------------------------------------

# Ordered, first match wins. Each one is a shape a human actually names files:
# our own convention, then the two exporters in use here. `re.IGNORECASE`.
#
# Each number is closed with `(?!\d)` rather than `\b`. An underscore is a WORD
# character, so `\b` never matches between the `9` and the `_` in `EP09_final` —
# and separator-underscores are exactly what batch exporters produce. `(?!\d)`
# says the only thing actually meant: the number has ended.
_EPISODE_PATTERNS = (
    r"\bep(?:isode)?[\s._-]*(\d{1,3})(?!\d)",  # ep01, ep 1, episode-12, EP09_final
    r"\[\s*part[\s._-]*(\d{1,3})\s*\]",  # "[Part 41]" — the 4K downloader's shape
    r"\bpart[\s._-]*(\d{1,3})(?!\d)",  # Part 41
    r"\bsession[\s._-]*(\d{1,3})(?!\d)",  # Session 2
    r"^(\d{1,3})[\s._-]",  # "03 - Title"
)


def episode_number_from(name: str) -> int | None:
    """The episode number a filename claims, or None when it claims none.

    None is a real answer, not a failure to try harder. A file whose name carries
    no number is reported to the operator so they can rename it; inferring one
    from position in a directory listing would silently reorder a series the
    first time an export was missing.
    """
    stem = Path(name).stem
    for pattern in _EPISODE_PATTERNS:
        m = re.search(pattern, stem, re.IGNORECASE)
        if m:
            number = int(m.group(1))
            if number > 0:
                return number
    return None


@dataclass(frozen=True)
class Discovery:
    """What a drop folder turned out to contain."""

    #: episode number -> the file that unambiguously claims it
    by_episode: dict[int, Path] = field(default_factory=dict)
    #: human-readable reasons files were not usable, one line each
    complaints: list[str] = field(default_factory=list)


def discover(folder: Path) -> Discovery:
    """Map a folder of dropped transcripts onto episode numbers.

    A collision disqualifies BOTH files rather than picking one. When two exports
    claim episode 3, the pipeline does not know which is the good one, and a
    coin-flip here publishes the wrong lecture under the right title.
    """
    if not folder.is_dir():
        return Discovery()

    claims: dict[int, list[Path]] = {}
    complaints: list[str] = []

    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in TIMED_SUFFIXES:
            continue
        number = episode_number_from(path.name)
        if number is None:
            complaints.append(
                f"{path.name}: no episode number in the filename — rename it to `ep07{path.suffix.lower()}` "
                f"(or include `[Part 7]` / `Session 7`) so it can be matched"
            )
            continue
        claims.setdefault(number, []).append(path)

    by_episode: dict[int, Path] = {}
    for number, paths in sorted(claims.items()):
        if len(paths) > 1:
            complaints.append(
                f"episode {number} is claimed by {len(paths)} files "
                f"({', '.join(p.name for p in paths)}) — none adopted; remove or rename all but one"
            )
            continue
        by_episode[number] = paths[0]

    return Discovery(by_episode=by_episode, complaints=complaints)


@dataclass(frozen=True)
class Candidate:
    """One dropped file, read and judged, ready to adopt or to explain itself."""

    episode: int
    path: Path
    cues: list[Cue]
    problems: list[str]
    coverage: float | None

    @property
    def adoptable(self) -> bool:
        return not self.problems and bool(self.cues)


def read_candidate(episode: int, path: Path, *, audio_duration_s: float | None) -> Candidate:
    """Read and judge one dropped file. Never raises — an unreadable file is a
    Candidate carrying the reason, so one bad export cannot abort a batch."""
    try:
        cues = parse_timed(path.read_text(encoding="utf-8", errors="replace"), name=path.name)
    except UnreadableTranscript as exc:
        return Candidate(episode=episode, path=path, cues=[], problems=[str(exc)], coverage=None)
    except OSError as exc:
        return Candidate(episode=episode, path=path, cues=[], problems=[f"unreadable: {exc}"], coverage=None)

    return Candidate(
        episode=episode,
        path=path,
        cues=cues,
        problems=problems(cues, audio_duration_s=audio_duration_s),
        coverage=coverage(cues, audio_duration_s),
    )
