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
#:
#: THE APOSTROPHE ALTERNATIVE IS CASE-SENSITIVE, and it has to be spelled that way
#: because the whole pattern is compiled `IGNORECASE`. It is there for a transliterated
#: hamza or ayn — `ta'wil`, `bala'` — which is always followed by a lower-case letter.
#: Left case-insensitive it also matched an opening single quotation mark before an
#: English word, so `('Glory to me')` scored as Arabic evidence. And `'s` is excluded
#: outright: an English possessive is not a transliteration, and counting it made every
#: `(may Allah's blessings be upon him)` in Mukhtasar ul-Asar — forty of them — read as
#: a romanized Arabic sentence.
_ROMANIZATION_MARKERS = re.compile(
    r"(?:^|[\s\-'’])(?:al|wa|bi|fi|min|ila|ma|man|fa|la|lil|li|ya|an|inna|anna|qala|kana|hadha|dhu)(?=[\s\-'’])"
    r"|-(?:ul|al|il|ah|at|un|in|hu|ha|ka|ni)\b"
    r"|['’](?-i:(?!s\b)[a-z])",
    re.IGNORECASE,
)

#: Evidence AGAINST: an English function word means the run is English prose, and a name
#: particle means it is somebody's name. Either one suppresses the finding outright.
_NOT_ARABIC_PROSE = re.compile(
    r"\b(?:the|and|of|is|are|was|were|that|this|which|with|from|see|page|chapter|vol|ibn|bin|abu|umm|bint)\b",
    re.IGNORECASE,
)

#: Evidence AGAINST, second kind: a digit means the bracket is a REFERENCE. Every book
#: here cites in the shape `(Ali 'Imran: 190-191)` or `(Surah al-Talaq, 65:1)`, whose
#: surah name is transliterated Arabic and therefore scores exactly like a saying. No
#: saying anywhere in this corpus contains a digit, so the rule costs nothing.
_CITATION_DIGIT = re.compile(r"\d")

#: Evidence AGAINST, third kind: the bracket is wholly italic. That is the books' own
#: mark for a technical TERM — `(*ribh ma lam yudman*)` — and which terms carry an inline
#: annotation is the annotation policy's decision, not this check's. A quoted saying is
#: never set in italics here.
_WHOLLY_ITALIC = re.compile(r"^([*_])(?!\1).+\1$", re.S)

#: Where a romanized sentence actually appears: inside a parenthetical beside its
#: English, which is the shape every one of the 14 live instances takes. Bounded length
#: so a whole paragraph of English in brackets is never a candidate.
_PARENTHETICAL_RE = re.compile(r"\(([^()]{12,300})\)")


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


def is_romanized_arabic(text: str, *, arabic_beside: bool = False) -> bool:
    """Is this run an Arabic sentence written in the English character set?

    Both conditions are POSITIVE and both are required, because the denylist version of
    this question passed the English word `approach` when `_book_substitution` shipped
    with one. Evidence FOR: Arabic function words, the article, a construct ending.
    Evidence AGAINST: an English function word, or a name particle — a person's name
    stays romanized by the annotation policy and must never be reported here.

    `arabic_beside` IS A PIECE OF EVIDENCE, and the strongest one available. The word
    list needs two hits before it will call a bracket Arabic, which is what keeps the
    English out; but a saying set in Latin letters immediately beside its own Arabic
    script needs no word list to identify it, because the book has already said what the
    words are. Eleven passages in Spiritual Ethos sat one hit under the bar for months
    for want of this — including `(anta minni wa ana minka)`, whose Arabic is the display
    line directly beneath it, and which the whole-book romanization pass of 2026-08-09
    walked past while rewriting the same chapter. The caller decides adjacency; see
    `romanized_arabic`. Lowering the bar to one hit INSTEAD was measured and rejected: it
    returns 58 findings across the seven books, 47 of them blessings, verse citations and
    glossed terms.
    """
    if ARABIC_COUNT_RE.search(text):
        return False
    if len(text.split()) < MIN_ROMANIZED_WORDS:
        return False
    if _NOT_ARABIC_PROSE.search(text):
        return False
    needed = 1 if arabic_beside else MIN_ROMANIZATION_MARKERS
    return len(_ROMANIZATION_MARKERS.findall(text)) >= needed


