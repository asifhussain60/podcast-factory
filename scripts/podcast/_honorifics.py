"""_honorifics.py — introduce an honorific in full, then abbreviate it.

A reading edition may use `(ع)` freely, but only once the reader has been shown
what it stands for. `the-master-and-the-disciple` shipped the other way round: six
`(ع)` sites and not one full `(عليه السلام)` in front of any of them, so a reader
meeting the first one had no way to know it was an honorific rather than, say, the
Arabic for the name beside it. Worse, a spelled-out `(عليهم السلام)` sat two pages
later, which reads as inconsistency rather than convention.

The rule, in Asif's words: *"I'm ok with the short honorific as long as the full
form has been used the first time."* So the FIRST occurrence of each honorific
prints its full formula and every later one prints the abbreviation.

Two properties this leans on:

  BOOK-SCOPED, not chapter-scoped. A convention is introduced once, in the copy a
  reader holds. Resetting per chapter would spell it out nine times and stop being
  a convention at all.

  PER FAMILY. `(ع)` is not `(عليهم السلام)` — singular and plural address
  different people, so seeing one teaches the reader nothing about the other. Each
  abbreviation is tracked against its own full form.

Deterministic and idempotent: after a run the first site holds the full formula,
which this pass then recognises as the introduction, so a second run changes
nothing. No model, no cost, nothing recalled.
"""

from __future__ import annotations

import re

from _arabic_coverage import normalize_arabic
from _book_arabic_audit import _HONORIFIC_FORMULAS

# The registry. One line per abbreviation — this is the only place to add one, per
# the repo's extensibility rule. Every expansion is asserted below to be a formula
# the Arabic audit already recognises, so this file can never introduce a spelling
# the audit would then flag as unverified Arabic.
HONORIFIC_ABBREVIATIONS: dict[str, str] = {
    "ع": "عليه السلام",
    "س": "عليها السلام",
    "ص": "صلى الله عليه وآله وسلم",
    "رض": "رضي الله عنه",
}

_UNKNOWN = [full for full in HONORIFIC_ABBREVIATIONS.values() if normalize_arabic(full) not in _HONORIFIC_FORMULAS]
if _UNKNOWN:  # pragma: no cover — a wiring error, caught at import
    raise ImportError(f"honorific expansion not in _HONORIFIC_FORMULAS: {_UNKNOWN}")

# Any parenthesised run short enough to be an honorific. Deliberately broad on the
# match and narrow on the decision: the callback below classifies the contents,
# which keeps the two questions ("is this parenthetical?" / "is it an honorific?")
# from being answered by one hard-to-read pattern.
_PAREN_RE = re.compile(r"\(([^()\n]{1,40})\)")


def expand_first_honorific_use(text: str) -> tuple[str, int]:
    """Spell out the first use of each honorific. Returns (text, expansions).

    A full formula met before its own abbreviation counts as the introduction, so
    a book that already spells one out on page three is left exactly as it is.
    """
    introduced: set[str] = set()
    expanded = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal expanded
        inner = match.group(1).strip()
        skeleton = normalize_arabic(inner)
        if skeleton in _HONORIFIC_FORMULAS:
            # The full form itself — whether it was always here or this pass just
            # wrote it. Either way the reader has now been shown the convention.
            introduced.add(skeleton)
            return match.group(0)
        full = HONORIFIC_ABBREVIATIONS.get(inner)
        if not full:
            return match.group(0)
        key = normalize_arabic(full)
        if key in introduced:
            return match.group(0)
        introduced.add(key)
        expanded += 1
        return f"({full})"

    return _PAREN_RE.sub(replace, text), expanded
