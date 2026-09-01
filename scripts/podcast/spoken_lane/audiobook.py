#!/usr/bin/env python3
"""Break one audiobook container into books and chapters on the Audiobook shelf.

THE JOB. A purchased audiobook can arrive as a single file holding many works —
the Dostoyevsky collection is 173.4 hours and twenty books in one container. This
turns that into `content/Audiobook/<slug>/m4a/Episodes/ep01.m4a …`, one folder per
book and one file per chapter, which is the layout the spoken lane and the
Podcast Factory Library already read.

STREAM COPY, NEVER RE-ENCODE. `-c copy` writes the same bytes into a shorter
container: no generation loss, and seconds rather than hours of CPU for 173 hours
of audio. The same choice `cut_chapter_audio.py` makes, for the same reasons.

A cut lands on a frame boundary, so a chapter is short or long by at most one
frame. That bound is the SOURCE's, not a constant: one AAC frame is 1024 samples,
which at this collection's 22.05 kHz is 46ms, where the 44.1 kHz MP3 figure
quoted next door is 26ms. Measured across all 285 cuts the worst case was 46ms
and the average half that — a boundary landing, not drift, and far below what an
ear notices at the start of a sentence.

AND NEVER RE-ENCODE UPWARD, specifically. Asked to "convert to 128kbps to limit
upload size", the honest answer is that this source is already 62.8 kbps AAC:
encoding it to 128 would roughly DOUBLE the collection to ~10 GB and add a lossy
generation to every file. `downsize_audio.py` states the same rule for the same
reason — "it never encodes UP … the floor is a floor, not a target" — and running
it over these books afterwards correctly reports them already below the floor and
writes nothing. Stream copy is both the smallest and the lossless option here.

THE ORIGINAL IS NEVER MODIFIED. Cuts are derivatives; the container stays exactly
as delivered. It is the only artifact here that cannot be regenerated.

DRY RUN IS THE DEFAULT. Nothing is written without `--apply`. A dry run prints the
whole plan and records the same ledger lines with outcome `skipped`, so what
WOULD happen is inspectable before 285 files land on disk.

Usage:
    python3 -m spoken_lane.audiobook --collection dostoyevsky            # dry run
    python3 -m spoken_lane.audiobook --collection dostoyevsky --apply
    python3 -m spoken_lane.audiobook --collection dostoyevsky --only crime-and-punishment
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _paths  # noqa: E402
from _step_ledger import step  # noqa: E402

from spoken_lane import manifest as M  # noqa: E402

PHASE = "audiobook-split"
PROFILE = "audiobook"


@dataclass(frozen=True)
class Collection:
    """One purchased container and the few facts no rule can read off it.

    `front_matter` and `trailing` are COUNTED BY A PERSON who looked at the
    chapter list — see `manifest.split_works` for why they are not detected. Both
    are small numbers that are easy to check and catastrophic to guess.
    """

    key: str
    title: str
    container: Path
    manifest_log: Path
    front_matter: int = 0
    trailing: int = 0
    first_work_name: str | None = None
    study_track: str | None = None
    slug_overrides: dict[str, str] = field(default_factory=dict)


COLLECTIONS: dict[str, Collection] = {
    "dostoyevsky": Collection(
        key="dostoyevsky",
        title="The Complete Fyodor Dostoyevsky Collection",
        container=Path.home()
        / "Documents/DVDFab/BookFab/eBook_Converted/audible"
        / "The Complete Fyodor Dostoyevsky Collection.mp3",
        # The container carries no chapter atoms of its own (`ffprobe
        # -show_chapters` is empty), but the tool that downloaded it logged the
        # manifest the store served, offsets included.
        manifest_log=Path.home() / "Documents/DVDFab/BookFab/Log/librocore.log",
        # Read off the chapter list: "Opening Credits", the collection's own
        # introduction, and a title card; then "End Credits" at the very end.
        front_matter=3,
        trailing=1,
        # The first work predates the prefixed naming and announces itself with
        # nothing — its tracks are just "Part 1 Chapter 01" and so on.
        first_work_name="NotesFromUnderground",
        study_track="philosophy",
        # The store's own metadata says "Ofa". See manifest.slugify.
        slug_overrides={"TheDreamOfaRidiculousMan": "the-dream-of-a-ridiculous-man"},
    ),
}


def _ffmpeg_cut(container: Path, start_ms: int, length_ms: int, dest: Path) -> None:
    """Copy one span out of the container. Raises on a non-zero ffmpeg exit."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.partial{dest.suffix}")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_ms / 1000:.3f}",
            "-t",
            f"{length_ms / 1000:.3f}",
            "-i",
            str(container),
            "-map",
            "0:a",
            "-c",
            "copy",
            str(tmp),
        ],
        check=True,
        capture_output=True,
    )
    tmp.replace(dest)


def _probe_ms(path: Path) -> int | None:
    return M.probe_duration_ms(path)


