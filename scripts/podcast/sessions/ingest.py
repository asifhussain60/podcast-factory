"""Lay one delivered series down at content/Sessions/<slug>/.

The output is an ordinary book folder — `_listener_book.load_book` is given no
hint that this content came from a lecture rather than a translation, because the
moment it needs one, two code paths exist for the same question.

WHAT THIS DOES NOT DO

  transcription   `ensure_transcripts.py` already asks the publisher what it is
                  about to ship and fills the gaps with Azure timed output
  Arabic          `_book_apparatus` runs standalone over the composed book.md
  episode design  there is nothing to design; a recording IS an episode

THE AUDIO MAP IS WRITTEN OUT, NOT INFERRED

Recording order and session order agree for every series here, but they are not
the same list: Love Of The Prophet has five recordings against six sessions, and
the one without a recording is the opener, so position alone puts the whole
series off by one. Rather than encode an offset that is right once and wrong
everywhere else, each series states which file belongs to which session. A
pairing Asif confirmed is data; a pairing a rule derived is a guess wearing the
same clothes.

The filenames are also taken from disk rather than from Drive, which reports
older titles for two of these five — a map built from the API finds three files
and silently drops two lectures.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from _paths import content_dir, ensure_book_skeleton

from .convert import convert, localise_images
from .dump import Session, duplicate_transcripts, load_sessions

# The Drive mount holding the recordings and the session images. Anchored to the
# home directory and overridable, because an absolute path baked into pipeline
# source only works on the machine it was written on.
DRIVE_ROOT = Path(
    os.environ.get(
        "PODCAST_FACTORY_SESSIONS_ROOT",
        Path.home() / "Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com/My Drive/SESSIONS",
    )
)
AUDIO_ROOT = DRIVE_ROOT / "Quran Studies"
IMAGE_ROOT = DRIVE_ROOT / "Resources Images"

PROFILE = "islamic_session"


@dataclass(frozen=True)
class Series:
    group_id: int
    slug: str
    title: str
    audio_dir: str  # relative to AUDIO_ROOT
    audio_map: dict[str, int]  # audio filename -> session Sequence
    # Sessions whose stored transcript must be ignored in favour of the
    # recording's own transcription. Session 211 holds a 99.96% copy of session
    # 215, so publishing it verbatim would put a different lecture under its
    # title; the recording is the only witness to what was actually said.
    transcript_from_audio: frozenset[int] = field(default_factory=frozenset)


SERIES: dict[str, Series] = {
    "love-of-the-prophet": Series(
        group_id=14,
        slug="love-of-the-prophet",
        title="Love Of The Prophet",
        audio_dir="Love Of The Prophet",  # the 2025/ re-delivery is deliberately excluded
        # Filenames exactly as they sit on disk, including the missing space in
        # "02cNeed" — the Drive API reports older titles for two of these, so a
        # map built from what the API says finds three of the five files.
        audio_map={
            "01 What is Love.mp3": 2,
            "02cNeed for Messengers.mp3": 3,
            "03 Islam as an experience.mp3": 4,
            "04 Character Of our prophet.mp3": 5,
            "05 Model For Success.mp3": 6,
        },
        transcript_from_audio=frozenset({2}),
    ),
}


@dataclass
class Report:
    slug: str
    chapters: int = 0
    episodes: int = 0
    words: int = 0
    quotes: int = 0
    badges_dropped: int = 0
    chrome_dropped: int = 0
    images_copied: int = 0
    images_missing: list[str] = field(default_factory=list)
    awaiting_transcription: list[int] = field(default_factory=list)
    unmapped_audio: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"  {self.slug}",
            f"    chapters {self.chapters}   episodes {self.episodes}   words {self.words:,}",
            f"    quotations promoted {self.quotes}",
            f"    dropped: {self.badges_dropped} verse badges, {self.chrome_dropped} editor controls",
            f"    images copied {self.images_copied}",
        ]
        if self.images_missing:
            lines.append(f"    images MISSING ({len(self.images_missing)}): {', '.join(self.images_missing[:4])}")
        if self.awaiting_transcription:
            seqs = ", ".join(str(n) for n in self.awaiting_transcription)
            lines.append(f"    reading text awaiting transcription for session(s): {seqs}")
        if self.unmapped_audio:
            lines.append(f"    audio with no session: {', '.join(self.unmapped_audio)}")
        lines.extend(f"    note: {n}" for n in self.notes)
        return "\n".join(lines)


def _meta_yml(series: Series, chapters: int) -> str:
    return (
        f"slug: {series.slug}\n"
        f"title: {series.title}\n"
        "\n"
        "series:\n"
        "  # Sessions are delivered lectures: the reading edition is the transcript,\n"
        "  # so the book branch is the whole deliverable rather than a companion to\n"
        "  # generated audio.\n"
        "  enable_book_branch: true\n"
        "  enable_slide_decks: false\n"
        "\n"
        "pipeline:\n"
        f"  # {chapters} chapters, one per delivered session. orchestrator-state.json\n"
        "  # is authoritative; this block is a human-readable mirror.\n"
        "  lane: sessions\n"
    )


def _series_config(series: Series) -> str:
    return (
        f"# series-config.yaml — {series.title}\n"
        "# Delivered lecture sessions ingested from KSESSIONS_DEV.\n"
        "\n"
        f"content_profile: {PROFILE}\n"
        "\n"
        '# The speaker is the author and the transcript records him saying "I".\n'
        "# Declared rather than inherited so the route stays readable here.\n"
        "narrative_frame: first_person_author\n"
        "\n"
        "# The source is a lecture, not a printed text. Gates that exist to catch a\n"
        "# translation reading like a calque do not apply to speech.\n"
        "source_medium: audio_lecture\n"
        "source_language: en\n"
        "\n"
        "book_voice: faithful\n"
        "book_augmentation: none\n"
        "book_visuals: manual_only\n"
        "\n"
        "enable_video: false\n"
    )


def _contract(series: Series, session: Session, number: int) -> str:
    blurb = session.description.replace("\n", " ").strip()
    if blurb.startswith("<--"):  # the admin's own placeholder
        blurb = ""
    safe = blurb.replace('"', "'")
    return (
        f"book_slug: {series.slug}\n"
        f"episode_number: {number}\n"
        f'title: "{session.name}"\n'
        f"source_session_id: {session.session_id}\n"
        f"source_sequence: {session.sequence}\n"
        "episode_format: lecture\n"
        "show_notes:\n"
        f'  blurb: "{safe}"\n'
    )


def ingest(slug: str, *, dry_run: bool = False) -> Report:
    series = SERIES[slug]
    report = Report(slug=slug)

    sessions = load_sessions(series.group_id)
    by_sequence = {s.sequence: s for s in sessions}

    for left, right in duplicate_transcripts(sessions):
        report.notes.append(f"sessions {left} and {right} hold near-identical transcripts")

    audio_dir = AUDIO_ROOT / series.audio_dir
    present = {p.name: p for p in audio_dir.iterdir() if p.suffix.lower() == ".mp3"}
    for name in sorted(present):
        if name not in series.audio_map:
            report.unmapped_audio.append(name)

    book_dir = content_dir(slug, profile=PROFILE)
    if not dry_run:
        ensure_book_skeleton(book_dir)
        (book_dir / "m4a" / "Episodes").mkdir(parents=True, exist_ok=True)
        (book_dir / "book" / "images").mkdir(parents=True, exist_ok=True)

    # --- chapters -----------------------------------------------------------
    parts = [f"# {series.title}", ""]
    for session in sessions:
        use_audio = session.sequence in series.transcript_from_audio
        converted = convert("" if use_audio else session.transcript_html)
        body, wanted = localise_images(converted.markdown, slug)

        report.chapters += 1
        report.quotes += converted.quotes
        report.badges_dropped += converted.dropped_badges
        report.chrome_dropped += converted.dropped_chrome
        report.words += len(body.split())

        if use_audio or not body.strip():
            report.awaiting_transcription.append(session.sequence)
            body = body or ""

        for session_id, filename in wanted:
            source = IMAGE_ROOT / session_id / filename
            target = book_dir / "book" / "images" / session_id / filename
            if not source.exists():
                report.images_missing.append(f"{session_id}/{filename}")
                continue
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            report.images_copied += 1

        parts.extend([f"## {session.name}", "", body, ""])

    if not dry_run:
        (book_dir / "book" / "book.md").write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
        (book_dir / "meta.yml").write_text(_meta_yml(series, report.chapters), encoding="utf-8")
        (book_dir / "_system" / "series-config.yaml").write_text(_series_config(series), encoding="utf-8")

    # --- episodes -----------------------------------------------------------
    # Flat layout: five recordings sit directly in m4a/Episodes/ with no
    # `Session N` folders, which is what `collect_audio` reads for a series under
    # the grouping threshold — the catalog then renders one untitled list.
    for number, (filename, sequence) in enumerate(sorted(series.audio_map.items(), key=lambda kv: kv[1]), start=1):
        session = by_sequence.get(sequence)
        if session is None or filename not in present:
            continue
        report.episodes += 1
        if dry_run:
            continue
        shutil.copy2(present[filename], book_dir / "m4a" / "Episodes" / f"ep{number:02d}.mp3")
        (book_dir / "chapter-contracts" / f"ep{number:02d}-{slug}.yml").write_text(
            _contract(series, session, number), encoding="utf-8"
        )

    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest a delivered lecture series.")
    parser.add_argument("slug", choices=sorted(SERIES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    report = ingest(args.slug, dry_run=args.dry_run)
    print(("DRY RUN — nothing written\n" if args.dry_run else "") + report.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
