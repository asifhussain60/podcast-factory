"""_book_honorific_defects.py — who a book names, and how it honours them.

Split out of `_book_defects.py` on 2026-08-11 when the two new Sessions checks pushed
that module past the DR-005 line cap. A real seam rather than an arbitrary cut: every
rule here is about a PERSON — which figure a bracket attaches to, which honorific is
theirs, how often it may be repeated, and what to do when it was typed in Latin letters.
Everything left behind in `_book_defects` is about how the PROSE is set.

The distinction is load-bearing rather than tidy. Reading a name backward out of a
sentence, folding "Ali" and "Ali ibn Abi Talib" into one man, and knowing that the
Prophet's honorific is mandatory where the Imams' is capped are all one body of
knowledge, and every one of them was learned from a defect Asif found by eye in a
shipped edition. A second module holding half of it would be where the two halves start
disagreeing about who somebody is.

FOUR CHECKS LIVE HERE

  honorific-overuse     `(ع)` after every occurrence of every name. Capped per figure per
                        chapter (Asif, 2026-08-09), counted under `figure_key`.

  prophet-wrong-honorific
                        the Prophet carrying `(ع)`, which belongs to the Imams. His is
                        the ligature, and it is NOT subject to the cap — it is mandatory
                        on every mention by name.

  romanized-honorific   a devotional formula spelled out in Latin letters. Repairable,
                        unlike a romanized SAYING, and the difference is the whole reason
                        it is its own check — see the table's own note.

Nothing here mutates a book; the repairs are in `_book_defect_fixes`.
"""

from __future__ import annotations

import re

from _book_defects import chapters
from _vowelling import MARKS_BODY as _MARKS_BODY

#: Arabic diacritics — imported, never retyped. `_vowelling` owns this set because it
#: is the marks-only gate's own definition of a mark, and the honorific matcher below
#: has to agree with it: a second spelling would let one of the two accept a phrase the
#: other rejected. (A test also refuses a module that respells an Arabic range.)
_TASHKEEL = _MARKS_BODY


def _tolerant(bare: str) -> str:
    """A pattern matching ``bare`` however it is vowelled.

    A hardcoded vowelled literal is a trap and it sprang immediately: `(عَلَيْهِ السَّلَامُ)`
    written with the shadda before the fatha did not match the same phrase written the
    other way round, so the expanded honorific opening chapter 1 of Spiritual Ethos was
    invisible to a check whose whole subject is honorifics. Since 2026-07-29 every Arabic
    run on the page is vowelled by a model, so the marks are exactly the part that cannot
    be predicted — and the consonantal skeleton is exactly the part that can.
    """
    marks = f"[{_TASHKEEL}]*"
    # Leading and TRAILING marks matter as much as the ones between letters: the final
    # damma on `السَّلَامُ` sits between the last letter and the closing bracket, and a
    # pattern that stopped at the letter matched nothing at all.
    return marks + marks.join((r"\s+" if ch == " " else re.escape(ch)) for ch in bare) + marks


#: The compact honorifics a figure other than the Prophet carries. The Prophet's own
#: form is deliberately absent — it is mandatory rather than capped, so counting it
#: here would report the convention working as though it were the defect.
_HONORIFIC_RE = re.compile(
    r"\((?:"
    + "|".join(
        [
            _tolerant("ع"),
            _tolerant("عليه السلام"),
            _tolerant("عليها السلام"),
            _tolerant("عليهم السلام"),
            _tolerant("رضي الله عنه"),
            r"as",
            r"a\.s\.",
        ]
    )
    + r")\)",
    re.IGNORECASE,
)

#: The name a compact honorific attaches to, read BACKWARD from the honorific. Two
#: patterns rather than one, because the thing that distinguishes a name from a
#: sentence-initial word is a CONNECTOR: "Ali ibn Abi Talib" is one figure, "Later Ali"
#: is an adverb followed by a figure, and both are two capitalised tokens in a row.
#: So a multi-word figure is accepted only when a connector joins it, and everything
#: else falls back to the single capitalised token immediately before.
_NAME_JOINED_RE = re.compile(
    r"([A-Z][\w'’-]*(?:\s+(?:ibn|bin|bint|abi|abu|of|the|al-[\w'’-]+)(?:\s+[A-Z][\w'’-]*)+)+)\s*$"
)
_NAME_SINGLE_RE = re.compile(r"([A-Z][\w'’-]*)\s*$")

