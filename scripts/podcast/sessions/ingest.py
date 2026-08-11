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

Recording order and session order agree nowhere near well enough to derive. Love
Of The Prophet has five recordings against six sessions and the one without a
recording is the opener, so position alone puts the series off by one; Surah
Al-Fateha's files are numbered 003-014 against sessions 4 and 13-23, so `003` is
session 14 and `007` is session 4 and reading the filename as a sequence puts
eleven of its twelve lectures under the wrong title.

So each series STATES which file belongs to which session, in `series.py`. A
pairing Asif confirmed is data; a pairing a rule derived is a guess wearing the
same clothes. That module holds every per-series fact for the same reason, and
this one holds the procedure that is identical for all of them.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from _book_edits import apply_composer_edits
from _book_frontmatter import apply_introduction
from _paths import content_dir, ensure_book_skeleton

from .convert import convert, localise_images
from .dump import Session, duplicate_transcripts, load_sessions
from .series import AUDIO_ROOT, IMAGE_ROOT, PROFILE, SERIES, Series


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
    # Corpus images the author referenced through a host — the live admin, or his
    # own dev server. Counted because they were classified as unreachable for as
    # long as this lane existed, and the number is how anyone would notice if the
    # classification regressed.
    images_recovered: int = 0
    images_external: list[str] = field(default_factory=list)  # genuinely elsewhere; not emitted
    images_unmappable: list[str] = field(default_factory=list)  # name no file in the corpus
    from_audio: list[int] = field(default_factory=list)
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
        if self.images_recovered:
            lines.append(f"    images recovered from a host-prefixed reference: {self.images_recovered}")
        if self.images_missing:
            lines.append(
                f"    images MISSING from the corpus, lifted out of the prose "
                f"({len(self.images_missing)}): {', '.join(self.images_missing[:4])}"
            )
        if self.images_unmappable:
            lines.append(
                f"    image references naming no corpus file, not rendered "
                f"({len(self.images_unmappable)}): {', '.join(self.images_unmappable[:3])}"
            )
        if self.images_external:
            lines.append(
                f"    images on another site, not rendered "
                f"({len(self.images_external)}): {', '.join(self.images_external[:3])}"
            )
        if self.from_audio:
            seqs = ", ".join(str(n) for n in self.from_audio)
            lines.append(f"    reading text taken from the recording for session(s): {seqs}")
        if self.awaiting_transcription:
            seqs = ", ".join(str(n) for n in self.awaiting_transcription)
            lines.append(f"    NO reading text at all for session(s): {seqs}")
        if self.unmapped_audio:
            lines.append(f"    audio with no session: {', '.join(self.unmapped_audio)}")
        lines.extend(f"    note: {n}" for n in self.notes)
        return "\n".join(lines)


def _without_image(body: str, path: str) -> str:
    """Lift one illustration out of the prose, leaving the paragraphs around it.

    Called for a reference the corpus cannot answer — 2 of Surah Al-Fateha's 65,
    2 of Wise Reminder's 131. The picture was lost years before this repo existed
    and no code here can bring it back; the only choice is whether the reader
    meets a broken icon or the sentence that surrounded it. The name is in the
    report either way.

    The blank line left behind is collapsed, because `convert` separates blocks
    with exactly one and a stray double gap is a visible hole where a figure used
    to be.
    """
    without = re.sub(rf"!\[[^\]]*\]\(\s*{re.escape(path)}\s*\)", "", body)
    return re.sub(r"\n{3,}", "\n\n", without).strip()


def _title_of(series: Series, session: Session) -> str:
    return series.title_fixes.get(session.sequence, session.name)


def _heard_text(book_dir: Path, episode: int | None) -> str:
    """What the recording says, as paragraphs, or "" when there is no transcript.

    The cues are grouped into paragraphs rather than emitted one per line: a VTT
    cue is a breath, not a sentence, and one line per breath reads as a subtitle
    file rather than as a chapter. Twelve is the smallest grouping that produced
    paragraphs of ordinary length across all five of these recordings — it is a
    rhythm, and the articulation pass repunctuates and re-breaks it afterwards.
    """
    if episode is None:
        return ""
    path = book_dir / "transcripts" / f"ep{episode:02d}.vtt"
    if not path.exists():
        return ""

    from _transcript import from_vtt  # local: only this branch needs it

    lines = [cue.text.strip() for cue in from_vtt(path.read_text(encoding="utf-8")) if cue.text.strip()]
    return "\n\n".join(" ".join(lines[i : i + 12]) for i in range(0, len(lines), 12))


