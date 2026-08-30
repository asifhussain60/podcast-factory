#!/usr/bin/env python3
"""Every episode that ships carries a transcript. If one is missing, make it.

    python3 scripts/podcast/ensure_transcripts.py <slug> [<slug> …]
        [--dry-run]      say what is missing and what it would cost, spend nothing
        [--force]        re-transcribe episodes that already have one
        [--locale]       speech locale (default en-US)
        [--adopt-from D] read externally-produced timed transcripts from D
        [--adopt-only]   never call Azure; fail loudly instead of spending

WHERE A TRANSCRIPT COMES FROM, IN ORDER

    1. one already on disk        nothing happens, nothing is spent
    2. one somebody handed us     adopted, nothing is spent
    3. Azure                      bought, at about $0.30 an audio-hour

    Step 2 is checked before step 3 because on lecture audio the bought one is
    the WORSE artifact, not merely the dearer one — see the header of
    `_external_transcript.py` for the measurement. Files are looked for in
    `<book>/transcripts/_inbox/` by default, so the everyday case is "drop the
    exports in the folder and publish" with nothing to remember.

    A dropped file that fails its checks does NOT silently become an Azure
    purchase: the failure is logged by name with its reason first, so the bill
    is never the first time anyone hears the export was bad. It then falls
    through to Azure anyway, because this runs inside the deploy and a bad
    export must not be able to stop a finished book from publishing. `--adopt-only`
    is the switch for a run that must prove it spent nothing.

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
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _external_transcript import Candidate, discover, read_candidate  # noqa: E402
from _listener_book import Book, load_book  # noqa: E402
from _transcript import (  # noqa: E402
    TRANSCRIPT_DIR,
    Cue,
    correct_terms,
    correction_map,
    flat_text,
    from_vtt,
    load_pronunciations,
    read_provenance,
    to_vtt,
    unheard_terms,
    vtt_path,
    write_provenance,
)

# Azure Speech fast transcription, Standard tier. Only used to print an estimate
# before spending; the ledger records what was actually billed.
USD_PER_AUDIO_HOUR = 0.30

#: Where dropped transcripts are looked for when `--adopt-from` is not given.
#: Under `transcripts/` rather than beside the audio because `.gitignore`
#: excludes `content/**/m4a/**` — the same reasoning `vtt_path` gives for the
#: transcripts themselves. The exports are the evidence for what we shipped.
INBOX_DIR = "_inbox"


def inbox_path(book_dir: Path) -> Path:
    return book_dir / TRANSCRIPT_DIR / INBOX_DIR


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


def _offered(book: Book, todo: list, *, adopt_from: Path | None, log) -> dict[int, Candidate]:
    """Read and judge every dropped file that claims an episode we still need.

    Judged BEFORE anything is written or bought, so the run can say up front how
    much of the work is already covered and what the rest will cost.

    A file claiming an episode this book ALREADY HAS is ignored in silence:
    re-dropping the whole folder after one new recording is the normal way to
    use this, and complaining about the twenty files that are already done would
    bury the one line that matters.

    A file claiming an episode the book DOES NOT HAVE is reported. It is the
    same silent-failure class the checks exist for: `[Part 41]` dropped into a
    twenty-episode book is a wrong folder or a misread name, it changes nothing,
    and without a line here the operator's only evidence is a bill for the
    episode they thought they had just supplied.
    """
    folder = adopt_from if adopt_from is not None else inbox_path(book.directory)
    found = discover(folder)
    for complaint in found.complaints:
        log(f"  ! {complaint}")

    known = {e.number for e in book.episodes}
    wanted = {e.number: e for e in todo}
    out: dict[int, Candidate] = {}
    for number, path in sorted(found.by_episode.items()):
        if number not in known:
            log(
                f"  ! {path.name}: claims episode {number}, but this book has "
                f"{len(known)} episode(s) — nothing was done with it"
            )
            continue
        episode = wanted.get(number)
        if episode is None:
            continue
        out[number] = read_candidate(number, path, audio_duration_s=episode.duration_s)
    return out


def _store(
    book: Book,
    episode,
    cues: list[Cue],
    mapping: dict[str, str],
    *,
    origin: str,
    detail: str,
    coverage: float | None,
    log,
) -> tuple[Path, dict]:
    """Correct, write, and describe one transcript — whatever produced it.

    Both routes come through here on purpose. The pronunciation correction pass
    is the only thing standing between a mangled religious term and the printed
    page, and a second write path would eventually be added without it: an
    adopted transcript would then ship uncorrected while a bought one did not,
    and the difference would be invisible until a reader found it.
    """
    cues, made = correct_terms(cues, mapping)

    out = vtt_path(book.directory, episode.number)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_vtt(cues), encoding="utf-8")

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

    row = {
        "source": origin,
        "detail": detail,
        "cues": len(cues),
        "corrections": sum(c.count for c in made),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    # Recorded as null rather than omitted when the recording's length is
    # unknown, so "not checked" is visibly different from "checked and fine".
    if origin == "external":
        row["coverage"] = coverage
    return out, row


def ensure(
    slug: str,
    *,
    force: bool = False,
    dry_run: bool = False,
    locale: str = "en-US",
    adopt_from: Path | None = None,
    adopt_only: bool = False,
    transcriber=None,  # injectable for tests: (path, locale) -> TimedTranscript
    log=print,
) -> int:
    """Returns the number of transcripts written, adopted or bought."""
    book = load_book(slug)
    shipping = [e for e in book.episodes if e.audio is not None]
    todo = missing_for(book, force=force)

    log(f"{slug}: {len(shipping)} episode(s) with audio, {len(todo)} without a transcript")

    if not shipping:
        return 0
    if not todo:
        log("  every shipped episode already has one — nothing to do, nothing spent.")
        return 0

    offered = _offered(book, todo, adopt_from=adopt_from, log=log)
    adoptable = {n: c for n, c in offered.items() if c.adoptable}
    rejected = {n: c for n, c in offered.items() if not c.adoptable}

    for number, candidate in sorted(rejected.items()):
        # Named and explained BEFORE the cost line, so a bad export is never
        # discovered after the fact by reading a bill.
        log(f"  ! ep{number:02d} {candidate.path.name} REJECTED, will not be adopted:")
        for reason in candidate.problems:
            log(f"      - {reason}")

    buying = [e for e in todo if e.number not in adoptable]

    if adoptable:
        log(f"  {len(adoptable)} transcript(s) supplied and verified — adopting, nothing spent for these")

    if buying and adopt_only:
        log(
            f"  ! --adopt-only: {len(buying)} episode(s) have no usable transcript "
            f"({', '.join(f'ep{e.number:02d}' for e in buying)}) — refusing to spend; they stay untranscribed"
        )
        buying = []

    seconds = sum(e.duration_s or 0 for e in buying)
    if buying:
        log(f"  {seconds / 3600:.2f} audio-hours to transcribe — about ${seconds / 3600 * USD_PER_AUDIO_HOUR:.2f}")

    if dry_run:
        for episode in todo:
            if episode.number in adoptable:
                log(f"  would adopt ep{episode.number:02d} — {adoptable[episode.number].path.name}")
            elif episode in buying:
                log(f"  would transcribe ep{episode.number:02d} — {episode.title}")
            else:
                log(f"  would leave ep{episode.number:02d} without a transcript — {episode.title}")
        return 0

    if buying and transcriber is None:
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
    provenance = read_provenance(book.directory)

    buying_numbers = {e.number for e in buying}

    for episode in todo:
        assert episode.audio is not None
        source = episode.audio.path
        candidate = adoptable.get(episode.number)

        if candidate is not None:
            log(f"  ep{episode.number:02d} {episode.title} — adopting {candidate.path.name}")
            cues = candidate.cues
            out, row = _store(
                book,
                episode,
                cues,
                mapping,
                origin="external",
                detail=candidate.path.name,
                coverage=candidate.coverage,
                log=log,
            )
            if candidate.coverage is not None:
                log(f"    covers {candidate.coverage:.0%} of the recording")
            else:
                log("    coverage NOT verified — the recording's length is unknown on this machine")
        elif episode.number in buying_numbers:
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
            out, row = _store(
                book,
                episode,
                cues,
                mapping,
                origin="azure",
                detail=f"{locale} fast-transcription",
                coverage=None,
                log=log,
            )
            try:
                from _cost_ledger import append_azure_stt_cost

                billed = append_azure_stt_cost(
                    book.directory,
                    phase="publish",
                    step=f"ensure-transcripts/ep{episode.number:02d}",
                    duration_seconds=float(episode.duration_s or result.duration_ms / 1000),
                )
                row["cost_usd"] = billed.cost_usd
                log(f"    Azure ${billed.cost_usd:.4f}")
            except Exception as exc:  # a ledger failure never costs us the transcript
                log(f"    WARN ledger append failed: {exc}")
        else:
            # Rejected export under --adopt-only, or nothing offered while
            # spending was refused. Already reported above; nothing more to say.
            continue

        written += 1
        heard[episode.number] = from_vtt(out.read_text(encoding="utf-8"))
        provenance[f"{episode.number:02d}"] = row

        drift = _drift(book, episode, heard[episode.number])
        if drift:
            log(f"    {drift}")

    if written:
        write_provenance(book.directory, provenance)

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
    ap.add_argument(
        "--adopt-from",
        type=Path,
        default=None,
        metavar="DIR",
        help="read externally-produced timed transcripts (.vtt/.srt) from DIR "
        "instead of the book's transcripts/_inbox/",
    )
    ap.add_argument(
        "--adopt-only",
        action="store_true",
        help="never call Azure — report what could not be adopted and spend nothing",
    )
    args = ap.parse_args(argv)

    total = 0
    for slug in args.slugs:
        total += ensure(
            slug,
            force=args.force,
            dry_run=args.dry_run,
            locale=args.locale,
            adopt_from=args.adopt_from,
            adopt_only=args.adopt_only,
        )
    if not args.dry_run:
        print(f"\ndone: {total} transcript(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