#: Bidi control marks. The KSESSIONS Quran widget wraps each verse in `&rlm;`/`&lrm;`
#: so it would lay out correctly inside the admin's left-to-right page. The reader sets
#: `dir="rtl"` on the paragraph itself, so they do nothing here but sit invisibly at the
#: ends of the run.
_BIDI_MARKS = "\u200e\u200f\u061c\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"

#: A quotation line closing on an ayah number in Arabic-Indic digits. Anchored to the
#: END: a digit inside a verse is part of the text, and no mushaf verse ends in one.
_TRAILING_AYAH_NUMBER_RE = re.compile(rf"[\s{_BIDI_MARKS}]*[\u0660-\u0669\u06f0-\u06f9]+[\s{_BIDI_MARKS}]*$")


def clean_verse_line(text: str) -> str:
    """The quotation as the mushaf holds it — no widget numeral, no invisible marks."""
    return _TRAILING_AYAH_NUMBER_RE.sub("", text).strip(_BIDI_MARKS + " ").strip()


def quote_line_noise(md: str) -> list[tuple[str, str]]:
    """(chapter, line) for each quoted verse carrying the widget's presentation debris.

    A VERSE IS RECOGNISED BY MATCHING THE CANONICAL MUSHAF EXACTLY, so anything the
    KSESSIONS Quran widget attached to the run decides whether the reader draws a Qur'an
    card or a generic quotation. Two things did, and both are invisible on the page:

      the ayah number   `۲۵۷` in Arabic-Indic digits, appended inside the verse
      bidi marks        `&rlm;` / `&lrm;` wrapped around it so the admin's own
                        left-to-right page would lay the Arabic out correctly

    In Surah Al-Fateha they cost 67 of the 75 quotations their match: no Uthmani face,
    no citation band, no `is-quranic`. Neither carries meaning here — the reader sets
    `dir="rtl"` itself, and it resolves the reference from the mushaf and prints
    `Al-Baqarah: 257` on the card's band, which says more than the bare numeral did.

    Scoped to Arabic-MAJORITY quotation lines. A digit inside a verse belongs to the
    text, and an English line's trailing number is a citation somebody wrote.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for _kind, lines in blocks(body):
            for line in lines:
                text = line[1:].strip() if line.startswith(">") else line
                if is_arabic_quote_line(text) and clean_verse_line(text) != text:
                    hits.append((title, text))
    return hits


def stray_emphasis(md: str) -> list[tuple[str, str]]:
    """(chapter, paragraph) for each paragraph carrying an unpaired `**`.

    An emphasis marker with no partner IN ITS OWN PARAGRAPH does not italicise anything —
    it prints, as two asterisks, in the middle of a reading edition. Sixteen of them show
    in Love Of The Prophet on the live site.

    THE PARAGRAPH IS THE UNIT, and that is the whole subtlety. Every one of the eight
    live blockquotes has an EVEN number of markers, so a block-level count sees nothing:

        > **Muhammad Ibn Abdullah — Accountability, Deeds
        >
        > حَاسِبُوا أَنْفُسَكُمْ …
        >
        > Hold yourselves accountable … before they are weighed**

    An opener on the attribution line and a closer four paragraphs later. Both renderers
    set each paragraph of a quotation as its own `<p>`, so neither marker ever meets its
    partner and both reach the page as text. Counting the block would call that balanced.

    The cause is upstream and is fixed — the Sessions converter read Font Awesome's `<i>`
    icons as emphasis, and the quotation builder balanced the odd count by appending a
    closer at the very end. This finds what that already wrote into chapters which are
    frozen by Composer edits and will never be regenerated.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        for _kind, lines in blocks(body):
            for para in _quote_paragraphs(lines):
                if para.count("**") % 2:
                    hits.append((title, para.strip()))
    return hits


