#!/usr/bin/env python3
"""Timed transcripts: the cue model, the file we ship, and the words we fix.

WHY THIS EXISTS SEPARATELY FROM THE FLAT TRANSCRIPTS

    `m4a/transcripts/<stem>.transcript.txt` is prose with no clock. Four things
    read it — the post-production review's episode pairing, `audit_transcript.py`,
    `normalize_m4a.py`'s verification, and `stitch_video.py`'s keyword sync — and
    it is the corpus their recorded findings were made against.

    Re-transcribing does NOT reproduce it. Measured 2026-08-04 on one episode:
    a fresh call is 92.6% word-for-word identical to the June transcript, and two
    calls minutes apart differ from each other. The model moves. So nothing here
    ever writes that file: a timed transcript is a NEW artifact beside it, and a
    difference in wording is something to report, never to apply.

WHAT WE SHIP

    WebVTT, one file per episode, one cue per phrase, speaker labels where
    diarization gave them. 17 KB for a 9-minute episode — about 340 KB for a
    twenty-episode book — which is small enough for the reader to fetch whole and
    is a format with a specification instead of one this repo invented.

    Cues carry the phrase clock, not the word clock. Word offsets come back in
    the same response and are dropped by `_azure.transcribe_audio_timed`; see the
    note there.

THE WORDS WE FIX, AND THE ONES WE REFUSE TO

    Speech-to-text mishears this library's vocabulary badly. From the probe, in
    one breath: "the third is qual" (qawl) and "the three letters of ner" (nur).
    Printing that against a book about what those words mean is worse than
    printing nothing.

    So cue TEXT is corrected — never a timing — against
    `content/knowledge-base/pronunciations.jsonl`, the same cross-book library the
    pronunciation probe writes into, using ONLY the `mangled_variants` a human has
    already confirmed. Nothing is guessed: a mishearing nobody has recorded is
    left exactly as heard and reported as a candidate, which is how it reaches
    that file in the first place. Fuzzy-matching a religious term to the nearest
    known one would eventually put a word in a scholar's mouth.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRONUNCIATIONS = REPO_ROOT / "content" / "knowledge-base" / "pronunciations.jsonl"


@dataclass(frozen=True)
class Cue:
    """One line of the transcript, and when it is said."""

    offset_ms: int
    duration_ms: int
    text: str
    speaker: int | None = None

    @property
    def end_ms(self) -> int:
        return self.offset_ms + self.duration_ms


# ---------------------------------------------------------------------------
# WebVTT
# ---------------------------------------------------------------------------


def _stamp(ms: int) -> str:
    """`hh:mm:ss.mmm`, always with the hour field — the spec allows either."""
    ms = max(0, int(ms))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    seconds, ms = divmod(ms, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


_STAMP_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})\s+-->\s+(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})")


def _parse_stamp(h: str | None, m: str, s: str, ms: str) -> int:
    return (int(h or 0) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


def to_vtt(cues: list[Cue]) -> str:
    """Render cues as WebVTT.

    Speakers are written as the spec's own voice span, `<v Speaker 2>`, rather
    than as a prefix inside the text: a player that understands VTT can then tell
    the label from the words, and one that does not still shows something
    sensible. Nothing here invents a NAME for a speaker — the service returns
    small integers, and which integer is which host is not a thing it knows.
    """
    lines = ["WEBVTT", ""]
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_stamp(cue.offset_ms)} --> {_stamp(cue.end_ms)}")
        voice = f"<v Speaker {cue.speaker}>" if cue.speaker is not None else ""
        lines.append(f"{voice}{cue.text}")
        lines.append("")
    return "\n".join(lines)


def from_vtt(text: str) -> list[Cue]:
    """Read back what `to_vtt` wrote.

    Only as tolerant as it needs to be — this parses our own output, so that a
    re-run can see an existing transcript is complete without re-paying for it,
    and so tests can assert a round trip rather than a byte comparison.
    """
    cues: list[Cue] = []
    block: list[str] = []

    def close() -> None:
        if not block:
            return
        timing = next((ln for ln in block if _STAMP_RE.match(ln)), None)
        if timing is None:
            return
        m = _STAMP_RE.match(timing)
        assert m is not None
        start = _parse_stamp(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _parse_stamp(m.group(5), m.group(6), m.group(7), m.group(8))
        said = " ".join(block[block.index(timing) + 1 :]).strip()
        speaker: int | None = None
        voice = re.match(r"^<v\s+Speaker\s+(\d+)>", said)
        if voice is not None:
            speaker = int(voice.group(1))
            said = said[voice.end() :]
        if said:
            cues.append(Cue(offset_ms=start, duration_ms=max(0, end - start), text=said.strip(), speaker=speaker))

    for raw in text.splitlines():
        if raw.strip() == "":
            close()
            block = []
            continue
        if raw.strip() == "WEBVTT" or raw.startswith("NOTE"):
            continue
        block.append(raw.strip())
    close()
    return cues


def flat_text(cues: list[Cue]) -> str:
    """The cues as running prose — for comparing against a flat transcript."""
    return " ".join(c.text for c in cues)


# ---------------------------------------------------------------------------
# Terminology
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Correction:
    heard: str
    corrected: str
    count: int


def load_pronunciations(path: Path | None = None) -> list[dict]:
    """The cross-book pronunciation library, or an empty list when absent.

    Absent is not an error: a machine that has not pulled the knowledge base can
    still produce transcripts, they simply go out uncorrected. Silent degradation
    is right here because the alternative — refusing to transcribe — would make
    the publish step fail for a reason that has nothing to do with publishing.
    """
    src = path or PRONUNCIATIONS
    if not src.is_file():
        return []
    rows: list[dict] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def correction_map(rows: list[dict], *, slug: str | None = None) -> dict[str, str]:
    """`{mangled form: canonical term}`, from confirmed entries only.

    Scoped to nothing by default — a mishearing of `al-Naysaburi` is the same
    mishearing whichever book it happens in, and the library records the term
    once with its `source_books` rather than once per book. `slug` narrows it
    when a caller wants only what this book confirmed.

    Entries whose status is `unfixable` still contribute: "unfixable" is a verdict
    about the AUDIO — the hosts cannot be made to say it right — and has nothing
    to do with whether the written transcript should spell it correctly. That is
    precisely the case where a reader most needs the text to be right.
    """
    out: dict[str, str] = {}
    for row in rows:
        term = (row.get("term") or "").strip()
        if not term:
            continue
        if slug is not None and slug not in (row.get("source_books") or []):
            continue
        for variant in row.get("mangled_variants") or []:
            variant = (variant or "").strip()
            # A variant equal to the term teaches nothing and would make the
            # replacement a no-op with a cost; a one-character variant would
            # match half the alphabet.
            if len(variant) < 3 or variant.casefold() == term.casefold():
                continue
            out[variant] = term
    return out


def correct_terms(cues: list[Cue], mapping: dict[str, str]) -> tuple[list[Cue], list[Correction]]:
    """Rewrite known mishearings in the cue TEXT. Timings are never touched.

    Whole words only, longest variant first — `Al Nasabiri` must win over any
    shorter form that happens to sit inside it. Matching ignores case because the
    service capitalises by sentence position; the replacement carries the
    library's own casing, which is the canonical spelling of the term.
    """
    if not mapping:
        return list(cues), []

    ordered = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(v) for v in ordered) + r")\b", re.IGNORECASE)
    lowered = {k.casefold(): v for k, v in mapping.items()}
    tally: dict[str, int] = {}

    def swap(match: re.Match[str]) -> str:
        heard = match.group(0)
        canonical = lowered.get(heard.casefold())
        if canonical is None:
            return heard
        tally[heard] = tally.get(heard, 0) + 1
        return canonical

    fixed = [replace(cue, text=pattern.sub(swap, cue.text)) for cue in cues]
    made = [Correction(heard=h, corrected=lowered[h.casefold()], count=n) for h, n in sorted(tally.items())]
    return fixed, made


def _loose(text: str) -> str:
    """Fold the things a transcript spells differently but says identically.

    Three differences, none of them audible:

        punctuation   the library writes `Qur'an`, speech-to-text writes `Quran`;
                      apostrophes — straight, curly, and the ayn and hamza this
                      corpus uses — carry no sound, and neither do the hyphens in
                      `al-Naysaburi`
        diacritics    `nāṭiq` and `natiq` are one word said one way, and the
                      library stores the scholarly transliteration while a
                      transcript can only ever produce the plain one
        case          the service capitalises by sentence position

    Without this the report cries wolf on every term that was heard perfectly
    well and merely written differently — which is worse than no report, because
    a list nobody can trust is a list nobody reads.
    """
    stripped = "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))
    # Punctuation is REMOVED, not turned into a space: `Qur'an` has to fold onto
    # `Quran`, and replacing the apostrophe with a separator would leave `qur an`
    # matching nothing. Whitespace is then collapsed on its own.
    # The class covers every mark this corpus uses for ayn and hamza — U+02BE and
    # U+02BF are the scholarly pair and are NOT the same characters as the curly
    # quotes, which is why listing only the quotes left `daʿwa` unfolded.
    return re.sub(r"\s+", " ", re.sub(r"['‘’`´ʻʼʽʾʿ′-]+", "", stripped.casefold())).strip()


def unheard_terms(cues_by_episode: dict[int, list[Cue]], rows: list[dict], *, slug: str) -> list[str]:
    """Terms this book confirmed that appear in NO episode of it.

    Asked ACROSS THE WHOLE BOOK, never per episode. Most terms are not spoken in
    most episodes — `Abu Malik` does not arrive until the fourteenth — so a
    per-episode version reports thirty-five absences an episode and means nothing.
    A term the library confirmed for this book and that appears nowhere in twenty
    recordings is a different claim, and usually a mishearing nobody has written
    down yet.

    A report, never a correction. This is the list to take to the pronunciation
    probe so a confirmed variant can be added and the next run fixes it; guessing
    which garbled word was meant is how the wrong word gets printed.
    """
    said = _loose(" ".join(flat_text(cues) for cues in cues_by_episode.values()))
    missing: list[str] = []
    for row in rows:
        term = (row.get("term") or "").strip()
        if not term or slug not in (row.get("source_books") or []):
            continue
        if _loose(term) not in said:
            missing.append(term)
    return sorted(set(missing))


# ---------------------------------------------------------------------------
# Where the files live
# ---------------------------------------------------------------------------

TRANSCRIPT_DIR = "transcripts"


def vtt_path(book_dir: Path, number: int) -> Path:
    """The timed transcript for one episode, keyed by EPISODE NUMBER.

    `(slug, number)` is the episode's identity everywhere else in this pipeline —
    the audio asset key, the listening position, the episode row — and a
    transcript keyed by the audio FILENAME would be lost the moment a recording is
    re-exported under a new name, which is the exact failure the listening
    position was rebuilt to escape.

    `BOOK_DIR/transcripts/`, NOT `BOOK_DIR/m4a/transcripts/`, and the difference
    is money. `.gitignore` excludes `content/**/m4a/**` to keep recordings out of
    the repository, and that rule swallows everything else under `m4a/` with them
    — so a timed transcript filed there would never be committed, would not exist
    on a fresh clone, and would be re-transcribed at Azure's rate every time
    somebody checked the book out. It is 17 KB of text per episode that costs
    real money to produce; it belongs in git, in the same tracked folder as the
    EP-keyed flat transcripts.
    """
    return book_dir / TRANSCRIPT_DIR / f"ep{number:02d}.vtt"
