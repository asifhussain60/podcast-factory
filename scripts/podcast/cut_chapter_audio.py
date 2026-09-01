#!/usr/bin/env python3
"""cut_chapter_audio.py — one recording per chapter, holding only that chapter.

WHY. A session's recordings are long sittings. `purification-of-the-heart` is two
of them, 19.6 hours, and 149 minutes of that — 13% — falls outside every chapter:
136 minutes at the head of the first recording where the speaker greets the room
and works through the chapters this edition begins after, plus the short gaps
between chapters. Press play on Envy and you got "Hello, welcome to my lecture"
and two and a half hours before reaching "We ended on hasad last time."

Asif, 2026-08-31: "can you strip out this noise from the recording so it only
represents what's in the chapter."

WHAT IS AND IS NOT A JUDGEMENT HERE. Nothing in this file decides what is worth
keeping. It keeps the span the chapter's own text was matched to — first cue to
last cue, the same spans `sessions/read_along.py` produced and `_cue_gate` passed
— and drops what NO chapter accounts for. Audio inside a chapter's span is never
touched, however far the speaker wanders inside it: this cuts around chapters,
never within one.

THE ORIGINALS ARE NEVER MODIFIED. The cut files are derivatives written beside
the manifest, and the two full recordings stay exactly as delivered — they are
the only artifact here that cannot be regenerated. Delete every cut file and one
re-run rebuilds them.

THE TIMINGS COME WITH. A cue's seconds are an offset into the file it was
measured against, so every cue is rebased by subtracting the chapter's start.
Doing this in the same pass as the cut is deliberate: a cut file with unrebased
cues would highlight paragraphs hours away from the audio, and the two facts must
never exist apart.

STREAM COPY, never re-encode. `-c copy` writes the same bytes into a shorter
container: no generation loss and seconds rather than hours of CPU for 19.6 hours
of audio. It lands on a frame boundary, which for MP3 is within about 26ms — far
below what an ear notices at the start of a sentence.

Usage:
    python3 scripts/podcast/cut_chapter_audio.py <slug> [--chapter KEY] [--dry-run]
    python3 scripts/podcast/cut_chapter_audio.py <slug> --force     # recut existing
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_media import narration_object_name  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _runlog import log_event  # noqa: E402

PHASE = "sessions-cut-audio"

#: A moment of room tone before the first word. Without it a stream copy landing
#: on the frame boundary nearest the cue can clip the opening consonant, which is
#: audible in a way the same error mid-sentence is not.
LEAD_IN_S = 0.35

#: And after the last, so a chapter does not end mid-breath.
TAIL_S = 0.6


def _manifest_path(book_dir: Path) -> Path:
    return book_dir / "book" / "narration" / "manifest.json"


def _span(entry: dict) -> tuple[float, float] | None:
    """First cue's start and last cue's end, or None when the chapter is untimed."""
    cues = entry.get("cues")
    if not isinstance(cues, list) or not cues:
        return None
    try:
        start = min(float(c["startS"]) for c in cues)
        end = max(float(c["endS"]) for c in cues)
    except (KeyError, TypeError, ValueError):
        return None
    if end <= start:
        return None
    return max(0.0, start - LEAD_IN_S), end + TAIL_S


def rebase(cues: list[dict], start: float) -> list[dict]:
    """Every cue's seconds, measured from the start of the CUT file.

    Clamped at zero rather than allowed negative: the lead-in means the first cue
    should land at about 0.35s, but a rounding difference must never produce a
    cue the player reads as being before the file begins.
    """
    out: list[dict] = []
    for cue in cues:
        moved = dict(cue)
        moved["startS"] = round(max(0.0, float(cue["startS"]) - start), 3)
        moved["endS"] = round(max(0.0, float(cue["endS"]) - start), 3)
        out.append(moved)
    return out


def cut(source: Path, target: Path, start: float, end: float) -> None:
    """Write `source[start:end]` to `target`, copying the stream."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # `.part.mp3`, not `.part`: ffmpeg chooses the output format from the
    # extension, and a bare `.part` makes it refuse rather than guess.
    tmp = target.with_name(target.name + ".part.mp3")
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            # BEFORE -i: ffmpeg seeks the container instead of decoding to the
            # mark, which is the difference between seconds and many minutes on
            # a ten-hour file.
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source),
            "-c",
            "copy",
            # The copied packets carry their original timestamps; without this
            # the file starts at hours-in and players show a wrong position.
            "-avoid_negative_ts",
            "make_zero",
            str(tmp),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed cutting {source.name}: {proc.stderr.strip()[:300]}")
    tmp.replace(target)