def _quote_paragraphs(lines: list[str]) -> list[str]:
    """The paragraphs of one block, as the renderers divide them.

    A blockquote's `>` lines are split on its blank `>` lines, which is exactly where
    both renderers start a new `<p>`. A plain paragraph is one paragraph.
    """
    out: list[str] = []
    cur: list[str] = []
    for line in lines:
        stripped = line[1:].strip() if line.startswith(">") else line
        if not stripped.strip():
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        cur.append(stripped)
    if cur:
        out.append(" ".join(cur))
    return out


def romanized_arabic(md: str) -> list[tuple[str, str]]:
    """(chapter, run) for each Arabic sentence printed in the English character set.

    Scoped to PARENTHETICALS, which is the shape all 14 live instances take: an English
    translation followed by the saying in romanization. Running it over free prose would
    reach single terms, and which terms carry an inline annotation is the annotation
    policy's decision, not this check's.

    "BESIDE" IS THE PARAGRAPH AND ITS TWO NEIGHBOURS, which is where a saying's own
    script actually sits: in the same sentence in one chapter of Spiritual Ethos, and as
    the display line under the lead-in everywhere else. Wider than that and a chapter
    that merely contains Arabic somewhere would vouch for every bracket in it.
    """
    hits: list[tuple[str, str]] = []
    for title, body in chapters(md):
        paragraphs = body.split("\n\n")
        # Where each paragraph starts, so a match offset can be placed in one of them
        # without searching the text a second time.
        spans: list[tuple[int, int]] = []
        at = 0
        for para in paragraphs:
            spans.append((at, at + len(para)))
            at += len(para) + 2

        for match in _PARENTHETICAL_RE.finditer(body):
            raw = match.group(1).strip()
            if _WHOLLY_ITALIC.match(raw) or _CITATION_DIGIT.search(raw):
                continue
            index = next(
                (i for i, (start, end) in enumerate(spans) if start <= match.start() <= end),
                None,
            )
            beside = index is not None and any(
                ARABIC_COUNT_RE.search(paragraphs[i]) for i in (index - 1, index, index + 1) if 0 <= i < len(paragraphs)
            )
            inner = raw.strip("*_")
            # A devotional formula is `romanized_honorific`'s, and it has a repair.
            # Reported by both, it would be listed as needing judgment it does not need.
            if honorific_script(inner) is not None:
                continue
            if is_romanized_arabic(inner, arabic_beside=beside):
                hits.append((title, inner))
    return hits


def bare_arabic(md: str) -> list[tuple[str, str]]:
    """(chapter, run) where an Arabic passage still carries no vowel marks.

    THE PIPELINE'S RULE, CHECKED A SECOND TIME. Arabic in these editions always
    carries its marks (Asif, 2026-07-29) and `vowel_book` puts them there at
    compose time — so a bare passage here is not a missing feature, it is a compose
    that did not finish the job. Until 2026-08-11 that happened routinely and
    invisibly: a model normalising one letter while vowelling correctly around it
    had its whole answer discarded by the marks-only gate, and the run stayed bare
    with nothing but a line in `_system/book-vowelling.json` to say so.

    The QUESTION is asked with `_vowelling.is_vowelling_candidate` — the very test
    the compose-time pass uses to choose what to vowel — so the check and the pass
    can never disagree about what counts as bare. Scripture is included on purpose:
    a Qur'anic run takes its marks from the canonical mushaf rather than a model,
    and a bare one means that lookup missed, which is worth seeing.
    """
    from _vowelling import is_vowelling_candidate

    hits: list[tuple[str, str]] = []
    for heading, body in chapters(md):
        for run in quotation_runs(body):
            if is_vowelling_candidate(run):
                hits.append((heading, run))
    return hits


