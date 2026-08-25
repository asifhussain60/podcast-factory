"""_book_translation_purity.py — an English translation line must stay English.

THE DEFECT THIS CATCHES. Asif's rule (2026-08-18): "English translations of the
Quran, sayings, quotes, etc., should NEVER include Arabic script. They should
always be correct English translations using American English and grammar."
Confirmed live on `sharh-al-masail-ghulam-hussain` — the compose model, told to
"preserve Arabic script when it appears in the source" and to preserve every
hadith/quote, satisfied both by writing the SAME words twice on one line:

    "The truthful merchant — اَلتَّاجِرُ الصَّدُوقُ — is raised on the Day of
    Resurrection with الصِّدِّيقِينَ and the martyrs."

The Arabic is not lost — the full vowelled hadith already sits in its own
block-quote directly above this line — so the embedded fragments are a pure
duplicate that also breaks the English sentence in half. `_translation_prompts`
now tells the model not to do this; this module is the deterministic backstop,
because a prompt instruction is advisory and this repo's own history is full of
the SAME instruction being satisfied only some of the time (the same compose
call that produced this line was also told "No em dashes" and used one anyway).

WHAT COUNTS AS A VIOLATION. A single glossary term getting its script appended
in a trailing parenthetical — `the ranks (حُدُود)`, `Ali (ع)` — is the book's
own, deliberate, once-per-book annotation convention (`_book_inline_arabic`)
and is never flagged. Anything else — a bare run, a run set off by em dashes,
a run inside a comma, a run any way other than `word (script)` — is a
translation line carrying Arabic it should not carry.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_BODY

_ARABIC_RUN = re.compile(rf"[{ARABIC_BODY}][{ARABIC_BODY}\s]*[{ARABIC_BODY}]|[{ARABIC_BODY}]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")

# The one legitimate shape: an Arabic run immediately wrapped in its own
# parentheses, directly after a Latin word (the annotation convention).
# Trailing punctuation before the closing paren (a comma, a closing quote) is
# allowed — `_book_inline_arabic`'s own window tolerates that same slack.
_LEGITIMATE_GLOSS = re.compile(rf"\([{ARABIC_BODY}][^()]*\)")


def _is_blockquote_line(line: str) -> bool:
    return line.lstrip().startswith(">")


def embedded_arabic_in_translation(line: str) -> list[str]:
    """Every Arabic run in ``line`` that is NOT a legitimate trailing gloss.

    Returns the offending runs (for reporting); empty when the line is clean.
    Only meaningful for a line that is itself predominantly English — a block
    quote of the ORIGINAL Arabic (no Latin letters at all, or only a citation
    label) is exactly what should carry the script and is never flagged.
    """
    if not _is_blockquote_line(line):
        return []
    if not _LATIN_LETTER.search(line):
        return []  # the Arabic quotation block itself — not a translation line
    # Mask out every legitimate gloss first, so a run genuinely inside one
    # never gets re-discovered by the general scan below.
    masked = _LEGITIMATE_GLOSS.sub("", line)
    return [m.group(0) for m in _ARABIC_RUN.finditer(masked)]


def translation_purity_findings(book_md: str) -> list[str]:
    """Every line in ``book_md`` carrying Arabic embedded in an English
    translation, as human-readable findings (line number + offending run(s))."""
    findings: list[str] = []
    for i, line in enumerate(book_md.splitlines(), start=1):
        offenders = embedded_arabic_in_translation(line)
        if offenders:
            sample = ", ".join(offenders[:3])
            findings.append(f"line {i}: Arabic embedded in an English translation — {sample}")
    return findings
