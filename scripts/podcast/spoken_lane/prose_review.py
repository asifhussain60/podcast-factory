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

from _arabic_coverage import ARABIC_BODY  # noqa: E402
from _sessions_prose_format import CAPS_RUN, SPACE_BEFORE_COMMA, _is_markdown_structure  # noqa: E402

#: Codes whose presence means the cleanup has not run. See the module docstring.
#:
#: `MID_SENTENCE_BREAKS` joined them on 2026-09-01. It was advisory while the
#: grouping rule manufactured the defect — 46% of White Nights' paragraphs began
#: mid-sentence, and blocking on a self-inflicted wound would have blocked every
#: book forever. `group_into_paragraphs` now breaks at sentence ends and that
#: figure is 0, so a book still showing them has a transcript with no terminal
#: punctuation to break on. That is a real defect, and a person should see the
#: book only after somebody has looked at it.
BLOCKING = frozenset({"ECHOED_HEADING", "SPACING", "MID_SENTENCE_BREAKS"})

#: Words that mark a chapter as the publisher's front matter rather than the
#: author's text — "This is White Nights … translated by Tim Zengerink, narrated
#: by Zeke Ring." Advisory: whether that belongs in a reading edition is Asif's
#: call, not a rule's, and the names in it are provenance worth keeping somewhere.
_FRONT_MATTER = re.compile(r"\b(narrated by|translated by|all rights reserved|is a production of)\b", re.I)

_SENTENCE_START = re.compile(r"^[\"'(\[A-Z0-9]")

#: What a chapter body says when its recording has not been transcribed yet.
#: Written by `spoken_lane/audiobook.py` so the book still composes and its
#: structure is visible. It is NOT prose and must not be reviewed as prose --
#: the first version scored it and reported 20 blocking findings on The Idiot,
#: a book whose only actual problem is that nobody has transcribed it. A review
#: that fails a book for not having started is noise, and noise is what stops
#: anyone reading the findings that matter.
_PLACEHOLDER = "_Awaiting transcript._"

#: A paragraph that is not PROSE, and so has no sentence to start.
#:
#: The mid-sentence check read every block as prose, and on `surah-al-fateha` --
#: a published book -- that reported 49 of 125 paragraphs broken in one chapter
#: and held the whole book NOT READY. Forty-three of the forty-nine were a
#: Qur'anic blockquote, a heading, or a list item; three more opened in Arabic,
#: which is RTL and has no capital letter to find. The book was fine and the
#: check was measuring markdown.
#:
#: `_is_markdown_structure` already answers the first half and is imported
#: rather than restated -- it is the same question `_sessions_prose_format` asks
#: before it touches a line.
_ARABIC_START = re.compile(f"^[{ARABIC_BODY}]")


def _is_prose(paragraph: str) -> bool:
    """True when a paragraph is running text that should begin like a sentence."""
    text = paragraph.strip()
    return bool(text) and not _is_markdown_structure(text) and not _ARABIC_START.match(text)


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
        if not body or body.strip() == _PLACEHOLDER:
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
        prose = [p for p in paras if _is_prose(p)]
        mid = [p for p in prose if not _SENTENCE_START.match(p)]
        if prose and len(mid) / len(prose) > 0.25:
            findings.append(
                Finding(
                    heading,
                    "MID_SENTENCE_BREAKS",
                    f"{len(mid)}/{len(prose)} prose paragraphs start mid-sentence — the transcript may carry "
                    "no sentence punctuation to break on",
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

    # A book whose chapters are all placeholders is not ready, it is UNSTARTED,
    # and the difference matters more than it looks. Skipping placeholder
    # chapters in `review_book` (correctly, since they are not prose) made The
    # Idiot report zero findings and therefore READY -- a book with no
    # transcripts at all, about which the honest answer is "there is nothing
    # here yet". Reporting nothing wrong is not the same as being right, and an
    # empty book passing a readiness gate is the worst failure this gate has:
    # it sends someone to read a file of placeholders.
    chapters = _chapters(book_dir / "book" / "book.md")
    if not chapters or all(b.strip() == _PLACEHOLDER or not b.strip() for _h, b in chapters):
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
