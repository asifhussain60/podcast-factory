"""Make a spoken chapter readable, and time it against the recording it came from.

A Sessions chapter whose prose came off the tape is the only kind of chapter in
this repo that must NOT be rewritten. Everywhere else the pipeline's job is to
turn a source into a book; here the paragraphs have to stay the words on the
recording, because the reader lights them up one at a time as Asif's own voice
reaches them. Rewriting a sentence breaks the only thing that makes the pairing
honest.

So this module does three narrow things, in order:

  CORRECT   spelling, punctuation, paragraph breaks, and the words the
            transcription dropped mid-sentence. Nothing else. The gate below
            measures how much of the original wording survived and REVERTS a
            window that failed it, so a pass that starts rewriting produces the
            raw transcription rather than literary prose — a no-op, never a loss.
            This is deliberately not `rearticulate`: that engine's contract is to
            make prose read like a book, which is the opposite of the contract
            here.

  SCRIPT    put the Arabic back. The transcription writes it phonetically
            ("Bismillahir Rahmanir Rahim"), and this book is an Islamic reading
            edition. Resolution goes through `_book_romanization`'s existing
            ladder, so a Qur'anic run comes back as the canonical mushaf's own
            vowelled wording rather than anyone's reconstruction of it, and every
            run records which rung answered it.

  TIME      pair each finished paragraph with the seconds of audio it was
            transcribed from, and write the manifest the Podcast Factory Library
            already reads for read-along. Where the pairing cannot be made
            confidently the chapter is published with NO cues: the recording
            still plays, and nothing is highlighted. A paragraph lit up while a
            different one is being spoken is worse than no highlighting at all.

WHAT IT DOES NOT DO. It renders no audio and uploads nothing. The recording is
already on the site serving the episode player, and the manifest points at that
same object rather than a second copy of it.

ORDER IS FORCED, same reasoning as `sessions-apparatus`: this rewrites prose
for spoken chapters, so it must run after `sessions-articulate` finishes,
never before. `main()` refuses to run while `sessions-articulate` is not
`completed`. On success (including the no-op "no spoken chapters" case) it
records `sessions-read-along` as `completed` in orchestrator-state.json, the
same state file every other lane step writes, so the lane's own apparatus
step — and the status card — can tell this one actually ran.

Usage:
    python3 scripts/podcast/sessions/read_along.py <slug> [--force] [--limit N]
    python3 scripts/podcast/sessions/read_along.py <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _align_paragraphs import SELF_SUPPORT, align, is_monotonic  # noqa: E402
from _book_edits import fingerprint, write_chapter_body  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _transcript import from_vtt  # noqa: E402
from reader_narration import audio_duration_seconds, chapter_blocks  # noqa: E402

from sessions.ingest import ARTICULATE_STEP, READ_ALONG_STEP, _write_state  # noqa: E402
from sessions.series import SERIES  # noqa: E402
from sessions.spoken import spoken_chapters  # noqa: E402

PHASE = "sessions-read-along"
MANIFEST_SCHEMA = 1

#: The share of transcript cues that must land on a paragraph with real evidence
#: before the timings are trusted enough to publish.
_CUE_CONFIDENCE = 0.55

# correct/restore_script/retention/detect_runs/_mushaf_wording moved to
# `_verbatim_correct.py` (2026-08-30) so phase 0d can reuse them without the
# core pipeline importing this lane module. Re-exported here (retention,
# detect_runs, _mushaf_wording verbatim; correct/restore_script as thin
# wrappers pinning `phase=PHASE`) so every existing import of this module —
# including the test suite — keeps working exactly as before.
from _verbatim_correct import _mushaf_wording as _mushaf_wording  # noqa: F401
from _verbatim_correct import correct as _vc_correct
from _verbatim_correct import detect_runs as detect_runs  # noqa: F401
from _verbatim_correct import restore_script as _vc_restore_script
from _verbatim_correct import retention as retention  # noqa: F401


def correct(book_dir: Path, base: str, *, label: str, log=print) -> tuple[str, list[str]]:
    return _vc_correct(book_dir, base, phase=PHASE, label=label, log=log)


def restore_script(book_dir: Path, text: str, *, label: str, book_title: str = "", log=print):
    return _vc_restore_script(book_dir, text, phase=PHASE, label=label, book_title=book_title, log=log)


# ── timings ──────────────────────────────────────────────────────────────────


def cue_map(markdown: str, cues) -> tuple[list[dict], float]:
    """Pair each rendered paragraph with the seconds of audio it came from.

    The alignment runs cues -> paragraphs, and the direction is the whole point.
    A paragraph is many cues long, so asking "which paragraph is this cue from"
    is a many-to-one question, which is what `_align_paragraphs` answers. Asked
    the other way it would force several paragraphs onto one cue and hand back
    timings that march backwards.

    Returns the cue list and the share of transcript cues placed with real
    evidence of their own — the caller's grounds for publishing them or not.
    """
    blocks = chapter_blocks(markdown)
    said = [c for c in cues if c.text.strip()]
    if not blocks or not said:
        return [], 0.0

    alignments = align([text for _, text in blocks], [c.text for c in said])
    if not alignments or not is_monotonic(alignments):
        return [], 0.0

    spans: dict[int, list] = {}
    for alignment, cue in zip(alignments, said):
        spans.setdefault(alignment.source_index, []).append(cue)

    out: list[dict] = []
    for idx, (block_index, text) in enumerate(blocks):
        window = spans.get(idx)
        if not window:
            # A paragraph no cue landed on cannot be timed, and guessing a span
            # for it from its neighbours would light it up during someone else's
            # sentence. The whole chapter is judged below; this one is skipped.
            continue
        out.append(
            {
                "idx": len(out),
                "blockIndex": block_index,
                "startS": round(min(c.offset_ms for c in window) / 1000, 3),
                "endS": round(max(c.end_ms for c in window) / 1000, 3),
                "text": text,
            }
        )

    confident = sum(1 for a in alignments if a.score >= SELF_SUPPORT)
    placed = len(out) / len(blocks)
    return out, min(confident / len(alignments), placed)


# ── the pass ─────────────────────────────────────────────────────────────────


def _manifest_path(book_dir: Path) -> Path:
    return book_dir / "book" / "narration" / "manifest.json"


def read_manifest(book_dir: Path) -> dict:
    path = _manifest_path(book_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_manifest(book_dir: Path, manifest: dict) -> None:
    path = _manifest_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_along_book(
    book_dir: Path,
    *,
    force: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    log=print,
) -> dict:
    """Correct, script and time every chapter that came off a recording."""
    book_dir = Path(book_dir).resolve()
    chapters = spoken_chapters(book_dir)
    if not chapters:
        return {"outcome": "skipped", "reason": "no chapters were taken from a recording"}

    manifest = read_manifest(book_dir)
    manifest.setdefault("chapters", {})
    manifest.update({"schema": MANIFEST_SCHEMA, "engine": "author-recording", "voice": "author"})

    outstanding = [
        (key, entry)
        for key, entry in chapters.items()
        if force or manifest["chapters"].get(key, {}).get("source_hash") != fingerprint(entry.get("base") or "")
    ]
    # Counted BEFORE the limit is applied. Reporting the remainder as "already
    # done" is how a `--limit 1` run said four chapters were finished that had
    # never been read.
    done_already = len(chapters) - len(outstanding)
    todo = outstanding[:limit] if limit is not None else outstanding

    log(
        f"  read-along: {book_dir.name} — {len(todo)} chapter(s) to do, "
        f"{done_already} already done, {len(outstanding) - len(todo)} deferred by --limit"
    )
    if dry_run:
        for key, entry in todo:
            log(f"    would correct and time: {entry['title']}")
        return {"outcome": "dry-run", "planned": len(todo)}

    done: list[str] = []
    untimed: list[str] = []
    warnings: list[str] = []
    resolutions: list = []

    for index, (key, entry) in enumerate(todo, start=1):
        title = entry["title"]
        episode = int(entry["episode"])
        base = entry.get("base") or ""
        log(f"  [{index}/{len(todo)}] {title} (recording {episode})")

        text, notes = correct(book_dir, base, label=key, log=log)
        warnings.extend(notes)
        text, found = restore_script(book_dir, text, label=key, book_title=book_dir.name, log=log)
        resolutions.extend(found)
        # Reported by RUNG, not as a bare total. "0 left as spoken" was true by
        # construction — the ladder's last rung always returns something — so it
        # measured nothing, while the number worth watching is how many runs
        # stand on a source rather than on a rendering of their own spelling.
        log(
            f"      Arabic: {sum(1 for r in found if r.provenance == 'library')} from the library, "
            f"{sum(1 for r in found if r.provenance == 'reconstructed')} reconstructed, "
            f"{sum(1 for r in found if not r.ok)} left as spoken"
        )

        # Writes book.md AND records the Composer edit, which is what makes the
        # corrected chapter survive the next ingest — the same guarantee, through
        # the same call, that a chapter Asif types by hand gets.
        write_chapter_body(book_dir, title, text)

        vtt = book_dir / "transcripts" / f"ep{episode:02d}.vtt"
        cues, confidence = ([], 0.0)
        if vtt.exists():
            cues, confidence = cue_map(text, from_vtt(vtt.read_text(encoding="utf-8")))

        audio = book_dir / "m4a" / "Episodes" / f"ep{episode:02d}.mp3"
        if not audio.exists():
            untimed.append(f"{title}: recording ep{episode:02d}.mp3 is not on disk")
            continue
        if confidence < _CUE_CONFIDENCE:
            # Published WITHOUT cues rather than not published: the reader still
            # gets the lecture to listen to while reading, and nothing is
            # highlighted in the wrong place.
            untimed.append(f"{title}: paragraphs could not be timed confidently ({confidence:.0%})")
            cues = []

        manifest["chapters"][key] = {
            "title": title,
            "episode": episode,
            "audio": f"m4a/Episodes/{audio.name}",
            "audio_key": f"{book_dir.name}/audio/ep{episode:02d}.mp3",
            # The RECORDING's length, not the last cue's end. They coincide when
            # the alignment reached the final paragraph and diverge exactly when
            # it did not — so taking it from the cues would report a chapter as
            # shorter than the audio the player is about to stream, and would
            # report nothing at all for a chapter published without cues.
            "duration_s": round(audio_duration_seconds(audio), 3),
            "source_hash": fingerprint(base),
            "voice": "author",
            "confidence": round(confidence, 3),
            "cues": cues,
        }
        write_manifest(book_dir, manifest)
        done.append(title)

    write_manifest(book_dir, manifest)
    if resolutions:
        from _book_romanization import write_record

        write_record(book_dir, resolutions)

    return {
        "outcome": "completed",
        "chapters": done,
        "untimed": untimed,
        "warnings": warnings,
        "arabic_from_library": sum(1 for r in resolutions if r.provenance == "library"),
        "arabic_reconstructed": sum(1 for r in resolutions if r.provenance == "reconstructed"),
        "arabic_left_spoken": sum(1 for r in resolutions if not r.ok),
        "at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", choices=sorted(SERIES))
    parser.add_argument("--force", action="store_true", help="redo chapters already corrected")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    book_dir = resolve_content(args.slug)
    if not (book_dir / "book" / "book.md").exists():
        print(f"no ingested book at {book_dir} — run the ingest first", file=sys.stderr)
        return 2

    state_path = book_dir / "_system" / "orchestrator-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"could not read orchestrator-state.json: {exc}", file=sys.stderr)
        return 2
    art_status = ((state.get("phases") or {}).get(ARTICULATE_STEP) or {}).get("status")
    if art_status != "completed":
        print(
            f"read-along: refusing — sessions-articulate is {art_status!r}, not completed. "
            "Run articulate.py to the end first.",
            file=sys.stderr,
        )
        return 1

    report = read_along_book(book_dir, force=args.force, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.dry_run:
        return 0

    _write_state(book_dir, SERIES[args.slug], done_through=READ_ALONG_STEP)
    print(f"read-along: orchestrator-state.json now reports through {READ_ALONG_STEP!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
