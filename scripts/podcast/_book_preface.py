"""Does this book OPEN properly — and if not, what is wrong with how it opens?

`_book_frontmatter` writes the introduction. This asks whether one is there and
whether it is doing its job, which is a different question and is asked at a
different time: by `compose_fix.py`, over a book already on disk, on Asif's
behalf, without re-running anything.

WHY IT IS A SEPARATE CHECK FROM THE GATE THAT WRITES ONE

`gate_introduction` judges a model's ANSWER before it is injected — is it under
the cap, is it prose, did it return a heading it was told not to. This judges a
BOOK, and the failure it exists to catch is one that gate cannot see: an
introduction that was never asked for at all, because the route that built the
book had no front-matter step. The Sessions lane shipped exactly that. Its first
chapter was the speaker's own spoken opening — who he is, why he runs these
sessions, greetings to the elders in the room, asking his teacher's permission to
begin — and a reader met all of it before being told a single thing about what
was in the book.

That opening is real and was rightly said aloud. It is simply not a preface. A
preface is written to the READER: what this is, what is in it, how to come at it.

WHAT "SPOKEN OPENING" LOOKS LIKE, AND WHY THE TEST IS DELIBERATELY BLUNT

The markers below are the ones that actually appear at the top of a delivered
lecture, and every one of them is about the OCCASION rather than the book: a
greeting to a room, a self-introduction, a request for permission to start, a
promise about what "today's session" will do. Two or more of them in an opening
section is the signal.

It is a report, never a repair. Deciding that a chapter of a religious text is
apparatus rather than teaching is a judgement, and the cure — replacing it with
an authored preface — is offered under a flag a person presses, exactly as every
other judgement-shaped repair in `compose_fix` is.
"""

from __future__ import annotations

import re
from pathlib import Path

# The introduction's heading, as `_book_frontmatter` prints it. Imported rather
# than re-typed would be better, and it is: see `_heading` below. This module
# keeps its own compiled form only.
_SECTION_RE = re.compile(r"(?m)^##[ \t]+(?!#)(.+?)[ \t]*$")

# The room, not the reader. Each phrase is one an opening actually carries.
_SPOKEN_MARKERS = (
    "salaam alaykum",
    "assalaam",
    "assalamu",
    "salaam alaikum",
    "thank you for taking the time",
    "thank you for joining",
    "for those of you who don't know me",
    "for those of you who do not know me",
    "let me introduce myself",
    "i'd like to take a moment to introduce",
    "i would like to introduce myself",
    "in today's session",
    "in this session, i",
    "let's get started",
    "let us begin",
    "may i begin",
    "with your permission",
    "joined the group",
    "in this group",
    "my name is",
)

# Under this, an "introduction" is a stub rather than a preface — a heading
# somebody left behind. Deliberately far below `MIN_INTRO_WORDS`, because this
# reports on books nobody has run the front-matter step over and a borderline
# short preface is not the failure worth interrupting for.
_MIN_USEFUL_WORDS = 40


def _heading() -> str:
    from _book_frontmatter import INTRO_HEADING

    return INTRO_HEADING[3:].strip().lower()


def sections(book_md: str) -> list[tuple[str, str]]:
    """Every `##` section as (title, body), in the order the book prints them."""
    parts = _SECTION_RE.split(book_md)
    out: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), (parts[i + 1] if i + 1 < len(parts) else "").strip()))
    return out


def spoken_opening_markers(text: str) -> list[str]:
    """Which occasion-markers this text carries. Two or more is the signal."""
    lowered = text.lower()
    return [m for m in _SPOKEN_MARKERS if m in lowered]


def preface_findings(book_md: str) -> list[tuple[str, str]]:
    """What is wrong with how this book opens, as (code, human sentence).

    Empty means the book opens with a preface addressed to the reader. Every
    finding names a cure a person can choose; nothing here changes anything.
    """
    found = sections(book_md)
    if not found:
        return [("no-sections", "the book has no `##` sections at all — nothing to open with")]

    wanted = _heading()
    title, body = found[0]
    words = len(body.split())

    if title.lower() == wanted:
        if words < _MIN_USEFUL_WORDS:
            return [
                (
                    "empty-preface",
                    f"the book opens with '{title}' but it holds only {words} words — "
                    "a heading with nothing under it, not a preface",
                )
            ]
        return []

    markers = spoken_opening_markers(body[:4000])
    if len(markers) >= 2:
        return [
            (
                "spoken-opening",
                f"the book opens with '{title}', which reads as the speaker opening the "
                f"occasion rather than a preface for the reader (it greets the room, "
                f"introduces the speaker, or asks leave to begin: {', '.join(markers[:3])}). "
                "A reader learns nothing here about what is in the book.",
            )
        ]

    return [
        (
            "missing-preface",
            f"the book opens straight into '{title}' with no introduction before it — "
            "nothing tells the reader what this is or what is in it",
        )
    ]


def preface_check(book_dir: Path) -> list[tuple[str, str]]:
    """How this book OPENS — a book-level question, so it hangs off the report root.

    Every other check here is scoped to the chapters somebody selected. This one
    cannot be: "is there a preface" is not a property of chapter 3, and a run
    that checked chapters 3-5 and stayed silent about a book with no opening at
    all would be reporting on the wrong thing.
    """
    book_md = book_dir / "book" / "book.md"
    return preface_findings(book_md.read_text(encoding="utf-8")) if book_md.is_file() else []


def write_preface(book_dir: Path, *, force: bool = False, log=print) -> dict:
    """Give the book the opening it is missing, from its own chapters.

    Asif's rule, 2026-08-11: if a preface cannot be built from the original
    source, review the content and build one. This is the second half — and the
    first half is why it needs no separate code path. `apply_introduction` reads
    facts only from files, and the chapter list is now taken from `book.md`'s own
    headings when there is no compose TOC, so a book with no source front matter
    is written up from what it actually contains.

    Idempotent and cached: asked of a model once per book, ever, unless `force`.
    And a preface Asif has edited in the Composer always wins — that check is
    inside `apply_introduction`, where every caller gets it.
    """
    from _book_frontmatter import apply_introduction

    return apply_introduction(book_dir, log=log, force=force)


def print_preface_findings(report: dict) -> None:
    """Say how the book opens, in the words this module owns.

    Same arrangement as `_quote_cards.print_quote_card_findings`: the module that
    decides what a defect IS also decides how it reads on screen, so the rule and
    the sentence describing it cannot drift apart in separate files.
    """
    for code, sentence in report.get("preface") or []:
        print(f"\n  how the book opens — {code}\n      {sentence}")
        print("      --preface writes one from the book's own chapters (asks a model, once)")
