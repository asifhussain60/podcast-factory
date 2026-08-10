#!/usr/bin/env python3
"""_book_translation_cards.py — the English rendering that prints outside its card.

Asif reported it on 2026-08-09 from the Book Composer: a verse drew as a quotation card
and its translation printed underneath, outside the panel. It is a CONTENT defect —
`book.md` carries the rendering as the next paragraph of body prose — and every card on
the approved specimen page (`_specimen-quote-tiers.html`) carries its rendering inside
the blockquote. There were 100 of them across the seven reading editions.

ITS OWN MODULE, not three more functions in `_book_defects`, for the reason that file
gives about itself: it holds detectors, and this one needs a shared reading of a
markdown shape plus the two boundary rules that decide which of three things a given
instance is. `_book_defects` re-exports all three so `DETECTORS` stays the one registry
a caller reads, and `_book_defect_fixes` imports the boundary rules so the repair and the
check can never disagree about where a rendering ends.

THREE SHAPES, AND THE LINES BETWEEN THEM ARE THE WHOLE POINT. Carrying the author's own
prose inside a quotation panel on a religious edition would be a worse defect than the
one being repaired, so each line is drawn where the repair stops being a MOVE and starts
being authorship:

  translation-outside-card       the paragraph is the rendering and nothing else. It
                                 folds in whole. Nothing is decided.

  translation-leads-a-paragraph  the paragraph OPENS on the rendering and continues into
                                 a sentence of the author's own. The rendering moves in,
                                 the sentence stays. The boundary is punctuation HE
                                 already placed.

  translation-fused-with-prose   what follows is not a sentence — it is a connective his
                                 sentence depends on (`(Al-Araf: 156), and`, where two
                                 verses are strung across two blockquotes), or an
                                 interjection between two halves of one verse. Moving the
                                 rendering out leaves prose that no longer parses, so a
                                 repair would have to WRITE something. Left for a person.

Nothing here mutates a book; the repairs live in `_book_defect_fixes`.
"""

from __future__ import annotations

import re

#: BOTH quotation styles, because the corpus uses both and reading only one is how four
#: cards in chapter 2 of Spiritual Ethos sat with no English at all while the check called
#: the chapter clean (found 2026-08-09 by looking at what the Library had actually stored).
#: `'God only wisheth to remove from you all impurity…' (Al-Ahzab: 33)` is the same defect
#: as its double-quoted neighbour and has to be read as one.
_QUOTATION_MARKS = "\"“”'‘’"

#: What may follow the closing mark and still belong to the quotation: its citation, and
#: the period that ends the sentence the author built around it.
_CITATION_TAIL = r"\s*(?:\([^)]*\))?\s*[.,]?"

#: What must be true of the remainder for a split to decide nothing: it has to stand as a
#: sentence. Deliberately BLUNT — a capital and at least four words. A cleverer rule would
#: start reaching for the shapes it must never touch, and the cost of being wrong there is
#: an author's words sitting inside a quotation panel in a religious text.
_MIN_SENTENCE_WORDS = 4


def quotation_marks(text: str) -> list[int]:
    """Where the quotation marks are — an apostrophe INSIDE a word is not one.

    Single quotes carry both jobs in English, so `'God only wisheth…'` opens and closes a
    quotation while `God's` and `the Prophet's` do not. A mark flanked by letters on both
    sides is an apostrophe; anything else is a mark. That distinction is what lets the
    single-quoted style be read with the same rules as the double-quoted one instead of a
    parallel set that would drift.
    """
    marks: list[int] = []
    for index, char in enumerate(text):
        if char not in _QUOTATION_MARKS:
            continue
        if char in "'‘’":
            before = text[index - 1] if index else ""
            after = text[index + 1] if index + 1 < len(text) else ""
            if before.isalpha() and after.isalpha():
                continue  # God's, wouldn't, Prophet's
        marks.append(index)
    return marks


def opens_on_a_quotation(text: str) -> bool:
    """The paragraph begins on a quotation mark — the precondition for all three shapes."""
    return bool(text) and text[0] in _QUOTATION_MARKS


def _closing_mark(text: str) -> int | None:
    """Where the quotation the paragraph OPENS with actually closes, or None.

    THE MARK MUST BE OF THE SAME FAMILY AS THE OPENER — single closes single, double
    closes double — and getting that wrong cut a verse in half. Spiritual Ethos renders
    Al-Araf 172 in single quotes with God's speech quoted in double ones INSIDE it:

        'And when thy Lord brought forth … [saying], "Am I not your Lord?" They said …'

    Taking simply the next mark stopped at that inner `"`, and because the remainder began
    on a capital ("Am") it passed the sentence test and was split there — half the verse in
    the card, half outside. Matching families instead makes the whole verse ONE rendering,
    with its inner quotation carried along inside it, which is what it is.

    RETURNING None ON AN UNCLOSED QUOTATION IS THE POINT, not a gap. That same passage as
    the book actually prints it opens on `'` and never closes one — the verse ends on a
    double mark. Where the author's own punctuation does not say where the quotation ends,
    neither can this, so the instance falls through to `translation_fused_with_prose` and
    waits for a person. Refusing is always available; guessing is not.
    """
    if not opens_on_a_quotation(text):
        return None
    single = text[0] in "'‘’"
    for index in quotation_marks(text)[1:]:
        if (text[index] in "'‘’") == single:
            return index
    return None