#: A figure's name never runs across one of these, so the backward read stops here.
_SENTENCE_BREAK_RE = re.compile(r"[.!?;:\n\"“”(]")

#: Words that look like a name to the patterns above but are not one.
_NOT_A_FIGURE = frozenset(
    {"he", "him", "his", "she", "her", "they", "them", "it", "the", "and", "said", "from", "may", "a", "an"}
)

#: The label a compact honorific gets when no name precedes it. `He (ع)` names nobody,
#: and reporting it as a figure called "He" would make the count unreadable.
UNATTRIBUTED = "(no name attached)"


#: How the edition names the Prophet, in either script. Deliberately does NOT include a
#: bare "Muhammad": the corpus also carries Jafar ibn Muhammad and Abu Jafar Muhammad
#: ibn Ali, for whom `(ع)` is correct, so a bare-name rule would report those as defects.
_PROPHET_NAME = (
    r"(?:the\s+)?(?:Holy\s+)?(?:Prophet(?:\s+Muhammad)?|Messenger\s+of\s+(?:Allah|God)"
    r"|Rasul\s*[- ]?\s*Allah|\u0631\u0633\u0648\u0644\s+\u0627\u0644\u0644\u0647|\u0627\u0644\u0646\u0628\u064a)"
)

#: The Prophet named, then a honorific that belongs to somebody else.
_PROPHET_HONORIFIC_RE = re.compile(_PROPHET_NAME + r"\s*" + _HONORIFIC_RE.pattern, re.IGNORECASE)


def opens_a_longer_formula(text: str, start: int) -> bool:
    """Is the honorific at ``start`` the FIRST thing inside another bracket?

    `the Messenger of Allah ((ع) and his family)` is ONE formula — "peace be upon him and
    his family" — that happens to open with the compact glyph. It is not the compact
    honorific used after a name, so the cap does not govern it, and the repair cannot
    touch it without leaving `(and his family)`, which says something the author did not.

    Shared by the detector and the repair deliberately. While only the repair skipped it,
    the check counted 47 instances the fixer would never reach, so four chapters of
    Mukhtasar 2 stayed permanently over-cap and a second pass repaired nothing.
    """
    return start > 0 and text[start - 1] == "("


def figure_key(figure: str) -> str:
    """The identity a figure label counts under.

    "Ali" and "Ali ibn Abi Talib" are one man, and a cap of once per figure per chapter
    that treated them as two would leave the reader three honorifics in two paragraphs —
    which is what chapter 1 of Spiritual Ethos did on the first repair run. The given
    name is what a reader recognises across the variants, so it is the key; the fuller
    label is still what gets REPORTED, because "Ali ×54" is the finding a human reads.
    """
    first = figure.split()[0].lower() if figure.split() else figure.lower()
    return first.strip(",.;:'’-") or figure.lower()


def _figure_before(text: str) -> str:
    """The figure a compact honorific at the end of ``text`` attaches to."""
    # A trailing comma is the appositive's opener — `The Messenger of Allah, (ع), used
    # to` — and it separates the name from the honorific in 507 of the corpus's 1,674
    # instances. Leaving it on made every one of those UNATTRIBUTED, which is how one
    # chapter reported 78 honorifics attached to nobody and why the cap left them alone.
    tail = _SENTENCE_BREAK_RE.split(text)[-1][-80:].rstrip(", \t")
    match = _NAME_JOINED_RE.search(tail) or _NAME_SINGLE_RE.search(tail)
    if not match:
        return UNATTRIBUTED
    words = [w for w in match.group(1).split() if w.lower() not in _NOT_A_FIGURE]
    return " ".join(words) if words else UNATTRIBUTED


# ── document structure ───────────────────────────────────────────────────────


