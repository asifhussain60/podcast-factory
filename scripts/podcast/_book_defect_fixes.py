"""_book_defect_fixes.py — the repairs for what `_book_defects` finds.

Detection and repair are separate modules on purpose. The detectors are read-only and
three callers share them; these functions REWRITE prose, and prose bound for the PDF has
a single sanctioned path — the Book Composer. So nothing here is wired into a compose
step. `compose_fix.py` calls them, records the result through the Composer's own save,
and the replay carries it into every future compose.

WHAT IS REPAIRED HERE, AND WHAT IS NEVER

  duplicated-arabic         REPAIRED. The lead-in's inline copy is deleted and the
                            blockquote keeps the quotation. Deterministic: the two runs
                            are already known to be the same text.

  prophet-wrong-honorific   REPAIRED. `The Messenger of Allah (ع)` becomes
                            `The Messenger of Allah ﷺ`. His own form (Asif, 2026-08-09).

  honorific-overuse         REPAIRED. The first use in a chapter stays, the rest go.

  romanized-arabic          NEVER, not here. Two of the fourteen live instances have no
                            Arabic anywhere on disk — not in the book, not in the source
                            scan, not in the hadith corpus — so the only way to supply
                            their script is a model recalling scripture, which this repo
                            forbids. `proposed_romanization_deletions` returns what a
                            human could approve; nothing applies it automatically.

  english-rtl               NEVER. It was a renderer defect and it is fixed there. A
                            content repair would be a workaround for a bug that is gone.

Every function is idempotent: running it twice changes nothing the first run did not.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_BODY, normalize_arabic
from _book_defects import (
    _HONORIFIC_RE,
    _PROPHET_NAME,
    ARABIC_ONLY_RE,
    MIN_QUOTATION_CHARS,
    _figure_before,
    blocks,
    duplicated_arabic,
)

#: The Prophet's own honorific (U+FDFA). Set in the Arabic face at the size the rest of
#: the Arabic uses, because the renderer wraps it in the same inline-Arabic span.
PROPHET_LIGATURE = "ﷺ"

#: A parenthesised Arabic run in running prose — the shape the lead-in duplicate takes.
_INLINE_ARABIC_PAREN_RE = re.compile(f"\\s*\\(([{ARABIC_BODY}][{ARABIC_BODY}\\s،؛]*)\\)")

#: Arabic faces that DO NOT CONTAIN U+FDFA. A book set to one of these would print an
#: empty box on every mandated mention, which on this rule is every page. Verified by
#: reading the font files 2026-08-09: Amiri, Scheherazade New and IBM Plex Sans Arabic
#: carry the glyph; these two do not.
FACES_WITHOUT_LIGATURE = ("Cairo", "Tajawal")

_PROPHET_HONORIFIC_SUB_RE = re.compile("(" + _PROPHET_NAME + r")\s*" + _HONORIFIC_RE.pattern, re.IGNORECASE)


def use_prophet_ligature(md: str) -> tuple[str, int]:
    """Give the Prophet his own honorific wherever he carries somebody else's.

    Idempotent: the pattern matches only a compact honorific, and the ligature is not
    one, so a second run finds nothing.
    """
    replaced = 0

    def _swap(match: re.Match[str]) -> str:
        nonlocal replaced
        replaced += 1
        return f"{match.group(1)} {PROPHET_LIGATURE}"

    return _PROPHET_HONORIFIC_SUB_RE.sub(_swap, md), replaced


def cap_honorifics(md: str, *, cap: int = 1) -> tuple[str, int]:
    """Keep the first `cap` compact honorifics per figure per chapter; drop the rest.

    Asif, 2026-08-09: once per figure per chapter, used where it adds value rather than
    after every occurrence of the name. Counted per chapter because a chapter is what a
    reader sits down to, and re-introducing the convention in the next one is a courtesy
    rather than clutter.

    Runs per chapter over the whole document at once, so the ordinal a figure's honorific
    holds is its position in that chapter — which is what "the first use" means.
    """
    out: list[str] = []
    dropped = 0
    counts: dict[str, int] = {}
    for line in md.split("\n"):
        if line.startswith("## "):
            counts = {}
            out.append(line)
            continue
        rebuilt: list[str] = []
        cursor = 0
        for match in _HONORIFIC_RE.finditer(line):
            figure = _figure_before(line[: match.start()])
            counts[figure] = counts.get(figure, 0) + 1
            if counts[figure] <= cap:
                continue
            # Take the honorific out along with the space that introduced it, so the
            # sentence closes up rather than printing a double space before the comma.
            start = match.start()
            while start > cursor and line[start - 1] == " ":
                start -= 1
            rebuilt.append(line[cursor:start])
            cursor = match.end()
            dropped += 1
        rebuilt.append(line[cursor:])
        out.append("".join(rebuilt))
    return "\n".join(out), dropped


def drop_duplicated_inline_arabic(md: str) -> tuple[str, int]:
    """Delete the lead-in's inline copy of Arabic the blockquote under it repeats.

    The blockquote keeps the quotation — it is the form the edition sets in the Arabic
    face, and the lead-in is English prose that should read as English. Only a
    parenthesised run is removed, and only one whose text the blockquote already gives,
    so nothing that appears once anywhere is ever touched.
    """
    if not duplicated_arabic(md):
        return md, 0

    removed = 0
    lines = md.split("\n")
    # Which Arabic runs a blockquote gives, per chapter, keyed by normalised text.
    chapter_quoted: set[str] = set()
    out: list[str] = []
    # Two passes per chapter: collect what the blockquotes hold, then clean the paras.
    sections: list[list[str]] = [[]]
    for line in lines:
        if line.startswith("## "):
            sections.append([])
        sections[-1].append(line)

    for section in sections:
        body = "\n".join(section)
        chapter_quoted = set()
        for kind, block_lines in blocks(body):
            if kind != "quote":
                continue
            for run in ARABIC_ONLY_RE.findall(" ".join(block_lines)):
                run = run.strip()
                if len(run) >= MIN_QUOTATION_CHARS:
                    chapter_quoted.add(normalize_arabic(run))
        if not chapter_quoted:
            out.extend(section)
            continue
        for line in section:
            if line.startswith(">") or not line.strip():
                out.append(line)
                continue

            def _maybe_drop(match: re.Match[str]) -> str:
                nonlocal removed
                inner = match.group(1).strip()
                if len(inner) < MIN_QUOTATION_CHARS or normalize_arabic(inner) not in chapter_quoted:
                    return match.group(0)
                removed += 1
                return ""

            cleaned = re.sub(_INLINE_ARABIC_PAREN_RE, _maybe_drop, line)
            out.append(re.sub(r" {2,}", " ", cleaned))
    return "\n".join(out), removed


def proposed_romanization_deletions(md: str) -> list[tuple[str, str]]:
    """(chapter, run) a human could approve deleting. NOTHING here applies them.

    An Arabic saying printed in the English character set breaks the rule locked
    2026-08-02, and the honest repair is to set it in Arabic — but the script has to come
    from somewhere. For two of the fourteen live instances it exists nowhere on disk, and
    a model recalling a hadith onto the page of a religious edition is not a repair.

    Deleting the romanization satisfies the rule and costs the reader nothing, because
    the English translation always sits immediately beside it. That is a judgment for
    Asif, so this only ever proposes.
    """
    from _book_defects import romanized_arabic

    return romanized_arabic(md)


#: Repairs by the defect name `_book_defects.DETECTORS` uses, so a caller can ask for a
#: fix by the same word the check reported. A defect absent from this map has no
#: automatic repair, and that is a statement rather than an omission — see the module
#: docstring for why `romanized-arabic` and `english-rtl` are not here.
FIXES = {
    "duplicated-arabic": drop_duplicated_inline_arabic,
    "prophet-wrong-honorific": use_prophet_ligature,
    "honorific-overuse": cap_honorifics,
}
