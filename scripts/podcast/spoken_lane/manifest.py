"""Read an audiobook container's chapter manifest and derive the works inside it.

WHAT A MANIFEST IS HERE. One audiobook file can hold many works — the Dostoyevsky
collection is 173.4 hours and twenty separate books in a single container. A
manifest is the list of its chapters, each with a start offset and a length in
milliseconds, and it is the ONLY honest way to cut such a file.

WHY NOT THE OBVIOUS SOURCES.

  * The container's own chapter atoms. Checked first, and for this file there are
    none — `ffprobe -show_chapters` returns an empty list. Other containers do
    carry them, so `from_container()` tries anyway and simply finds nothing here.

  * A screenshot of the player's chapter list. It shows DURATIONS, not offsets,
    so every start has to be reconstructed by summing — and a per-track rounding
    error of half a second compounds to minutes of drift by the end of 289
    tracks. Several of the durations were also clipped by the column they were
    rendered in. Offsets that are read are worth more than offsets that are
    inferred.

  * DVDFab's own log, which is what this file actually reads for that collection.
    It records the manifest the store served, with `start_offset_ms` per chapter,
    so no arithmetic is involved at all.

THE TOTAL IS CHECKED, NOT ASSUMED. `reconcile()` compares the manifest's own
extent against the container's probed duration. A manifest that describes a
different file, or that was truncated when it was logged, disagrees by more than
a rounding error — and cutting on it would silently produce chapters offset from
the words in them. Everything downstream is keyed to these numbers, so this is
the one place they get challenged.

WHERE A WORK BEGINS. Every work in a multi-work container opens with its own
short "opening credits" track, and the title carries the work's name as a prefix
(`03_TheCrocodile_Chapter1`). So a work boundary is an `_OpeningCredits` track,
and the work's name is what precedes it.

Matched as a SUBSTRING, never a suffix — and that is not fussiness. Some titles
in this collection carry a trailing annotation from however they were catalogued
(`01_TheDouble_OpeningCredits(The_Devils)`). A suffix test misses that one line,
which does not raise anything: it silently merges The Double into Poor Folk and
hands back nineteen works that all look plausible. The test below pins it.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

#: A work boundary. Substring, for the reason in the module docstring.
_OPENING_CREDITS = re.compile(r"_OpeningCredits")

#: The leading track number a multi-work container puts on every title.
_TRACK_PREFIX = re.compile(r"^\d+[_\-\s]*")

#: How far the manifest's extent may differ from the container's probed duration
#: before the two are considered to describe different things. A container's
#: duration is reported to the frame and a manifest to the millisecond, so they
#: are never bit-identical; a whole minute across many hours is not rounding.
RECONCILE_TOLERANCE_MS = 60_000


@dataclass(frozen=True)
class Chapter:
    """One track: where it starts in the container, and how long it runs."""

    index: int
    title: str
    start_ms: int
    length_ms: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.length_ms


@dataclass(frozen=True)
class Work:
    """One book inside the container, and the tracks that make it up."""

    name: str
    chapters: tuple[Chapter, ...]

    @property
    def start_ms(self) -> int:
        return self.chapters[0].start_ms

    @property
    def end_ms(self) -> int:
        return self.chapters[-1].end_ms

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def _chapter_rows(rows: Iterable[dict[str, Any]]) -> list[Chapter]:
    out: list[Chapter] = []
    for i, row in enumerate(rows):
        try:
            start = int(row["start_offset_ms"])
            length = int(row["length_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(Chapter(index=i, title=str(row.get("title") or ""), start_ms=start, length_ms=length))
    return out


def from_container(container: Path) -> list[Chapter]:
    """The container's OWN chapter atoms, when it has any. Often it has none."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", str(container)],
            capture_output=True,
            text=True,
            check=True,
        )
        chapters = json.loads(proc.stdout).get("chapters") or []
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []
    out: list[Chapter] = []
    for i, c in enumerate(chapters):
        try:
            start = int(float(c["start_time"]) * 1000)
            end = int(float(c["end_time"]) * 1000)
        except (KeyError, TypeError, ValueError):
            continue
        title = str((c.get("tags") or {}).get("title") or "")
        out.append(Chapter(index=i, title=title, start_ms=start, length_ms=end - start))
    return out