def cut_book(book_dir: Path, *, only: str = "", force: bool = False, dry_run: bool = False, log=print) -> dict:
    book_dir = Path(book_dir).resolve()
    path = _manifest_path(book_dir)
    if not path.exists():
        return {"outcome": "skipped", "reason": "this book has no narration timings"}

    manifest = json.loads(path.read_text(encoding="utf-8"))
    chapters = manifest.get("chapters")
    if not isinstance(chapters, dict):
        return {"outcome": "skipped", "reason": "the manifest names no chapters"}

    done: list[str] = []
    skipped: list[str] = []
    saved = 0.0

    for anchor, entry in chapters.items():
        if only and anchor != only:
            continue
        title = str(entry.get("title") or anchor)
        # A chapter already cut has REBASED cues — they measure the cut file, not
        # the recording — so recomputing the span from them would cut the first
        # fifty minutes of the sitting instead of the fifty this chapter occupies.
        # `cut_span` is the span in the SOURCE's own coordinates and is the only
        # thing that survives a rebase, so it is what a recut uses. (Found by
        # running --force once: it produced a plausible file of the wrong hour.)
        recorded = entry.get("cut_span")
        span = tuple(recorded) if isinstance(recorded, list) and len(recorded) == 2 else _span(entry)
        if span is None:
            skipped.append(f"{title}: no timings, so no span to cut")
            continue
        start, end = float(span[0]), float(span[1])

        # Already cut, and from this same span: a re-run is a no-op rather than
        # an hour of ffmpeg. The span is what identifies it, so a re-timed
        # chapter recuts and an unchanged one does not.
        stamp = [round(start, 3), round(end, 3)]
        target_rel = f"book/narration/{narration_object_name(anchor)}"
        target = book_dir / target_rel
        if not force and target.exists() and entry.get("cut_span") == stamp:
            skipped.append(f"{title}: already cut from this span")
            continue

        source_rel = str(entry.get("cut_from") or entry.get("audio") or "")
        source = book_dir / source_rel
        if not source.exists():
            skipped.append(f"{title}: {source_rel or 'its recording'} is not on disk")
            continue
        if source.resolve() == target.resolve():
            skipped.append(f"{title}: refusing to cut a file onto itself")
            continue

        log(f"  {title[:44]:46} {start / 60:7.1f}-{end / 60:7.1f} min  ({(end - start) / 60:5.1f} min)")
        if dry_run:
            done.append(title)
            continue

        cut(source, target, start, end)
        saved += start
        # Rebase only cues that have not been rebased already — a recut writes
        # the same file from the same source span, so its cues are already right.
        if recorded is None:
            entry["cues"] = rebase(entry.get("cues") or [], start)
        entry["audio"] = target_rel
        # The cut file is this chapter's OWN object, so it must NOT keep pointing
        # at the whole recording's key — that key belongs to the episode asset
        # the player streams, and `_listener_media` would reference that instead
        # of publishing this file.
        entry.pop("audio_key", None)
        entry["duration_s"] = round(end - start, 3)
        entry["cut_from"] = source_rel
        entry["cut_span"] = stamp
        done.append(title)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not dry_run:
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log_event(
            "chapter-audio-cut",
            book_dir=book_dir,
            phase=PHASE,
            msg=f"{len(done)} chapter(s) cut, {len(skipped)} left alone",
            cut=len(done),
            skipped=len(skipped),
        )

    return {
        "outcome": "dry-run" if dry_run else "completed",
        "cut": done,
        "skipped": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--chapter", default="", help="one chapter key, for a first look")
    parser.add_argument("--force", action="store_true", help="recut even where the span is unchanged")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    book_dir = resolve_content(args.slug)
    if book_dir is None:
        print(f"no content found for {args.slug}", file=sys.stderr)
        return 2

    print(f"==> cutting chapter audio: {args.slug}{' (dry run)' if args.dry_run else ''}")
    report = cut_book(book_dir, only=args.chapter, force=args.force, dry_run=args.dry_run)
    if report["outcome"] == "skipped":
        print(f"    {report['reason']}")
        return 0
    print(f"    {len(report['cut'])} cut, {len(report['skipped'])} left alone")
    for line in report["skipped"]:
        print(f"      {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
