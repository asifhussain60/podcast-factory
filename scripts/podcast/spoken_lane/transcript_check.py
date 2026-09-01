"""Is a spoken book's transcript actually usable? Deterministic, no model spend.

WHY THIS EXISTS. A transcript arrives from outside the pipeline — TurboScribe,
Azure, whatever transcribed the recording — and every failure it can carry is
SILENT. Nothing downstream raises: the chapter simply reads wrong, or reads
short, or highlights nothing, and the first person to notice is a reader.

Asif, 2026-09-01, looking at the first audiobook: "Make sure there are no funny
characters used in the book… add these checks to the pipeline and harness with
tests so this does not happen again."

The five failures below are each one that HAS happened or was one keystroke away:

  CORRUPTION      White Nights' fifth chapter came back with 138 U+FFFD
                  replacement characters where the exporter mangled its curly
                  quotes and apostrophes — `don�t`, `said, �Nastenka`. Nothing
                  errored. It composed into `book.md` and sat there.

  UNPARSEABLE     SRT and VTT differ by one character in the timestamp — a comma
                  where a period belongs — so an SRT file saved as `.vtt` parses
                  to ZERO cues. The chapter then publishes with audio playing and
                  nothing highlighting, and no error anywhere says why.

  MISPAIRED       A transcript whose cues run minutes past (or short of) the
                  recording is a transcript of a DIFFERENT chapter. Read-along
                  would highlight confidently and wrongly, which `read_along.py`
                  states is worse than highlighting nothing.

  MISSING         A book with eight recordings and seven transcripts is not
                  ready, and the gap is invisible in a folder listing.

  EMPTY           A file that parses but carries no words is a failed export
                  that looks like a success.

WHAT IS NOT AN ERROR, deliberately. Em dashes, and letters like the é in
"cliché" and the ç in "façade", are correct English typography and correct
spelling; a check that flagged them would train its reader to ignore it. Only
U+FFFD is unambiguous — it is not a character anyone types, it is the mark left
where a byte failed to decode.

    python3 -m spoken_lane.transcript_check <slug>     # one book
    python3 -m spoken_lane.transcript_check --all      # every spoken book
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

#: The mark left where a byte failed to decode. Never typed on purpose.
REPLACEMENT_CHAR = "\ufffd"

#: Both extensions are real spoken-lane recordings and the first version of this
#: file looked only for `.m4a`. Sessions books hold `.mp3`, so every one of their
#: transcripts was reported ORPHAN -- 339 findings, almost all of them this bug.
#: A checker that cries wolf is worse than none, because its next real finding is
#: the one nobody reads.
AUDIO_EXT = (".m4a", ".mp3")

#: How far a transcript's last cue may sit from the end of its recording. Wide
#: on purpose: a narrator's closing silence is real, and the failure this catches
#: is a transcript of the WRONG chapter, which is minutes out, not seconds. The
#: eight White Nights files land within 0.6s, so this has ~50x of headroom before
#: it would fire on a correct pairing.
DRIFT_TOLERANCE_MS = 30_000


@dataclass(frozen=True)
class Finding:
    episode: int | None
    code: str
    detail: str

    def __str__(self) -> str:
        where = f"ep{self.episode:02d}" if self.episode else "book"
        return f"{where}  {self.code}  {self.detail}"


def _audio_lengths(book_dir: Path) -> dict[int, int]:
    """episode -> recorded length in ms, from the chapter index the split wrote."""
    import json

    path = book_dir / "_system" / "audiobook-chapters.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        int(c["episode"]): int(c["length_ms"])
        for c in data.get("chapters", [])
        if isinstance(c, dict) and "episode" in c and "length_ms" in c
    }


def episode_numbers(book_dir: Path) -> list[int]:
    """The episode numbers this book has recordings for, in either extension.

    Only the FLAT `ep01.m4a` / `ep01.mp3` shape, which is the spoken lane's: one
    recording per chapter, numbered to match its transcript. A podcast book's
    `m4a/Episodes/Session 2 - Title/EP-01-....m4a` is a different layout for a
    different thing and is deliberately not read here.
    """
    out = []
    for f in (Path(book_dir) / "m4a" / "Episodes").glob("ep*"):
        if f.suffix.lower() in AUDIO_EXT and f.stem[2:].isdigit():
            out.append(int(f.stem[2:]))
    return sorted(set(out))


def check_book(book_dir: Path) -> list[Finding]:
    """Every problem this book's transcripts carry. Empty list means usable.

    Reports EVERY finding rather than stopping at the first: a caller fixing
    transcripts wants the whole list, and a gate wants to say how much is wrong.
    """
    from _transcript import from_vtt

    book_dir = Path(book_dir)
    out: list[Finding] = []
    episodes = sorted(episode_numbers(book_dir))
    lengths = _audio_lengths(book_dir)

    for n in episodes:
        vtt = book_dir / "transcripts" / f"ep{n:02d}.vtt"
        if not vtt.exists():
            out.append(Finding(n, "MISSING", "recording has no transcript"))
            continue
        try:
            text = vtt.read_text(encoding="utf-8")
        except OSError as e:
            out.append(Finding(n, "UNREADABLE", str(e)))
            continue

        bad = text.count(REPLACEMENT_CHAR)
        if bad:
            out.append(
                Finding(n, "CORRUPTION", f"{bad} replacement character(s) — the exporter mangled quotes or accents")
            )

        cues = from_vtt(text)
        if not cues:
            out.append(
                Finding(n, "UNPARSEABLE", "no cues — an SRT saved as .vtt parses to zero (comma vs period in stamps)")
            )
            continue

        words = sum(len(c.text.split()) for c in cues)
        if not words:
            out.append(Finding(n, "EMPTY", "cues carry no words"))

        recorded = lengths.get(n)
        if recorded:
            drift = abs(cues[-1].end_ms - recorded)
            if drift > DRIFT_TOLERANCE_MS:
                out.append(
                    Finding(
                        n,
                        "MISPAIRED",
                        f"last cue is {drift / 1000:.0f}s from the end of a {recorded / 60000:.0f}min "
                        "recording — likely a transcript of a different chapter",
                    )
                )

    # A transcript with no recording behind it: the reverse gap, equally silent.
    for vtt in sorted((book_dir / "transcripts").glob("ep*.vtt")):
        if vtt.stem[2:].isdigit() and int(vtt.stem[2:]) not in episodes:
            out.append(Finding(int(vtt.stem[2:]), "ORPHAN", "transcript has no recording"))

    return out


def is_complete(book_dir: Path) -> bool:
    """True when every recording has a usable transcript beside it.

    This is what the scaffolder asks before it records `sessions-transcribe` as
    done. "Present" was the old answer and it is not good enough: a file full of
    replacement characters is present, and a book that claims the step on that
    basis hands corrupted prose to every phase after it.
    """
    book_dir = Path(book_dir)
    episodes = list((book_dir / "m4a" / "Episodes").glob("ep*.m4a"))
    if not episodes:
        return False
    return not check_book(book_dir)


def _is_spoken_lane(book_dir: Path) -> bool:
    """Does this book's own state file put it on the spoken lane?"""
    import json

    path = Path(book_dir) / "_system" / "orchestrator-state.json"
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("pipeline_mode") == "sessions_lane"
    except (OSError, ValueError):
        return False


def main(argv: list[str] | None = None) -> int:
    import _paths

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", nargs="?", help="one book; omit with --all")
    parser.add_argument("--all", action="store_true", help="every book that has a transcripts/ folder")
    args = parser.parse_args(argv)

    if args.all:
        # SPOKEN-LANE BOOKS ONLY. Scoping this to "every book with a transcripts/
        # folder" was the first version and it was wrong: a podcast book's
        # transcripts are of NotebookLM's GENERATED episodes, which answer to no
        # part of this contract, and sweeping them in buried the real findings.
        books = [b for b in (Path(d) for *_r, d in _paths.iter_content()) if _is_spoken_lane(b)]
    elif args.slug:
        found = _paths.find_content(args.slug)
        if not found:
            print(f"no book found for slug {args.slug!r}", file=sys.stderr)
            return 2
        books = [Path(found[-1])]
    else:
        parser.error("give a slug or --all")

    total = 0
    for book in sorted(books):
        findings = check_book(book)
        total += len(findings)
        mark = "ok  " if not findings else "FAIL"
        print(f"{mark}  {book.name}  ({len(findings)} finding(s))")
        for f in findings:
            print(f"        {f}")
    print(f"\n{total} finding(s) across {len(books)} book(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
