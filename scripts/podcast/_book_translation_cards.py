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

from _book_defects import blocks, chapters, is_arabic_quote_line, quote_paragraphs

#: The paragraph is the rendering AND NOTHING ELSE: it opens on a quotation mark, closes
#: on one, may carry a citation, and holds EXACTLY ONE quoted span. That last clause is
#: what makes the whole-paragraph fold safe — without it, `"…sport and play," says the
#: Quran, "and verily…"` would fold the author's interjection into the card with it.
ONLY_THE_RENDERING_RE = re.compile(r'^["“][^"“”]+["”]\s*(\([^)]*\))?\s*\.?\s*$')

#: A rendering at the head of a paragraph: the quoted span, then its citation, then the
#: sentence-ending period the author wrote. Everything after the match is his own prose.
_LEADING_RENDERING_RE = re.compile(r'^(["“][^"“”]*["”]\s*(?:\([^)]*\))?\s*\.?)\s*(.*)$', re.S)

#: What must be true of the remainder for the split to decide nothing: it has to stand as
#: a sentence. Deliberately BLUNT — a capital and at least four words. A cleverer rule
#: would start reaching for the cases below it, and the cost of being wrong there is an
#: author's words sitting inside a quotation panel in a religious text.
_MIN_SENTENCE_WORDS = 4


def cards_missing_their_rendering(md: str):
    """(chapter, quotation lines, following paragraph) for every stranded rendering.

    The shape all three detectors share: a blockquote holding ONLY Arabic — so it has no
    English inside it — immediately followed by a paragraph that opens on a quotation
    mark. Read once here so the three cannot disagree about what they are classifying.
    """
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
            if not text.startswith('"') and not text.startswith("“"):
                continue
            yield title, lines, text


def split_rendering_from_gloss(text: str) -> tuple[str, str] | None:
    """(rendering, the author's sentence) when the paragraph opens on one and continues
    into the other — otherwise None.

    None is the answer for both of the other two shapes, which is what makes this one
    function the boundary: `translation_leads_a_paragraph` fires when it returns a pair,
    `translation_fused_with_prose` fires when it does not and the fold does not either.
    """
    match = _LEADING_RENDERING_RE.match(text)
    if not match:
        return None
    rendering, rest = match.group(1).strip(), match.group(2).strip()
    if not rest or not rest[0].isupper() or len(rest.split()) < _MIN_SENTENCE_WORDS:
        return None
    return rendering, rest


def translation_outside_card(md: str) -> list[tuple[str, str]]:
    """(chapter, rendering) where the English belongs in the card and can simply move."""
    return [(title, text) for title, _, text in cards_missing_their_rendering(md) if ONLY_THE_RENDERING_RE.match(text)]


def translation_leads_a_paragraph(md: str) -> list[tuple[str, str]]:
    """(chapter, rendering) where the rendering opens the paragraph and a sentence follows."""
    return [
        (title, split_rendering_from_gloss(text)[0])
        for title, _, text in cards_missing_their_rendering(md)
        if not ONLY_THE_RENDERING_RE.match(text) and split_rendering_from_gloss(text)
    ]


def translation_fused_with_prose(md: str) -> list[tuple[str, str]]:
    """(chapter, paragraph) where the rendering cannot be separated without rewording."""
    return [
        (title, text)
        for title, _, text in cards_missing_their_rendering(md)
        if not ONLY_THE_RENDERING_RE.match(text) and not split_rendering_from_gloss(text)
    ]