#: The devotional formulas the KSESSIONS transcripts spell out in Latin letters, and the
#: script each one is. NOT a transliteration table and NOT a general romanization repair:
#: every entry here is a FIXED FORMULA whose Arabic is not in dispute anywhere, which is
#: exactly why supplying it is not the thing `romanized_arabic` refuses.
#:
#: That refusal stands and is unchanged. A romanized SAYING has a specific Arabic wording
#: that a model would have to recall, and recalling scripture is forbidden here. A
#: honorific has one wording, said the same way by everyone who says it, and this repo
#: already hardcodes one of them — `PROPHET_LIGATURE` — on precisely this reasoning.
#:
#: THE PROPHET'S FORM IS THE LIGATURE, and that is Asif's choice of 2026-08-11 made with
#: the cost stated: `ﷺ` is *sallallahu alayhi wa sallam* and the transcripts say
#: *wa aalihee* — and his family. He chose consistency with the six books already using
#: the ligature over keeping the longer form on this one. Recorded because it is a
#: doctrinal preference, not a formatting default, and a later reader of this table
#: should not have to guess that somebody weighed it.
#:
#: Allah's carries its vowel marks, per the standing rule for Arabic this repo writes.
#: The Prophet's is a single ligature glyph and has none to carry.
#:
#: Spellings vary in the source — `Subhanahu` and `Subhanhu`, capitalised either way —
#: so the match folds case and is anchored to the whole bracket.
#:
#: ONLY ATTESTED FORMS GO IN. `(SWS)` is here because 81 of them stand in Love Of The
#: Prophet and every one follows the Prophet by name — checked, not assumed. `(SAW)`,
#: `(PBUH)` and the rest are deliberately absent until a book actually carries one: an
#: initialism this short is exactly where a defensive guess starts matching English.
ROMANIZED_HONORIFICS: dict[str, str] = {
    r"sal+allahu\s+alayhi\s+wa\s+aalihee\s+wa\s+sallam": "ﷺ",
    r"sws": "ﷺ",
    r"subhan\w*\s+wa\s+ta'ala": "سُبْحَانَهُ وَتَعَالَى",
}

_ROMANIZED_HONORIFIC_RE = re.compile(
    r"\s*\(\s*(?:" + "|".join(ROMANIZED_HONORIFICS) + r")\s*\)",
    re.IGNORECASE,
)

#: The same alternation without the bracket, for naming which formula a hit was.
_HONORIFIC_FORMS = [
    (re.compile(rf"^{pattern}$", re.IGNORECASE), script) for pattern, script in ROMANIZED_HONORIFICS.items()
]


def honorific_script(run: str) -> str | None:
    """The Arabic a spelled-out honorific should be set in, or None if it is not one."""
    stripped = run.strip().strip("*_").strip()
    return next((script for form, script in _HONORIFIC_FORMS if form.match(stripped)), None)


def romanized_honorific(md: str) -> list[tuple[str, str]]:
    """(chapter, run) for each devotional formula printed in the English character set.

    Split from `romanized_arabic` because the two have OPPOSITE repairs, and reporting
    them together is what made 197 instances in Surah Al-Fateha read as unfixable. A
    saying needs its own wording found on disk and is refused when it is not there; a
    honorific has one wording and is simply set in script.

    `romanized_arabic` excludes whatever this claims, so each run is reported once, by
    the check that can do something about it.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for match in _ROMANIZED_HONORIFIC_RE.finditer(body):
            hits.append((title, match.group(0).strip().strip("()").strip()))
    return hits


def honorific_overuse(md: str, *, cap: int = 1) -> list[tuple[str, str, int]]:
    """(chapter, figure, count) where a figure carries more compact honorifics than `cap`.

    Asif, 2026-08-09: once per figure per chapter, used where it adds value rather than
    after every occurrence of the name. The Prophet's own honorific is NOT counted — it
    is mandatory on every mention by name, so counting it here would report the
    convention working as though it were the defect.
    """
    hits: list[tuple[str, str, int]] = []
    for title, body in chapters(md):
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        for match in _HONORIFIC_RE.finditer(body):
            if opens_a_longer_formula(body, match.start()):
                continue
            figure = _figure_before(body[: match.start()])
            key = figure_key(figure)
            counts[key] = counts.get(key, 0) + 1
            # Report the FULLEST label the chapter used for this person — "Ali ibn Abi
            # Talib" tells a reader who is meant where the key "ali" does not.
            if len(figure) > len(labels.get(key, "")):
                labels[key] = figure
        for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if count > cap:
                hits.append((title, labels[key], count))
    return hits


def prophet_wrong_honorific(md: str) -> list[tuple[str, str]]:
    """(chapter, mention) where the Prophet carries a honorific that is not his.

    True under any reading of the convention, so it does not wait on the cap policy:
    `(ع)` is the honorific of the Imams and the other figures, and `The Messenger of
    Allah (ع)` — 21 times in one chapter of Mukhtasar 2 — gives the Prophet somebody
    else's. His own form is the ligature `ﷺ` (Asif, 2026-08-09).
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for match in _PROPHET_HONORIFIC_RE.finditer(body):
            hits.append((title, " ".join(match.group(0).split())))
    return hits
