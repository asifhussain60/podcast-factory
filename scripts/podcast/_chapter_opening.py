#!/usr/bin/env python3
"""_chapter_opening.py — a chapter begins with a capital letter.

Asif, 2026-08-31, looking at "Love of the World" in the Library: "Chapter start
should NEVER be lower case. ALWAYS begin with capital."

WHY IT HAPPENS. Nothing in the pipeline ever asserted this. A chapter's opening
words are whatever the source handed over, and for a Sessions book the source is
a person speaking: Asif began that sitting mid-thought ("and know that the love
of the world..."), the transcription recorded exactly that, and the verbatim lane
is under orders not to rewrite him. So the lowercase survived every pass — not
because a pass got it wrong, but because no pass was looking.

WHY IT IS SAFE TO FIX HERE. The verbatim contract for spoken chapters
(`_verbatim_correct.py`) already places "punctuation and capitalisation" inside
the licence to correct — they are artifacts of transcription, not of speech. A
capital letter changes no word, so the prose stays the speaker's.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It capitalizes ONE letter: the first of a chapter's first paragraph. It is not a
sentence-case pass and never touches the body, because a rule that rewrote every
sentence would be rewriting the book on a typographic pretext.

It also never invents a sentence. A chapter that opens on a FRAGMENT — text lost
at the chapter boundary, which is a content defect that a capital letter would
disguise rather than repair — is capitalized like any other AND reported by
`fragment_openings()`, so the underlying loss stays visible to a human. Silently
turning "telling, and short of it." into "Telling, and short of it." would make a
truncated chapter look intentional, and that is the one outcome worth avoiding.

Script with no case (Arabic, digits, punctuation) is left exactly as it is:
`str.upper()` on a letter that has no uppercase form is a no-op everywhere, but
being explicit keeps a future reader from assuming otherwise.

Deterministic, idempotent, no model, no cost.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import _HEADING_RE, anchor_key  # noqa: E402

#: Inline markers a paragraph may legitimately open with before its first letter.
#: `*` and `_` are emphasis, and the quote/bracket forms open a quotation. A
#: LIST item (`* `, `- `, `1. `) is not prose and is excluded by _is_prose below,
#: so the ambiguity of a leading `*` is settled by what follows it, not guessed.
_LEAD = re.compile(r'^([\s"\'“‘\(\[\*_]*)(.*)$', re.DOTALL)

#: A line that is markdown structure rather than the chapter's opening prose.
_NOT_PROSE = re.compile(
    r"""^(
        \#            # a heading
      | >             # a blockquote
      | \|            # a table row
      | !             # an image
      | <             # raw html
      | ```           # a fence
      | ---           # a rule or front-matter
      | (\*|-|\+)\s   # a bullet ("* " with the space, unlike *emphasis*)
      | \d+\.\s       # a numbered item
    )""",
    re.VERBOSE,
)

#: A fragment reads as the tail of a sentence that began somewhere else: it opens
#: on a lowercase word and reaches a sentence end before it reaches a clause of
#: its own. Deliberately narrow — it reports, it never edits.
_FRAGMENT = re.compile(r"^[a-z][a-z'’-]*\s*,")


def _is_prose(line: str) -> bool:
    return bool(line.strip()) and not _NOT_PROSE.match(line.strip())


def _first_prose_line(body: str) -> tuple[int, str] | None:
    """The index and text of the paragraph a reader meets first, or None.

    Skips fenced blocks wholesale: a chapter that opens with code has no opening
    sentence to capitalize, and the first letter inside a fence is code.
    """
    fenced = False
    for idx, line in enumerate(body.split("\n")):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if _is_prose(line):
            return idx, line
    return None


def _capitalize(line: str) -> str:
    """Uppercase the first cased letter, leaving any opening markup in place."""
    m = _LEAD.match(line)
    if not m:
        return line
    lead, rest = m.group(1), m.group(2)
    if not rest:
        return line
    first = rest[0]
    if not first.isalpha() or not first.islower():
        return line
    return lead + first.upper() + rest[1:]


def openings(text: str) -> list[dict]:
    """Every chapter's opening line, with what this module would do to it."""
    out: list[dict] = []
    parts = _HEADING_RE.split(text)
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        found = _first_prose_line(body)
        if not found:
            continue
        _, line = found
        stripped = _LEAD.match(line).group(2) if _LEAD.match(line) else line
        out.append(
            {
                "chapter": head.lstrip("# ").strip(),
                "key": anchor_key(head),
                "line": line.strip(),
                "lowercase": bool(stripped and stripped[0].isalpha() and stripped[0].islower()),
                "fragment": bool(_FRAGMENT.match(stripped)),
            }
        )
    return out


def fragment_openings(text: str) -> list[dict]:
    """Chapters whose opening looks like the tail of a lost sentence.

    PASS THE TEXT BEFORE `capitalize_openings`. The signal IS the lowercase word
    — "telling," reads as a tail, "However," is somebody starting a sentence — so
    reading this after the capital has been applied finds nothing, every time.
    Compose is unaffected by that ordering because it regenerates the chapter from
    source on each run, so the lowercase returns and the warning re-fires.

    Reported, never repaired: restoring the missing words is a content decision
    that belongs to a person with the source in front of them.
    """
    return [o for o in openings(text) if o["fragment"]]


def capitalize_openings(text: str) -> str:
    """Return `text` with every chapter's first prose letter capitalized."""
    parts = _HEADING_RE.split(text)
    if len(parts) == 1:
        return text
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        found = _first_prose_line(body)
        if found:
            idx, line = found
            lines = body.split("\n")
            lines[idx] = _capitalize(line)
            body = "\n".join(lines)
        out.append(head)
        out.append(body)
    return "".join(out)


def apply_chapter_openings(book_dir: Path, *, log=print) -> None:
    """The `5a-opening` step: capitalize, then report any fragment.

    The file handling lives here rather than at the call site because that is
    what `apply_arabic_substitution` and `apply_bridges` already do — a step that
    inlines its own read/write in the apparatus is the minority shape, and this
    one has a two-part body (fix, then warn) that would be the longest of them.
    """
    md = book_dir / "book" / "book.md"
    if not md.exists():
        return
    before = md.read_text(encoding="utf-8")
    # Read the fragments off `before`: the lowercase IS the signal, and
    # `capitalize_openings` is about to remove it.
    fragments = fragment_openings(before)
    after = capitalize_openings(before)
    if after != before:
        md.write_text(after, encoding="utf-8")
        log("    opening: chapter openings capitalized")
    for frag in fragments:
        log(f"    opening: WARNING {frag['chapter']!r} opens mid-sentence — text may be lost at the boundary")
