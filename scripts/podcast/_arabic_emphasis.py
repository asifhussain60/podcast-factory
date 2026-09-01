"""Arabic script is never italicised, and this is why it was.

THE CAUSE, traced 2026-08-31 after Asif saw slanted Arabic in the Book Composer.

Italics mark a ROMANIZATION. That is this repo's own convention and it is written
into the articulation standard: REQ-BA-127 speaks of "a term the book sets in
italics as foreign", and the gloss-coverage gate counts `*marifah*` as a term
owing its script. So a source that writes `*dunya*` is correct.

Arabic restoration then replaces the romanization with script IN PLACE —
`text.replace(run, resolution.arabic)` — at three separate sites. The emphasis
around it survives, and `*dunya*` becomes `*دُنْيَا*`: script wearing the marker
that meant "this is a romanization". The markup was right about the old content
and nobody re-examined it for the new.

WHY IT LOOKS BROKEN rather than merely being wrong. Arabic has no italic
tradition and the faces this repo sets it in — Scheherazade New, KFGQPC Uthmanic
— ship no italic. Asked for one, the browser and the PDF renderer both synthesise
an oblique by shearing the glyphs, which is why 619 runs in one book read as
smeared. It is a rendering artifact, not a style.

IT IS SYSTEMIC. Eleven books carry it: 619 runs in `purification-of-the-heart`,
393 in `kunooz-al-hikmah`, 156 in `ayyuhal-walad`'s chapter sources, and a
handful each in eight more. Every automatic gate passed all of them, because
nothing ever asked the question.

THE RULE, stated so it can be checked: emphasis whose content is ENTIRELY Arabic
script is a defect. Emphasis around a romanization is correct and untouched.
Emphasis around a mixed run — `*dunya (دُنْيَا)*` — is left alone too: the
romanization in it still justifies the marker, and guessing at a partial strip
is how a repair starts editing prose.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_BODY

#: `*…*` or `_…_` whose entire content is Arabic script, its marks, and the
#: punctuation and spacing that legitimately sit inside one quotation. Anchored
#: on the emphasis markers, so a run of Arabic that carries no emphasis — the
#: overwhelming majority — is never touched.
#:
#: `**bold**` is deliberately NOT matched: bold is not the romanization marker,
#: and an Arabic phrase a human chose to bold is a decision, not this artifact.
_ITALIC_ARABIC = re.compile(
    r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)|(?<![\w_])_([^_\n]+?)_(?![\w_])",
)

_ARABIC_CHAR = re.compile(f"[{ARABIC_BODY}]")
#: Invisible bidi formatting. NOT content: a Qur'anic verse lifted from the
#: mushaf arrives wrapped in a right-to-left mark and a left-to-right mark, and
#: counting those as "something other than Arabic" made every such verse read as
#: a mixed run and kept its italics. Eighteen survived the first repair of
#: `purification-of-the-heart` for exactly this reason.
_BIDI = "\u200e\u200f\u061c\u200b\u200c\u200d\ufeff"

#: What may accompany script inside one emphasis without making it "mixed":
#: Arabic itself, invisible bidi marks, whitespace, and ASCII punctuation.
#:
#: Arabic's OWN punctuation is deliberately not listed: the comma, semicolon,
#: question mark and full stop all live inside `ARABIC_BODY` already. Spelling
#: them out a second time meant writing a character range whose endpoints are
#: both Arabic, which is precisely what the repo's one-definition ratchet in
#: `tests/test_arabic_coverage.py` forbids — and it caught this module doing it.
#: One definition of what "Arabic" means; everything else asks `ARABIC_BODY`.
_ALLOWED_BESIDE = re.compile(f"[{ARABIC_BODY}{_BIDI}\\s.,:;!?()\\[\\]'\"—–-]+")


def is_script_only(inner: str) -> bool:
    """True when this emphasis wraps Arabic script and nothing that needs it.

    Requires at least one Arabic character (so `*and*` is not a match) and
    nothing outside the allowed set (so `*dunya (دُنْيَا)*` is not one either —
    its romanization still earns the marker).
    """
    if not inner or not _ARABIC_CHAR.search(inner):
        return False
    return _ALLOWED_BESIDE.fullmatch(inner) is not None


def findings(text: str) -> list[str]:
    """Every italicised Arabic run in *text*, in order, deduplicated by content."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _ITALIC_ARABIC.finditer(text or ""):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        if is_script_only(inner) and inner not in seen:
            seen.add(inner)
            out.append(inner)
    return out


def repair(text: str) -> tuple[str, int]:
    """Drop the emphasis around every Arabic-only run. Returns (text, count).

    DETERMINISTIC and content-preserving: it removes two characters per run and
    changes nothing else, so the prose, the script, and the vowelling all come
    out byte-identical apart from the markers. That is what makes it safe to run
    over a finished book instead of re-authoring one.
    """
    n = 0

    def _sub(m: re.Match) -> str:
        nonlocal n
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        if is_script_only(inner):
            n += 1
            return inner
        return m.group(0)

    return _ITALIC_ARABIC.sub(_sub, text or ""), n
