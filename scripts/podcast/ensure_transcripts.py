#!/usr/bin/env python3
"""Every episode that ships carries a transcript. If one is missing, make it.

    python3 scripts/podcast/ensure_transcripts.py <slug> [<slug> …]
        [--dry-run]   say what is missing and what it would cost, spend nothing
        [--force]     re-transcribe episodes that already have one
        [--locale]    speech locale (default en-US)

WHY THIS IS NOT `transcribe_notebooklm.py`

    That script globs `m4a/*.m4a` — files sitting LOOSE in the book's audio
    folder, which is where raw NotebookLM output lands while a podcast is still
    being made. Arranging those recordings into `m4a/Episodes/Session N — …/` is
    the author's act of declaring the podcast finished, and it is also what moves
    them out of that glob. The consequence, measured on the one book that ships a
    podcast: the transcriber sees zero of its twenty episodes.

    So this asks the PUBLISHER what it is about to ship — `_listener_book` knows
    both layouts and already decides which file belongs to which episode number —
    and guarantees a transcript for exactly those. "Every shipped episode has a
    transcript" is then true by construction rather than by remembering.

WHY IT RUNS INSIDE THE DEPLOY

    Because otherwise it does not run. A transcript that has to be remembered is
    a transcript that half the library will not have. It is idempotent and keyed
    on the file existing, so the everyday case — a re-push after writing Companion
    notes — asks Azure for nothing and costs nothing. Only a genuinely new episode
    is paid for, at about $0.30 an audio-hour, under standing Azure authorization.

WHAT IT WILL NOT DO

    It never writes `m4a/transcripts/<stem>.transcript.txt`. Four things read that
    file and a fresh transcription does not reproduce it — see the header of
    `_transcript.py`. Where a flat transcript already exists, this reports how far
    the new hearing has drifted from it and leaves it alone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_book import Book, load_book  # noqa: E402
from _transcript import (  # noqa: E402
    Cue,
    correct_terms,
    correction_map,
    flat_text,
    from_vtt,
    load_pronunciations,
    to_vtt,
    unheard_terms,
    vtt_path,
)

# Azure Speech fast transcription, Standard tier. Only used to print an estimate
# before spending; the ledger records what was actually billed.
USD_PER_AUDIO_HOUR = 0.30


def missing_for(book: Book, *, force: bool = False) -> list:
    """The episodes that ship audio and have no timed transcript yet."""
    out = []
    for episode in book.episodes:
        if episode.audio is None:
            continue
        if not force and vtt_path(book.directory, episode.number).is_file():
            continue
        out.append(episode)
    return out


def _drift(book: Book, episode, cues: list[Cue]) -> str | None:
    """How far this hearing sits from the flat transcript, when there is one.

    Reported, never acted on. A number here is not a fault — it is the model
    having moved since June — but a number that is suddenly large means the wrong
    file has been attached to an episode, which is worth seeing in the log.
    """
    import difflib

    folder = book.directory / "m4a" / "transcripts"
    if not folder.is_dir():
        return None
    stem = f"ch{episode.number:02d}"
    candidates = sorted(p for p in folder.glob("*.transcript.txt") if p.name.startswith(stem))
    if not candidates:
        return None
    old = candidates[0].read_text(encoding="utf-8")
    ratio = difflib.SequenceMatcher(None, old.split(), flat_text(cues).split()).ratio()
    return f"{ratio:.1%} of the wording matches {candidates[0].name} (left untouched)"


def ensure(
    slug: str,
    *,
    force: bool = False,
    dry_run: bool = False,
    locale: str = "en-US",
    transcriber=None,  # injectable for tests: (path, locale) -> TimedTranscript
    log=print,
) -> int:
    """Returns the number of transcripts written."""
    book = load_book(slug)
    shipping = [e for e in book.episodes if e.audio is not None]
    todo = missing_for(book, force=force)

    log(f"{slug}: {len(shipping)} episode(s) with audio, {len(todo)} without a transcript")

    if not shipping:
        return 0
    if not todo:
        log("  every shipped episode already has one — nothing to do, nothing spent.")
        return 0

    seconds = sum(e.duration_s or 0 for e in todo)
    log(f"  {seconds / 3600:.2f} audio-hours to transcribe — about ${seconds / 3600 * USD_PER_AUDIO_HOUR:.2f}")

    if dry_run:
        for episode in todo:
            log(f"  would transcribe ep{episode.number:02d} — {episode.title}")
        return 0

    if transcriber is None:
        import _azure
        from _engine import ENGINE_AZURE, TASK_TRANSCRIBE, engine_guard

        engine_guard(TASK_TRANSCRIBE, ENGINE_AZURE)
        creds = _azure.load_speech_creds()

        def transcriber(path: Path, loc: str):
            return _azure.transcribe_audio_timed(creds, path.read_bytes(), path.name, locale=loc)

    rows = load_pronunciations()
    mapping = correction_map(rows)
    written = 0
    # Kept so the "never heard" question can be asked of the WHOLE book at the
    # end. Asked per episode it reports thirty-five absences every time and means
    # nothing — see `unheard_terms`.
    heard: dict[int, list[Cue]] = {}

    for episode in todo:
        assert episode.audio is not None
        source = episode.audio.path
        log(f"  ep{episode.number:02d} {episode.title} — transcribing {source.name}...")

        result = transcriber(source, locale)
        cues = [
            Cue(offset_ms=p.offset_ms, duration_ms=p.duration_ms, text=p.text, speaker=p.speaker)
            for p in result.phrases
        ]

        if not cues:
            # Silent or corrupt audio, or a locale the model could not hear. Not
            # fatal: publishing a book must not stop because one recording failed
            # to transcribe, and the episode simply ships without one.
            log("    ERROR: no speech recognised — skipped, this episode ships without a transcript")
            continue

        cues, made = correct_terms(cues, mapping)

        out = vtt_path(book.directory, episode.number)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_vtt(cues), encoding="utf-8")
        written += 1

        speakers = sorted({c.speaker for c in cues if c.speaker is not None})
        log(
            f"    wrote {out.name} — {len(cues)} cues, "
            f"{'speakers ' + '/'.join(str(s) for s in speakers) if speakers else 'one voice'}, "
            f"{out.stat().st_size:,} bytes"
        )
        if made:
            log(
                f"    corrected {sum(c.count for c in made)} mishearing(s): "
                + ", ".join(f"{c.heard!r}->{c.corrected!r}x{c.count}" for c in made[:6])
            )

        heard[episode.number] = cues

        drift = _drift(book, episode, cues)
        if drift:
            log(f"    {drift}")

        try:
            from _cost_ledger import append_azure_stt_cost

            row = append_azure_stt_cost(
                book.directory,
                phase="publish",
                step=f"ensure-transcripts/ep{episode.number:02d}",
                duration_seconds=float(episode.duration_s or result.duration_ms / 1000),
            )
            log(f"    Azure ${row.cost_usd:.4f}")
        except Exception as exc:  # a ledger failure never costs us the transcript
            log(f"    WARN ledger append failed: {exc}")

    # Read every transcript this book now has, not only the ones just made, so a
    # single re-run of one episode still answers the question about the book.
    for episode in shipping:
        if episode.number in heard:
            continue
        path = vtt_path(book.directory, episode.number)
        if path.is_file():
            heard[episode.number] = from_vtt(path.read_text(encoding="utf-8"))

    unheard = unheard_terms(heard, rows, slug=slug)
    if unheard:
        log(
            f"  {len(unheard)} term(s) this book confirmed appear in no episode — "
            "likely mishearings to settle with the pronunciation probe:"
        )
        log(f"    {', '.join(unheard)}")

    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slugs", nargs="+", help="book slug(s)")
    ap.add_argument("--dry-run", action="store_true", help="report the work and the cost, spend nothing")
    ap.add_argument("--force", action="store_true", help="re-transcribe episodes that already have one")
    ap.add_argument("--locale", default="en-US", help="speech locale (default en-US)")
    args = ap.parse_args(argv)

    total = 0
    for slug in args.slugs:
        total += ensure(slug, force=args.force, dry_run=args.dry_run, locale=args.locale)
    if not args.dry_run:
        print(f"\ndone: {total} transcript(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