def only_the_rendering(text: str) -> bool:
    """The paragraph is the rendering AND NOTHING ELSE.

    Nothing after its closing mark but a citation and a full stop. Marks INSIDE it are
    fine — a verse may quote speech — but the mark that closes it has to be the last thing
    on the line. That is what still stops `"…sport and play," says the Quran, "and
    verily…"` from folding the author's aside into the card: the quotation closes after
    `play,` and his words follow it.
    """
    closing = _closing_mark(text)
    return closing is not None and re.fullmatch(_CITATION_TAIL, text[closing + 1 :]) is not None


#: The three shapes, in the order the module docstring explains them. Exported so a
#: caller — and the import-order test — can name them without retyping the strings.
QUOTE_SHAPES = (
    "translation-outside-card",
    "translation-leads-a-paragraph",
    "translation-fused-with-prose",
)


def cards_missing_their_rendering(md: str):
    """(chapter, quotation lines, following paragraph) for every stranded rendering.

    The shape all three detectors share: a blockquote holding ONLY Arabic — so it has no
    English inside it — immediately followed by a paragraph that opens on a quotation
    mark. Read once here so the three cannot disagree about what they are classifying.

    THE IMPORT IS DEFERRED, AND IT HAS TO BE. `_book_defects` imports the three detectors
    from this module to build its registry, so a module-level import back would be a
    cycle — one that resolves fine when `_book_defects` is imported first (which is what
    every caller and every test happened to do) and raises ImportError the moment anything
    imports THIS module first. Deferring it here breaks the cycle at the only place it can
    be broken without moving the block readers out of the module that owns them.
    `tests/test_translation_card.py` imports this module first in a fresh interpreter.
    """
    from _book_defects import blocks, chapters, is_arabic_quote_line, quote_paragraphs

    for title, body in chapters(md):
        blks = blocks(body)
        for index, (kind, lines) in enumerate(blks):
            if kind != "quote":
                continue
            paras = quote_paragraphs(lines)
            if not paras or not all(is_arabic_quote_line(p) for p in paras):
                continue
            following = blks[index + 1] if index + 1 < len(blks) else None
            if not following or following[0] != "para":
                continue
            text = " ".join(line.strip() for line in following[1]).strip()
            if not opens_on_a_quotation(text):
                continue
            yield title, lines, text


def split_rendering_from_gloss(text: str) -> tuple[str, str] | None:
    """(rendering, the author's sentence) when the paragraph opens on one and continues
    into the other — otherwise None.

    None is the answer for both of the other two shapes, which is what makes this one
    function the boundary: `translation_leads_a_paragraph` fires when it returns a pair,
    `translation_fused_with_prose` fires when it does not and the fold does not either.

    The rendering ends at the FIRST closing mark, plus whatever citation and full stop the
    author put after it. A later quotation in the remainder is his own — chapter 5 of
    Spiritual Ethos introduces a second saying that way — and it stays outside.
    """
    closing = _closing_mark(text)
    if closing is None:
        return None
    tail = re.match(_CITATION_TAIL, text[closing + 1 :])
    cut = closing + 1 + (tail.end() if tail else 0)
    rendering, rest = text[:cut].strip(), text[cut:].strip()
    if not rest or not rest[0].isupper() or len(rest.split()) < _MIN_SENTENCE_WORDS:
        return None
    return rendering, rest


def translation_outside_card(md: str) -> list[tuple[str, str]]:
    """(chapter, rendering) where the English belongs in the card and can simply move."""
    return [(title, text) for title, _, text in cards_missing_their_rendering(md) if only_the_rendering(text)]


def translation_leads_a_paragraph(md: str) -> list[tuple[str, str]]:
    """(chapter, rendering) where the rendering opens the paragraph and a sentence follows."""
    return [
        (title, split_rendering_from_gloss(text)[0])
        for title, _, text in cards_missing_their_rendering(md)
        if not only_the_rendering(text) and split_rendering_from_gloss(text)
    ]


def translation_fused_with_prose(md: str) -> list[tuple[str, str]]:
    """(chapter, paragraph) where the rendering cannot be separated without rewording."""
    return [
        (title, text)
        for title, _, text in cards_missing_their_rendering(md)
        if not only_the_rendering(text) and not split_rendering_from_gloss(text)
    ]