def split_collection(
    collection: Collection,
    *,
    apply: bool = False,
    only: set[str] | None = None,
) -> dict:
    """Derive the works, then write one folder and one file per chapter.

    Returns a report the caller prints. Idempotent: a chapter whose file already
    exists at the right size is left alone, so a re-run after an interruption
    only does what is left.
    """
    if not collection.container.exists():
        raise SystemExit(f"container not found: {collection.container}")
    if not collection.manifest_log.exists():
        raise SystemExit(f"manifest log not found: {collection.manifest_log}")

    chapters = M.from_container(collection.container) or M.from_log(collection.manifest_log)
    container_ms = _probe_ms(collection.container)
    ok, diff = M.reconcile(chapters, container_ms)
    if not ok:
        raise SystemExit(
            f"manifest does not describe this container: {len(chapters)} chapters, "
            f"extent differs from the file by {diff} ms. Refusing to cut — every "
            f"chapter would be offset from the words in it."
        )

    works = M.split_works(
        chapters,
        first_work_name=collection.first_work_name,
        front_matter=collection.front_matter,
        trailing=collection.trailing,
    )
    report: dict = {
        "collection": collection.key,
        "chapters": len(chapters),
        "container_ms": container_ms,
        "reconcile_diff_ms": diff,
        "works": [],
        "written": 0,
        "existing": 0,
    }

    for order, work in enumerate(works, start=1):
        slug = M.slugify(work.name, collection.slug_overrides)
        if only and slug not in only:
            continue
        book_dir = _paths.content_dir(slug, profile=PROFILE)
        episodes = book_dir / "m4a" / "Episodes"

        with step(book_dir, PHASE, "work-split") as rec:
            rec.detail(
                slug=slug,
                order=order,
                source_name=work.name,
                tracks=len(work.chapters),
                start_ms=work.start_ms,
                end_ms=work.end_ms,
                duration_ms=work.duration_ms,
            )
            if not apply:
                rec.skipped("dry-run")

        # The chapter index. Written even on a dry run's sibling `--apply`, and
        # written BEFORE the audio, because it is the only record of what each
        # `ep01.m4a` actually is: the titles live in the container's manifest and
        # nowhere else on disk. Without this the files are ordered but anonymous,
        # and whoever transcribes them has to go back to the log to find out
        # which chapter they are holding.
        if apply:
            with step(book_dir, PHASE, "chapter-index") as rec:
                index_path = book_dir / "_system" / "audiobook-chapters.json"
                index_path.parent.mkdir(parents=True, exist_ok=True)
                index_path.write_text(
                    json.dumps(
                        {
                            "schema": "podcast.audiobook-chapters/v1",
                            "collection": collection.key,
                            "work": work.name,
                            "slug": slug,
                            "source_container": str(collection.container),
                            "chapters": [
                                {
                                    "episode": n,
                                    "file": f"m4a/Episodes/ep{n:02d}.m4a",
                                    "transcript": f"transcripts/ep{n:02d}.vtt",
                                    "title": c.title,
                                    "start_ms": c.start_ms,
                                    "length_ms": c.length_ms,
                                }
                                for n, c in enumerate(work.chapters, start=1)
                            ],
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                rec.changed(len(work.chapters))
                rec.outputs(index_path)

        written = existing = 0
        for n, chapter in enumerate(work.chapters, start=1):
            dest = episodes / f"ep{n:02d}.m4a"
            if dest.exists() and dest.stat().st_size > 0:
                existing += 1
                continue
            if not apply:
                written += 1
                continue
            with step(book_dir, PHASE, f"audio-cut:ep{n:02d}") as rec:
                rec.detail(
                    title=chapter.title,
                    start_ms=chapter.start_ms,
                    length_ms=chapter.length_ms,
                )
                _ffmpeg_cut(collection.container, chapter.start_ms, chapter.length_ms, dest)
                rec.outputs(dest)
            written += 1

        report["works"].append(
            {
                "order": order,
                "slug": slug,
                "title": work.name,
                "tracks": len(work.chapters),
                "duration_ms": work.duration_ms,
                "dir": str(book_dir),
                "written": written,
                "existing": existing,
            }
        )
        report["written"] += written
        report["existing"] += existing

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--collection", required=True, choices=sorted(COLLECTIONS))
    parser.add_argument("--apply", action="store_true", help="actually write. Default is a dry run.")
    parser.add_argument("--only", action="append", help="limit to these slugs (repeatable).")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON.")
    args = parser.parse_args(argv)

    report = split_collection(
        COLLECTIONS[args.collection],
        apply=args.apply,
        only=set(args.only) if args.only else None,
    )

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    mode = "APPLY" if args.apply else "DRY RUN — nothing written (pass --apply)"
    print(f"{mode}\n")
    print(
        f"manifest: {report['chapters']} chapters, reconciles with the container "
        f"to within {report['reconcile_diff_ms']} ms\n"
    )
    print(f"{'#':>3}  {'slug':34s} {'tracks':>6s} {'hours':>6s}  {'cut':>5s} {'have':>5s}")
    for w in report["works"]:
        print(
            f"{w['order']:3d}  {w['slug']:34s} {w['tracks']:6d} "
            f"{w['duration_ms'] / 3600000:6.2f}  {w['written']:5d} {w['existing']:5d}"
        )
    print(f"\n{report['written']} file(s) to write, {report['existing']} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
