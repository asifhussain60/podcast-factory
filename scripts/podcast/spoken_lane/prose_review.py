"""Is a spoken book's prose fit for a person to read yet? Report, don't rewrite.

Asif, 2026-09-01, after opening the first audiobook in the Book Composer:
"I should not be told to view the Book, session, audiobook in Compose … until
the chapters have been cleaned and cleared through this review and fix step."

So Composer-readiness stops being something anyone ASSERTS and becomes something
this module COMPUTES. `is_composer_ready` is the one answer, and it is derived
from the prose on disk.

BLOCKING vs ADVISORY, and the distinction is the whole design.

  BLOCKING   a defect the cleanup can fix on its own. Its presence means
             `normalize_sessions_prose` has not run over this book, so the book
             is not ready and nobody should be sent to look at it. Fixing it
             needs no judgement, which is exactly why leaving it is inexcusable.

  ADVISORY   a defect only a person can settle. It is reported every time and
             blocks nothing, because a gate that waits on human judgement is a
             gate that never opens and a book that never ships.

Everything here REPORTS. Nothing in this file edits prose — `_sessions_prose_format`
is where repair lives, and keeping the two apart is what lets this run at any
time, on any book, with no risk attached to running it.

WHY THE AMBIGUOUS CASES ARE ADVISORY, concretely. Both were candidates for
auto-repair and both were rejected after measuring them against books already on
disk:

  * A run of capitals looks like a heading the narrator read aloud, and in White
    Nights it is one. In `surah-al-fateha` it is `AM YOUR KING` and `BOW DOWN
    BEFORE ME` — emphatic speech inside a quotation. Promoting those would put a
    divine utterance in a section heading.

  * A space before a comma looks like loose typing. In these books it is the
    residue of a MISSING ARABIC TERM — "The word  , which is also used in Urdu".
    Closing it would not fix the defect, it would conceal it.

    python3 -m spoken_lane.prose_review <slug>
    python3 -m spoken_lane.prose_review --all
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _sessions_prose_format import CAPS_RUN, SPACE_BEFORE_COMMA  # noqa: E402

#: Codes whose presence means the cleanup has not run. See the module docstring.
BLOCKING = frozenset({"ECHOED_HEADING", "SPACING"})

#: Words that mark a chapter as the publisher's front matter rather than the
#: author's text — "This is White Nights … translated by Tim Zengerink, narrated
#: by Zeke Ring." Advisory: whether that belongs in a reading edition is Asif's
#: call, not a rule's, and the names in it are provenance worth keeping somewhere.
_FRONT_MATTER = re.compile(r"\b(narrated by|translated by|all rights reserved|is a production of)\b", re.I)

_SENTENCE_START = re.compile(r"^[\"'(\[A-Z0-9]")


@dataclass(frozen=True)
class Finding:
    chapter: str
    code: str
    detail: str

    @property
    def blocking(self) -> bool:
        return self.code in BLOCKING

    def __str__(self) -> str:
        return f"{'BLOCK' if self.blocking else 'note '}  {self.chapter[:26]:26s}  {self.code:18s}  {self.detail}"


def _chapters(book_md: Path) -> list[tuple[str, str]]:
    """(heading, body) for each `## ` section."""
    if not book_md.exists():
        return []
    text = book_md.read_text(encoding="utf-8")
    out = []
    for section in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = section.partition("\n")
        out.append((head.strip(), body.strip()))
    return out


def review_book(book_dir: Path) -> list[Finding]:
    """Every prose finding in this book's composed edition."""
    findings: list[Finding] = []
    for heading, body in _chapters(Path(book_dir) / "book" / "book.md"):
        if not body:
            continue

        # BLOCKING — the cleanup fixes these unaided.
        if heading and re.match(rf"^{re.escape(heading)}\s*[.,:;!?—-]*\s+", body, re.IGNORECASE):
            findings.append(Finding(heading, "ECHOED_HEADING", f"body opens by repeating {heading!r}"))
        for pattern, label in ((re.compile(r"[A-Za-z0-9] -[A-Za-z0-9]"), "orphaned hyphen"),):
            n = len(pattern.findall(body))
            if n:
                findings.append(Finding(heading, "SPACING", f"{n}x {label}"))

        # ADVISORY — a person decides.
        for m in CAPS_RUN.finditer(body):
            findings.append(Finding(heading, "SPOKEN_HEADING", f"capitals mid-prose: {m.group(0)[:60]!r}"))
        n_comma = len(SPACE_BEFORE_COMMA.findall(body))
        if n_comma:
            findings.append(
                Finding(heading, "GAP_BEFORE_COMMA", f"{n_comma}x — often a dropped term, not loose spacing")
            )
        if _FRONT_MATTER.search(body[:400]):
            findings.append(Finding(heading, "FRONT_MATTER", "reads as publisher credits, not the author's text"))

        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        mid = [p for p in paras if not _SENTENCE_START.match(p)]
        if paras and len(mid) / len(paras) > 0.25:
            findings.append(
                Finding(
                    heading,
                    "MID_SENTENCE_BREAKS",
                    f"{len(mid)}/{len(paras)} paragraphs start mid-sentence — sessions-articulate has not run",
                )
            )
    return findings


def is_composer_ready(book_dir: Path) -> bool:
    """Should a person be sent to the Book Composer for this book yet?

    False while any BLOCKING finding stands. Advisory findings never hold a book
    back: they need a person, and the Composer is where that person works.
    """
    book_dir = Path(book_dir)
    if not (book_dir / "book" / "book.md").exists():
        return False
    return not [f for f in review_book(book_dir) if f.blocking]


def main(argv: list[str] | None = None) -> int:
    import _paths

    from spoken_lane.transcript_check import _is_spoken_lane

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--all", action="store_true", help="every spoken-lane book")
    args = parser.parse_args(argv)

    if args.all:
        books = [b for b in (Path(d) for *_r, d in _paths.iter_content()) if _is_spoken_lane(b)]
    elif args.slug:
        found = _paths.find_content(args.slug)
        if not found:
            print(f"no book found for slug {args.slug!r}", file=sys.stderr)
            return 2
        books = [Path(found[-1])]
    else:
        parser.error("give a slug or --all")

    blocking = 0
    for book in sorted(books):
        findings = review_book(book)
        if not (book / "book" / "book.md").exists():
            continue
        blocks = [f for f in findings if f.blocking]
        blocking += len(blocks)
        ready = "COMPOSER-READY" if not blocks else "NOT READY"
        print(f"\n{ready}  {book.name}  ({len(blocks)} blocking, {len(findings) - len(blocks)} advisory)")
        for f in findings:
            print(f"   {f}")
    print(f"\n{blocking} blocking finding(s). A book with any is not ready to be reviewed by hand.")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
