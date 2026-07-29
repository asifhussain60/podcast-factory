"""_vowelling.py — the admissibility gate for supplied Arabic vowelling.

PYTHON HALF OF A MIRROR PAIR. The JavaScript half is
``plan-dashboard/scripts/lib/vowelling.mjs``, which serves the Composer's
Diacritics button; this half serves the compose-time pass
(``vowel_book.py``). Both are pinned to the SAME fixtures at
``plan-dashboard/scripts/lib/vowelling.fixtures.json`` — a change to either
implementation that is not matched in the other fails a test rather than letting
the button and the pipeline disagree about what counts as an admissible
vowelling. Same contract as the repo's three other mirror pairs.

WHAT THIS GATE IS, AND WHAT IT IS NOT (Asif, 2026-07-29). It is NOT a rule about
whether Arabic should be vowelled. That question is settled: it always should be.
Asif does not read Arabic, so a bare run is not "unverified" to him, it is
unreadable, and the earlier contract — a model proposes, a human accepts, and
only then does a mark reach the page — was reversed for exactly that reason.

What survives is narrower and load-bearing: a vowelling may differ from its
source in MARKS ONLY. ``skeleton()`` strips every combining mark and tatweel, and
a candidate is refused unless its skeleton is byte-identical to the source run's.
A model that adds marks passes. A model that "corrects" a letter, drops a word,
normalises a hamza form, or quietly substitutes the mushaf's Uthmani spelling
fails and never reaches ``book.md``. On an Arabic verb a wrong vowel is a reading
choice; a changed letter is a different word, and this book is largely reported
speech. Relaxing the policy on marks was Asif's call; letting letters move under
cover of it never was.
"""

from __future__ import annotations

import re

# Combining marks: tashkeel, superscript alif, Quranic annotation signs. Tatweel
# is included because it stretches a letter rather than being one, and two
# otherwise-identical skeletons must not differ over it.
MARKS_RE = re.compile("[ً-ْٓ-ٰ۟۠-ۭـ]")

# Arabic script, for asking whether a string contains Arabic at all.
ARABIC_RE = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")

# Marks per Arabic letter above which a run counts as already vowelled. The bare
# source averages ~0.02; a fully vowelled text runs an order of magnitude higher.
# Deliberately generous: a run the scanner left with two disambiguating marks is
# still bare for this purpose. Used only to CHOOSE runs, never to judge one.
VOWELLED_DENSITY = 0.15

# Shortest run worth vowelling, in skeleton characters excluding whitespace. Below
# this a "run" is a stray word inside English prose, where the surrounding sense a
# vocalisation depends on is not in the run at all.
MIN_RUN_CHARS = 8


def skeleton(text: str) -> str:
    """The consonantal skeleton: every mark and tatweel gone, whitespace collapsed.

    Two strings with the same skeleton differ ONLY in vocalisation, which is the
    entire permitted delta.
    """
    return re.sub(r"\s+", " ", MARKS_RE.sub("", text or "")).strip()


def mark_count(text: str) -> int:
    """How many combining marks a run carries."""
    return len(MARKS_RE.findall(text or ""))


def mark_density(text: str) -> float:
    """Marks per Arabic letter. Zero for a run with no Arabic letters at all."""
    letters = [c for c in (text or "") if ARABIC_RE.match(c) and not MARKS_RE.match(c)]
    return (mark_count(text) / len(letters)) if letters else 0.0


def rejection_reason(source: str, candidate: str) -> str | None:
    """Why this vowelling is inadmissible, or ``None`` when it may be applied.

    The reason is returned rather than swallowed: a passage the model keeps
    failing on is a passage a human should look at directly.
    """
    if not candidate or not candidate.strip():
        return "empty"
    if not ARABIC_RE.search(candidate):
        return "no Arabic script in the candidate"
    a, b = skeleton(source), skeleton(candidate)
    if a != b:
        # Report the first divergence — "differs at character 12" lets a reader
        # see instantly whether a word was rewritten or a clause dropped.
        i = 0
        while i < len(a) and i < len(b) and a[i] == b[i]:
            i += 1
        return (
            f"letters changed, not just marks (first difference at character {i + 1}: "
            f'source "{a[i : i + 12]}" vs proposal "{b[i : i + 12]}")'
        )
    if mark_count(candidate) <= mark_count(source):
        return "adds no vowel marks"
    return None


def is_vowelling_candidate(text: str) -> bool:
    """A run worth vowelling: Arabic, long enough to be a passage, still bare."""
    t = (text or "").strip()
    if not ARABIC_RE.search(t):
        return False
    if len(skeleton(t).replace(" ", "")) < MIN_RUN_CHARS:
        return False
    return mark_density(t) < VOWELLED_DENSITY


def is_arabic_passage(text: str) -> bool:
    """Predominantly Arabic, not merely containing some.

    An English paragraph quoting three Arabic words is not a passage to vowel:
    sending it would ask the model to hand back English it must not touch, and the
    skeleton check would then refuse whatever came back. Same ratio the Composer's
    button and the vowelling route apply on their own selections.
    """
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    arabic = len(ARABIC_RE.findall(text or ""))
    return not (latin > 2 or arabic < latin * 4)