_HEADING_RE = re.compile(r"^(#{2,6})[ \t]*(.*?)[ \t]*$")


def orphaned_heading(md: str) -> list[tuple[str, str]]:
    """(chapter, sub-heading) for a `###`+ heading with no body of its own.

    Found 2026-08-14: a Sessions-lane hand-off rewrite left "Meanings Of Word
    ILAH" as a bare topic label directly above its first child, "YALAA" —
    same level, nothing between them, so the reader sees two consecutive
    headings that read as duplicates rather than a topic and its point. The
    actual intro sentence for "Meanings Of Word ILAH" had been misfiled under
    "YALAA" instead, which is the same defect from the other side: a heading
    that owns no prose of its own.

    Two shapes, both empty-handed:
      - a heading whose title text is itself blank (`###` with nothing after
        it) — always wrong, regardless of what follows;
      - a heading with real title text but no paragraph, quote, or list line
        before the NEXT heading at the SAME level — its "body" is just
        another heading it cannot be told apart from.

    A heading immediately followed by a DEEPER heading (`##` then `###`) is
    not a hit: a chapter or section diving straight into its first
    subsection with no preamble is ordinary book structure, not a defect —
    over a third of this book's own chapters open exactly that way.

    Judgment, not mechanics, decides the fix (delete the label, or promote
    what follows into its actual children), so this is deliberately absent
    from `_book_defect_fixes.FIXES` — report-only, like the file's other
    heading-adjacent check would be were one to exist.
    """
    hits: list[tuple[str, str]] = []
    for chapter_title, body in chapters(md):
        lines = body.split("\n")
        headings: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            m = _HEADING_RE.match(line)
            if m:
                headings.append((i, len(m.group(1)), m.group(2)))
        for idx, (line_no, level, title) in enumerate(headings):
            if not title:
                hits.append((chapter_title, f"blank heading marker ({'#' * level})"))
                continue
            next_line_no = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
            has_body = any(line.strip() for line in lines[line_no + 1 : next_line_no])
            if has_body:
                continue
            if idx + 1 < len(headings) and headings[idx + 1][1] == level and headings[idx + 1][2]:
                hits.append((chapter_title, title))
    return hits


#: Every detector, by the name a report and a gate address it under. One registry so a
#: caller cannot know about four of five — which is how the romanization defect ran in
#: two shipped editions while the other checks were being written.
# The three "rendering outside its card" detectors live in `_book_translation_cards`,
# and everything about WHO a book names and how it honours them lives in
# `_book_honorific_defects`. Both are imported here so `DETECTORS` stays the ONE
# registry a caller reads — the whole reason this file has a registry at all.
#
# The imports sit at the BOTTOM because both of those modules read the block and
# chapter helpers from this one. By this line those helpers are defined, so the cycle
# resolves; at the top of the file it would not.
from _book_honorific_defects import (  # noqa: E402
    honorific_overuse,
    honorific_script,
    prophet_wrong_honorific,
    romanized_honorific,
)
from _book_translation_cards import (  # noqa: E402
    translation_fused_with_prose,
    translation_leads_a_paragraph,
    translation_outside_card,
)

DETECTORS = {
    "duplicated-arabic": duplicated_arabic,
    "english-rtl": english_set_right_to_left,
    "romanized-arabic": romanized_arabic,
    "romanized-honorific": romanized_honorific,
    "stray-emphasis": stray_emphasis,
    "quote-line-noise": quote_line_noise,
    "honorific-overuse": honorific_overuse,
    "prophet-wrong-honorific": prophet_wrong_honorific,
    "translation-outside-card": translation_outside_card,
    "translation-leads-a-paragraph": translation_leads_a_paragraph,
    "translation-fused-with-prose": translation_fused_with_prose,
    "bare-arabic": bare_arabic,
    "orphaned-heading": orphaned_heading,
}