# The lane's own steps, in the order it runs them. Written into the state file so
# every tool that asks "how far along is this book" — the status card, the
# cross-book dashboard, `_paths.status_for` — gets an answer, instead of reading
# a book with no state file as a fresh orchestrator run stalled at 0% of a
# twenty-nine-step sequence it does not run.
#
# Deliberately the SAME file the orchestrator writes, under the same key. A
# second progress file for a second lane would be a second answer to one
# question, and the first tool to read the wrong one would be silently wrong.
LANE_STEPS: tuple[str, ...] = (
    "sessions-ingest",
    "sessions-transcribe",
    "sessions-articulate",
    "sessions-preface",
    "sessions-apparatus",
)


def _write_state(book_dir: Path, series: Series, *, done_through: str) -> None:
    """Record what this lane has actually finished, and claim nothing else.

    `status` is `draft` and stays `draft`: publishing is a decision a person
    makes, and nothing here may make a book audience-facing by running.
    """
    path = book_dir / "_system" / "orchestrator-state.json"
    prior = {}
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prior = {}

    cut = LANE_STEPS.index(done_through)
    phases = {step: {"status": "completed" if i <= cut else "pending"} for i, step in enumerate(LANE_STEPS)}

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "book_slug": series.slug,
                "category": "lectures",
                "branch": f"Sessions/{series.slug}",
                "pipeline_mode": "sessions_lane",
                "phase": done_through,
                "phase_status": "completed",
                "last_completed_phase": done_through,
                "next_phase": LANE_STEPS[cut + 1] if cut + 1 < len(LANE_STEPS) else None,
                "last_error": None,
                "phases": phases,
                # Never promoted here. `publish_to_library.py` is what flips it,
                # and only after a person has looked at the book.
                "status": prior.get("status", "draft"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _meta_yml(series: Series, chapters: int) -> str:
    return (
        f"slug: {series.slug}\n"
        f"title: {series.title}\n"
        f'title_arabic: "{series.title_arabic}"\n'
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
        f'title: "{_title_of(series, session)}"\n'
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

    # Which recording carries which session. Computed once, before the chapters,
    # because a chapter with no usable stored transcript has to be able to ask
    # for its own recording's transcription — the two loops read the same map
    # rather than each deriving the pairing.
    episode_of = {
        sequence: number
        for number, (_, sequence) in enumerate(sorted(series.audio_map.items(), key=lambda kv: kv[1]), start=1)
    }

    # --- chapters -----------------------------------------------------------
    parts = [f"# {series.title}", ""]
    for session in sessions:
        if session.sequence in series.preface_sessions:
            report.notes.append(
                f"session {session.sequence} ({session.name}) is a spoken opening — "
                "replaced by the edition's own introduction"
            )
            continue
        use_audio = session.sequence in series.transcript_from_audio
        converted = convert("" if use_audio else session.transcript_html)
        body, wanted = localise_images(converted.markdown)

        # The illustrations, resolved BEFORE the chapter is written, because a
        # reference the corpus cannot answer must not reach the page.
        #
        # `wanted` is what the prose now points at; each one is copied into the
        # book's own `book/images/` so the print edition and the site read the
        # same file. One that is not on disk is named in the report AND lifted
        # out of the prose: reporting alone would still leave a broken-image icon
        # in a printed reading edition, and "report, do not silently drop" is
        # satisfied by the report — the drop is the opposite of silent.
        for session_id, filename in wanted:
            source = IMAGE_ROOT / session_id / filename
            target = book_dir / "book" / "images" / session_id / filename
            if not source.exists():
                report.images_missing.append(f"{session_id}/{filename}")
                body = _without_image(body, f"images/{session_id}/{filename}")
                continue
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            report.images_copied += 1

        report.images_recovered += len(converted.hosted_images)
        report.images_external.extend(converted.external_images)
        report.images_unmappable.extend(converted.unmappable_images)

        # No usable stored text: take what the recording says instead. The VTT
        # is written by `ensure_transcripts.py` before this runs, and it is read
        # rather than re-derived — the cues on disk are what the Listen panel
        # follows, so the Read tab and the transcript panel cannot disagree
        # about what was said. Absent, the chapter stays empty and is reported.
        if use_audio or not body.strip():
            heard = _heard_text(book_dir, episode_of.get(session.sequence))
            if heard:
                body = heard
                report.from_audio.append(session.sequence)
            else:
                report.awaiting_transcription.append(session.sequence)

        report.chapters += 1
        report.quotes += converted.quotes
        report.badges_dropped += converted.dropped_badges
        report.chrome_dropped += converted.dropped_chrome
        report.words += len(body.split())

        parts.extend([f"## {_title_of(series, session)}", "", body, ""])

    # The episode-to-chapter bridge, WRITTEN OUT rather than derived at read
    # time — `read_bridge` refuses to infer, and it is right to for a book.
    #
    # A book's episodes are a re-segmentation: NotebookLM was given chapters and
    # produced episodes along its own lines, so which chapter an episode covers
    # is a judgement somebody has to make. A lecture has no such gap. The
    # recording IS the session and the chapter is that same session's transcript
    # — they are one thing filed twice, so the pairing is an identity, and it is
    # the SAME `audio_map` the recordings themselves were placed by. This writes
    # the file `read_bridge` already reads; it does not teach it a new rule.
    bridge = {
        str(number): [_title_of(series, by_sequence[sequence])]
        for sequence, number in sorted(episode_of.items())
        if sequence in by_sequence
    }

    if not dry_run:
        (book_dir / "_system" / "listener-episode-chapters.json").write_text(
            json.dumps(bridge, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (book_dir / "book" / "book.md").write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
        (book_dir / "meta.yml").write_text(_meta_yml(series, report.chapters), encoding="utf-8")
        (book_dir / "_system" / "series-config.yaml").write_text(_series_config(series), encoding="utf-8")

        # The human's text goes back on top, LAST — the same final step, and the
        # same function, that `compose_book_v2` ends with.
        #
        # Without this, running the ingest a second time would silently discard
        # every articulated chapter and every Composer save, and the run would
        # report success while doing it. That is precisely the failure the
        # singular-edit rule exists to prevent, and a lane that regenerates
        # book.md is a lane that has to honour it.
        #
        # A chapter is re-converted whether it carries an edit or not, unlike the
        # book route which skips regenerating an edited chapter. It can afford
        # to: conversion here is a deterministic HTML walk with no model behind
        # it, so there is no cost to pay and nothing to protect from being
        # re-derived. Only the OUTCOME has to match, and the replay decides that.
        # The edition's own introduction, before the replay so a human edit to it
        # still wins. Authored ONCE per book and cached — `apply_introduction` is
        # idempotent and asks the model again only under `force`, so re-running
        # the ingest costs nothing and cannot rewrite a preface Asif has read.
        #
        # The SAME function every other route uses. A lecture series needs the
        # same thing a translated treatise needs — a short, honestly titled page
        # saying what this is and what is in it — and a second implementation of
        # it here would be a second answer to that question, drifting from the
        # first the moment either changed. What the lane supplies is the fact
        # that this book is spoken; the brief adapts on `source_medium`.
        intro = apply_introduction(book_dir, log=lambda *_: None)
        if intro.get("words"):
            report.notes.append(f"edition introduction: {intro['words']} words")
        elif intro.get("reason"):
            report.notes.append(f"edition introduction NOT written: {intro['reason']}")

        replayed = apply_composer_edits(book_dir, log=lambda *_: None)

        # LAST, so it describes the run that just happened rather than the one
        # that was about to. `sessions-preface` is the furthest step this
        # function performs; transcription runs before it and the apparatus
        # after, each stamping its own.
        _write_state(book_dir, series, done_through="sessions-preface")
        if replayed["applied"]:
            report.notes.append(f"{replayed['applied']} authored chapter(s) replayed over the fresh text")
        if replayed["orphaned"]:
            report.notes.append(f"{replayed['orphaned']} saved edit(s) name a chapter this ingest did not produce")

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
