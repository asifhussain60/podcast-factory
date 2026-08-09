"""_book_defects.py — reading-edition defects the post-articulation route lets through.

Five checks over a finished `book/book.md`, each one a defect Asif found BY EYE in a
shipped edition after every automatic gate had passed it. They live here, in a module,
rather than inside the test that first recorded them, because three callers need the
same answer and a second copy is how two of them start disagreeing:

  * `tests/test_book_articulation_defects.py` — records what stands today
  * the compose apparatus's review gate — so the pipeline stops on a NEW instance
  * the `pf-compose-fix` skill — so a manual repair is judged by the same rule

Nothing here mutates a book. Every function reads markdown and returns findings.

THE FIVE DEFECTS

  DUPLICATED ARABIC       a lead-in sentence carries an Arabic quotation inline, in
                          parentheses, and the blockquote immediately under it repeats
                          the identical run. The reader sees the same words twice in
                          two consecutive lines. The CORRECT shape is the lead-in
                          giving the TRANSLITERATION and the blockquote giving the
                          Arabic — except that since 2026-08-09 romanization is itself
                          a defect (below), so the correct shape is now the lead-in
                          giving the ENGLISH and the blockquote giving the Arabic.

  ENGLISH SET RIGHT-TO-LEFT
                          a translation paragraph inside an Arabic blockquote rendered
                          in the Arabic face, right to left, with its quotation marks
                          thrown to the wrong ends. FIXED at the renderer 2026-08-09;
                          this asks the renderers' own live question, so the check is
                          end-to-end proof over real content that the fix holds.

  ROMANIZED ARABIC        a whole Arabic sentence printed in the English character set
                          — `(Ana madinatul-ilm wa 'Ali babuha)`. Asif's rule of
                          2026-08-02 is quoted verbatim in `_book_inline_arabic`:
                          "there should be zero English transliteration of Arabic
                          terms, words, paragraphs, sentences, etc. in book.md."
                          `_book_substitution` implements it for glossary TERMS, under
                          two positive conditions — the romanization must fit the
                          skeleton of a known script, and a human must have classed the
                          term `teach`. A whole SENTENCE matches no glossary term, so
                          nothing reached it and 14 ran in two shipped editions.

  HONORIFIC OVERUSE       `(ع)` after every occurrence of every name. Capped per figure
                          per chapter (Asif, 2026-08-09), and counted under `figure_key`
                          so "Ali" and "Ali ibn Abi Talib" are one man rather than two.

  PROPHET'S HONORIFIC     the Prophet carrying `(ع)`, which belongs to the Imams. His is
                          the ligature. A SEPARATE rule from the cap, and not subject to
                          it: his is mandatory on every mention by name.

WHY POSITIVE CONDITIONS, EVERYWHERE

`_book_substitution` shipped with a denylist and it passed the English word `approach`.
The romanization check therefore requires evidence FOR Arabic — function words, the
article, a construct ending — and it suppresses on evidence AGAINST: an English
function word, or the `ibn`/`abu` of a person's name, which stays romanized by policy.
A name is not a sentence and must never be substituted.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_BODY, normalize_arabic
from _vowelling import MARKS_BODY as _MARKS_BODY

#: An Arabic run long enough to be a QUOTATION rather than a glossed term. A short run
#: legitimately repeats — `(بَاب)` beside "bab" is the house annotation style — and
#: flagging those would bury the real finding.
MIN_QUOTATION_CHARS = 12

#: A translation paragraph long enough that setting it right-to-left is unmistakably
#: wrong. Below this a mixed line is usually a term with its gloss.
MIN_TRANSLATION_LATIN = 20

#: A romanized run must be at least this many words to read as a SENTENCE. One or two
#: romanized words are a term, which is `_book_substitution`'s business and is governed
#: by the annotation policy — this check must not reach into that decision.
MIN_ROMANIZED_WORDS = 3

#: And it must carry at least this much Arabic evidence. Two independent markers, so a
#: single hyphenated English word can never reach the threshold on its own.
MIN_ROMANIZATION_MARKERS = 2

#: What counts as Arabic comes from `_arabic_coverage.ARABIC_BODY`, the repo's ONE
#: definition. Nine modules used to respell it and two of them omitted Extended-A, so
#: the same character was Arabic to one gate and not to another; a test now refuses a
#: new module that retypes the range.
ARABIC_ONLY_RE = re.compile(f"[{ARABIC_BODY}][{ARABIC_BODY}\\s،؛]*")

#: One Arabic character — the same alphabet the two renderers count, which is what makes
#: the shared quotation-line rule comparable across all three copies.
ARABIC_COUNT_RE = re.compile(f"[{ARABIC_BODY}]")

#: Arabic function words and morphology, transliterated. Evidence FOR Arabic.
#: Deliberately excludes `ibn`/`abu`/`umm`/`bint` — those are name particles and appear
#: below as evidence AGAINST, because a name is the one thing that stays romanized.
_ROMANIZATION_MARKERS = re.compile(
    r"(?:^|[\s\-'’])(?:al|wa|bi|fi|min|ila|ma|man|fa|la|lil|li|ya|an|inna|anna|qala|kana|hadha|dhu)(?=[\s\-'’])"
    r"|-(?:ul|al|il|ah|at|un|in|hu|ha|ka|ni)\b"
    r"|['’][a-z]",
    re.IGNORECASE,
)

#: Evidence AGAINST: an English function word means the run is English prose, and a name
#: particle means it is somebody's name. Either one suppresses the finding outright.
_NOT_ARABIC_PROSE = re.compile(
    r"\b(?:the|and|of|is|are|was|were|that|this|which|with|from|see|page|chapter|vol|ibn|bin|abu|umm|bint)\b",
    re.IGNORECASE,
)

#: Where a romanized sentence actually appears: inside a parenthetical beside its
#: English, which is the shape every one of the 14 live instances takes. Bounded length
#: so a whole paragraph of English in brackets is never a candidate.
_PARENTHETICAL_RE = re.compile(r"\(([^()]{12,300})\)")

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


def chapters(md: str) -> list[tuple[str, str]]:
    """(heading, body) for each `##` section, in document order."""
    out: list[tuple[str, str]] = []
    title: str | None = None
    cur: list[str] = []
    for line in md.split("\n"):
        if line.startswith("## "):
            if title is not None:
                out.append((title, "\n".join(cur)))
            title, cur = line[3:].strip(), []
        else:
            cur.append(line)
    if title is not None:
        out.append((title, "\n".join(cur)))
    return out


def blocks(body: str) -> list[tuple[str, list[str]]]:
    """(kind, lines) for each paragraph and blockquote, in order."""
    out: list[tuple[str, list[str]]] = []
    cur: list[str] = []
    kind: str | None = None
    for line in body.split("\n"):
        k = "quote" if line.startswith(">") else ("blank" if not line.strip() else "para")
        if k != kind:
            if cur and kind in ("para", "quote"):
                out.append((kind, cur))
            cur, kind = [], k
        if k != "blank":
            cur.append(line)
    if cur and kind in ("para", "quote"):
        out.append((kind, cur))
    return out


def quotation_runs(text: str) -> list[str]:
    """Arabic runs long enough to be quotations rather than glossed terms."""
    return [r.strip() for r in ARABIC_ONLY_RE.findall(text) if len(r.strip()) >= MIN_QUOTATION_CHARS]


def quote_paragraphs(lines: list[str]) -> list[str]:
    """A blockquote's own paragraphs, with the `>` markers stripped."""
    paras: list[str] = []
    cur: list[str] = []
    for line in lines:
        stripped = line.lstrip(">").strip()
        if not stripped:
            if cur:
                paras.append(" ".join(cur))
                cur = []
        else:
            cur.append(stripped)
    if cur:
        paras.append(" ".join(cur))
    return paras


