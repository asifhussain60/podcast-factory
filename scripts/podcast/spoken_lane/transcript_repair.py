"""Repair what an exporter mangled on the way out, before anything reads it.

Asif, 2026-09-01: "so was the issue in the transcription? If so, then this
should be the first fix step right?"

Partly, and this module is the part that was. White Nights' fifth chapter came
back from TurboScribe with 138 U+FFFD replacement characters where its own curly
quotes and apostrophes should have been — `don�t`, `said, �Nastenka`. Nothing
errored; it composed straight into `book.md`.

`transcript_check` was written the same day and DETECTS that. It does not fix it,
so the first mangled export would have blocked its book at `sessions-ingest` and
waited for somebody to repair the file by hand — which is exactly what happened
to ep05, with a throwaway script that was never part of anything. A check without
a repair moves the manual step, it does not remove it.

WHY U+FFFD IS SAFE TO REPAIR AT ALL. It is not a character anyone types. It is
the mark left where a byte failed to decode, so its presence is unambiguous
evidence of damage — unlike every other artifact in this lane, where the hard
part is deciding whether there is a defect at all. Here the only question is
which character was lost, and the surrounding text answers it.

CLASSIFIED BY CONTEXT, and refused when context does not answer:

    don�t              letter on both sides          -> apostrophe
    said, �Nastenka    boundary before, letter after -> opening double quote
    a bench.�  Over    letter before, boundary after -> closing double quote
    anything else      unclassifiable                -> LEFT IN PLACE

The last row is the important one. A replacement character this cannot explain
stays exactly where it is, so `transcript_check` still reports CORRUPTION and the
book still refuses to advance. Guessing there would trade a loud failure for a
silent wrong character in a book.

Measured against the real damage: 110 quotes and 28 apostrophes, none left
unclassified.

    python3 -m spoken_lane.transcript_repair <slug>            # dry run
    python3 -m spoken_lane.transcript_repair <slug> --apply
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spoken_lane.transcript_check import REPLACEMENT_CHAR  # noqa: E402

#: What sits either side of a lost character, and what that implies it was.
_APOSTROPHE = "'"
_DOUBLE_QUOTE = '"'

#: Characters that end a run of text — a boundary, as opposed to a letter.
_BOUNDARY = " \t\n\r"


@dataclass(frozen=True)
class Repair:
    episode: int
    apostrophes: int
    quotes: int
    unresolved: int

    @property
    def fixed(self) -> int:
        return self.apostrophes + self.quotes

    def __str__(self) -> str:
        tail = f", {self.unresolved} LEFT UNRESOLVED" if self.unresolved else ""
        return f"ep{self.episode:02d}  {self.fixed} repaired ({self.apostrophes} apostrophe, {self.quotes} quote){tail}"


def repair_text(text: str) -> tuple[str, int, int, int]:
    """Return (repaired, apostrophes, quotes, unresolved)."""
    if REPLACEMENT_CHAR not in text:
        return text, 0, 0, 0

    out: list[str] = []
    apostrophes = quotes = unresolved = 0
    for i, ch in enumerate(text):
        if ch != REPLACEMENT_CHAR:
            out.append(ch)
            continue
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if prev.isalpha() and nxt.isalpha():
            # A contraction: don't, wasn't, I'm.
            out.append(_APOSTROPHE)
            apostrophes += 1
        elif (not prev or prev in _BOUNDARY or not prev.isalnum()) and (nxt.isalpha() or nxt == _BOUNDARY[0]):
            # Speech opening: `said, "Nastenka`.
            out.append(_DOUBLE_QUOTE)
            quotes += 1
        elif prev and (prev.isalnum() or prev in ".,;:!?") and (not nxt or nxt in _BOUNDARY):
            # Speech closing: `a bench." Over`.
            out.append(_DOUBLE_QUOTE)
            quotes += 1
        else:
            # Context does not say. Leave the damage visible so the check keeps
            # refusing the book, rather than putting a guessed character in it.
            out.append(ch)
            unresolved += 1
    return "".join(out), apostrophes, quotes, unresolved


def repair_book(book_dir: Path, *, apply: bool = False) -> list[Repair]:
    """Repair every transcript in a book. Idempotent; a clean file is untouched."""
    book_dir = Path(book_dir)
    out: list[Repair] = []
    for vtt in sorted((book_dir / "transcripts").glob("ep*.vtt")):
        if not vtt.stem[2:].isdigit():
            continue
        try:
            text = vtt.read_text(encoding="utf-8")
        except OSError:
            continue
        repaired, apo, quo, unres = repair_text(text)
        if not (apo or quo or unres):
            continue
        if apply and repaired != text:
            vtt.write_text(repaired, encoding="utf-8")
        out.append(Repair(int(vtt.stem[2:]), apo, quo, unres))
    return out


def main(argv: list[str] | None = None) -> int:
    import _paths

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--apply", action="store_true", help="write. Default is a dry run.")
    args = parser.parse_args(argv)

    found = _paths.find_content(args.slug)
    if not found:
        print(f"no book found for slug {args.slug!r}", file=sys.stderr)
        return 2

    repairs = repair_book(Path(found[-1]), apply=args.apply)
    if not repairs:
        print("nothing to repair — no replacement characters in any transcript")
        return 0
    print("APPLY" if args.apply else "DRY RUN — nothing written (pass --apply)")
    for r in repairs:
        print(f"  {r}")
    unresolved = sum(r.unresolved for r in repairs)
    print(f"\n{sum(r.fixed for r in repairs)} repaired, {unresolved} left unresolved.")
    if unresolved:
        print("Unresolved damage stays in the file so transcript_check keeps refusing the book.")
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