def from_log(log: Path) -> list[Chapter]:
    """The largest ``"chapters":[…]`` array in a DVDFab/librocore log.

    A log accumulates every title the tool ever handled, so it holds one array
    per book. The LARGEST is taken rather than the last, because "most chapters"
    identifies the multi-work container unambiguously while "most recent" depends
    on what the operator happened to download afterwards. `reconcile()` is what
    actually confirms the choice was right.
    """
    raw = log.read_text(errors="replace")
    best: list[Chapter] = []
    for match in re.finditer(r'"chapters"\s*:\s*\[', raw):
        opening = raw.index("[", match.start())
        depth = 0
        for i in range(opening, len(raw)):
            if raw[i] == "[":
                depth += 1
            elif raw[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        rows = json.loads(raw[opening : i + 1])
                    except ValueError:
                        rows = []
                    found = _chapter_rows(rows) if isinstance(rows, list) else []
                    if len(found) > len(best):
                        best = found
                    break
    return best


def probe_duration_ms(container: Path) -> int | None:
    """The container's own duration, for `reconcile()`. None when unreadable."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(container),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(float(proc.stdout.strip()) * 1000)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def reconcile(chapters: list[Chapter], container_ms: int | None) -> tuple[bool, int | None]:
    """Does the manifest describe THIS container? Returns (ok, difference_ms).

    Unreadable duration returns ok with no difference rather than blocking: the
    manifest may still be right and a probe failure is not evidence against it.
    The caller records which of the two happened.
    """
    if not chapters:
        return False, None
    if container_ms is None:
        return True, None
    diff = abs(chapters[-1].end_ms - container_ms)
    return diff <= RECONCILE_TOLERANCE_MS, diff


def work_name(title: str) -> str | None:
    """The work a track belongs to, or None if the title carries no work prefix."""
    match = _OPENING_CREDITS.search(title)
    if not match:
        return None
    return _TRACK_PREFIX.sub("", title[: match.start()]).strip("_- ") or None


def split_works(
    chapters: list[Chapter],
    *,
    first_work_name: str | None = None,
    front_matter: int = 0,
    trailing: int = 0,
) -> list[Work]:
    """Group tracks into works, one per `_OpeningCredits` boundary.

    `front_matter` and `trailing` are the container's OWN tracks — its opening
    credits, a title card, a preface to the whole collection, a closing sign-off.
    They are COUNTED BY THE CALLER, never detected here, and that is deliberate.

    Detecting them is exactly the kind of guess that fails quietly. A first
    attempt at this treated "the first work starts at the first track saying Part
    or Chapter" as the rule, which read plausibly and silently dropped that work's
    own `Introduction` — 284 tracks came back instead of 285, every one of the
    twenty works looked right, and nothing was there to say a chapter had gone
    missing. A container's front matter is a handful of tracks a person can read
    in one glance; the repo already asks rather than infers for the equivalent
    chapter-segmentation decision at intake, for the same reason.

    Tracks between `front_matter` and the first boundary are a work that predates
    the prefixed naming and so announces itself with nothing — the caller names it
    via `first_work_name`. When no such tracks exist the name is unused.

    Trailing container tracks are NOT attached to the last work: padding the final
    book with the collection's sign-off would make it the only one that ends with
    something it does not contain.
    """
    if not chapters:
        return []
    body = chapters[front_matter : len(chapters) - trailing if trailing else None]
    boundaries = [i for i, c in enumerate(body) if _OPENING_CREDITS.search(c.title)]
    if not boundaries:
        return []

    works: list[Work] = []
    if boundaries[0] > 0:
        works.append(
            Work(
                name=first_work_name or "untitled-opening-work",
                chapters=tuple(body[: boundaries[0]]),
            )
        )
    for a, b in zip(boundaries, boundaries[1:] + [len(body)]):
        segment = body[a:b]
        if not segment:
            continue
        works.append(Work(name=work_name(segment[0].title) or f"work-{a:03d}", chapters=tuple(segment)))
    return works


def slugify(name: str, overrides: dict[str, str] | None = None) -> str:
    """A work's folder name: `TheBrothersKaramazov` -> `the-brothers-karamazov`.

    `overrides` maps a work NAME to a finished slug, for the cases the rule
    cannot reach because the source itself is wrong. This collection catalogues
    one work as `TheDreamOfaRidiculousMan` — "Ofa", a typo in the store's own
    metadata — and no camel-case rule recovers the missing space. Correcting it
    here rather than in the splitter keeps the manifest a faithful record of what
    the container says while the folder still reads properly.
    """
    if overrides and name in overrides:
        return overrides[name]
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name.replace("_", "-"))
    return re.sub(r"-+", "-", re.sub(r"[^a-zA-Z0-9-]", "-", spaced)).strip("-").lower()


#: A camel-case boundary, and a letter-to-digit one. `FirstNight` -> `First Night`,
#: `Chapter1` -> `Chapter 1`.
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_LETTER_DIGIT = re.compile(r"(?<=[A-Za-z])(?=\d)")


def chapter_title(title: str, work_name: str) -> str:
    """A readable chapter heading from a container's track name.

    `03_WhiteNights_FirstNight` -> `First Night`. The leading track number and the
    work prefix are dropped, and what remains is split on camel case.

    BEST EFFORT, AND SAID SO. The input is a filename the publisher chose, not a
    title anyone wrote for a reader, so some of it does not recover: this
    collection catalogues one chapter as `Astory` and another as
    `NastenkasHistory`, which come back as "Astory" and "Nastenkas History" --
    a missing space and a missing apostrophe that no rule can put back. The raw
    name is kept verbatim in `_system/audiobook-chapters.json`, and the heading
    is a Composer edit away from being right. Guessing harder here would mean
    inventing punctuation into a chapter title, which is worse than a plain one.
    """
    stem = _TRACK_PREFIX.sub("", title)
    for prefix in (f"{work_name}_", f"{work_name}"):
        if prefix and stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    stem = stem.strip("_- ")
    if not stem:
        return "Untitled"
    stem = _CAMEL.sub(" ", _LETTER_DIGIT.sub(" ", stem.replace("_", " ")))
    return re.sub(r"\s+", " ", stem).strip()