# ── the four detectors ───────────────────────────────────────────────────────


def duplicated_arabic(md: str) -> list[tuple[str, str]]:
    """(chapter, run) where a blockquote repeats Arabic its lead-in already gave."""
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        found = blocks(body)
        for idx, (kind, lines) in enumerate(found):
            if kind != "quote":
                continue
            lead = next((b for b in reversed(found[:idx]) if b[0] == "para"), None)
            if lead is None:
                continue
            lead_runs = {normalize_arabic(r) for r in quotation_runs(" ".join(lead[1]))}
            for run in quotation_runs(" ".join(lines)):
                if normalize_arabic(run) in lead_runs:
                    hits.append((title, run))
                    break
    return hits


def is_arabic_quote_line(text: str) -> bool:
    """Which script a quotation line is MOSTLY in.

    THIRD COPY of `isArabicQuoteLine`, pinned by the shared fixtures at
    `plan-dashboard/scripts/lib/arabic-quote-line.fixtures.json` — the other two are the
    print renderer and the on-screen reader. A test reads the same fixtures.
    """
    arabic = len(ARABIC_COUNT_RE.findall(text))
    if arabic == 0:
        return False
    return arabic > len(re.findall(r"[A-Za-z]", text))


def english_set_right_to_left(md: str) -> list[tuple[str, str]]:
    """(chapter, opening) for each translation paragraph the renderers WOULD set RTL.

    Asks the renderers' own live question, so a hit here is what the page actually does
    rather than a guess about it.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for kind, lines in blocks(body):
            if kind != "quote":
                continue
            paras = quote_paragraphs(lines)
            if not any(is_arabic_quote_line(p) for p in paras):
                continue
            for para in paras:
                latin = len(re.findall(r"[A-Za-z]", para))
                if latin >= MIN_TRANSLATION_LATIN and is_arabic_quote_line(para):
                    hits.append((title, para[:70]))
    return hits


def is_romanized_arabic(text: str) -> bool:
    """Is this run an Arabic sentence written in the English character set?

    Both conditions are POSITIVE and both are required, because the denylist version of
    this question passed the English word `approach` when `_book_substitution` shipped
    with one. Evidence FOR: Arabic function words, the article, a construct ending.
    Evidence AGAINST: an English function word, or a name particle — a person's name
    stays romanized by the annotation policy and must never be reported here.
    """
    if ARABIC_COUNT_RE.search(text):
        return False
    if len(text.split()) < MIN_ROMANIZED_WORDS:
        return False
    if _NOT_ARABIC_PROSE.search(text):
        return False
    return len(_ROMANIZATION_MARKERS.findall(text)) >= MIN_ROMANIZATION_MARKERS


def romanized_arabic(md: str) -> list[tuple[str, str]]:
    """(chapter, run) for each Arabic sentence printed in the English character set.

    Scoped to PARENTHETICALS, which is the shape all 14 live instances take: an English
    translation followed by the saying in romanization. Running it over free prose would
    reach single terms, and which terms carry an inline annotation is the annotation
    policy's decision, not this check's.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for match in _PARENTHETICAL_RE.finditer(body):
            inner = match.group(1).strip().strip("*_")
            if is_romanized_arabic(inner):
                hits.append((title, inner))
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


#: Every detector, by the name a report and a gate address it under. One registry so a
#: caller cannot know about four of five — which is how the romanization defect ran in
#: two shipped editions while the other checks were being written.
DETECTORS = {
    "duplicated-arabic": duplicated_arabic,
    "english-rtl": english_set_right_to_left,
    "romanized-arabic": romanized_arabic,
    "honorific-overuse": honorific_overuse,
    "prophet-wrong-honorific": prophet_wrong_honorific,
}
