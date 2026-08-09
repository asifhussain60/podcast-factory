#!/usr/bin/env python3
"""The English rendering belongs INSIDE its quotation card — detection and the fold.

Asif reported it on 2026-08-09 from the Book Composer: the verse drew as a card and its
translation printed underneath, outside the panel. It is a CONTENT defect — `book.md`
carries the rendering as the next paragraph of body prose — and every card on the
approved specimen page carries it inside the blockquote.

WHAT THESE TESTS ARE REALLY PROTECTING is the line between the two detectors. Of the 100
live instances, 48 run the rendering straight into the author's own commentary in the
same paragraph. Folding one of those in would carry authorial prose inside a quotation
panel on a religious edition — a worse defect than the one being repaired — so the split
is asserted from both sides, with the real shapes taken out of the books.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_defect_fixes import FIXES, fold_translation_into_card  # noqa: E402
from _book_defects import (  # noqa: E402
    DETECTORS,
    translation_fused_with_prose,
    translation_outside_card,
)

ARABIC = "وَإِنَّكَ لَعَلَىٰ خُلُقٍ عَظِيمٍۢ"


def chapter(*body: str) -> str:
    return "## 1. A Chapter\n\n" + "\n\n".join(body) + "\n"


# ── the repairable shape ─────────────────────────────────────────────────────


def test_a_rendering_stranded_under_its_card_is_found():
    md = chapter("Lead-in:", f"> {ARABIC}", '"Verily, thou art of a tremendous nature" (Al-Qalam: 4).')
    assert translation_outside_card(md) == [
        ("1. A Chapter", '"Verily, thou art of a tremendous nature" (Al-Qalam: 4).')
    ]


def test_the_fold_moves_the_sentence_in_without_changing_a_character():
    rendering = '"It is not the sights that are blind" (Al-Hajj: 46).'
    md = chapter("Lead-in:", f"> {ARABIC}", rendering)
    out, folded = fold_translation_into_card(md)
    assert folded == 1
    assert f"> {ARABIC}\n>\n> {rendering}" in out
    # nothing added, nothing dropped — the same sentence, one level in
    assert out.count(rendering) == 1
    assert translation_outside_card(out) == []


def test_the_fold_is_idempotent():
    md = chapter("Lead-in:", f"> {ARABIC}", '"A rendering." (Al-Qalam: 4)')
    once, first = fold_translation_into_card(md)
    twice, second = fold_translation_into_card(once)
    assert (first, second) == (1, 0)
    assert twice == once


def test_a_rendering_with_no_citation_still_folds():
    md = chapter(f"> {ARABIC}", '"Ali is to me as my own soul."')
    out, folded = fold_translation_into_card(md)
    assert folded == 1
    assert '>\n> "Ali is to me as my own soul."' in out


def test_a_multi_line_rendering_keeps_every_line_inside():
    md = chapter(f"> {ARABIC}", '"The first line of a long rendering\nand its second line" (Al-Baqarah: 2).')
    out, folded = fold_translation_into_card(md)
    assert folded == 1
    assert '> "The first line of a long rendering' in out
    assert '> and its second line" (Al-Baqarah: 2).' in out


# ── the shape that must NEVER be folded ──────────────────────────────────────


def test_a_rendering_that_runs_into_commentary_is_reported_not_repaired():
    """The 48-instance shape. Real text from spiritual-ethos."""
    fused = (
        '"And who despaireth of the mercy of his Lord except those who stray in error?" '
        "(Al-Hijr: 56). The Quran's assurances of mercy come fully alive in souls like his."
    )
    md = chapter(f"> {ARABIC}", fused)
    assert translation_outside_card(md) == []
    assert [t[1] for t in translation_fused_with_prose(md)] == [fused]
    out, folded = fold_translation_into_card(md)
    assert (out, folded) == (md, 0)


def test_an_interjection_between_two_quoted_spans_is_not_repaired():
    """Real text from spiritual-ethos: the author speaks between two halves of a verse."""
    fused = (
        '"And the life of this world is nothing but sport and play," says the Quran, '
        '"and verily, the abode of the Hereafter, that is true life."'
    )
    md = chapter(f"> {ARABIC}", fused)
    assert translation_outside_card(md) == []
    assert len(translation_fused_with_prose(md)) == 1
    assert fold_translation_into_card(md)[1] == 0


def test_a_card_that_already_holds_its_rendering_is_left_alone():
    md = chapter(f'> {ARABIC}\n>\n> "Already inside."')
    assert translation_outside_card(md) == []
    assert translation_fused_with_prose(md) == []
    assert fold_translation_into_card(md)[1] == 0


def test_ordinary_prose_after_a_card_is_not_a_rendering():
    """Only a paragraph opening on a quotation mark is a candidate at all."""
    md = chapter(f"> {ARABIC}", "The Prophet's words give voice to that substance.")
    assert translation_outside_card(md) == []
    assert translation_fused_with_prose(md) == []


def test_a_quotation_with_no_arabic_is_not_a_card():
    md = chapter("> An English pull-quote.", '"A following quotation."')
    assert translation_outside_card(md) == []
    assert fold_translation_into_card(md)[1] == 0


def test_a_card_followed_by_a_heading_is_left_alone():
    md = "## 1. One\n\n> " + ARABIC + '\n\n## 2. Two\n\n"A quotation opening the next chapter."\n'
    assert translation_outside_card(md) == []
    assert fold_translation_into_card(md)[1] == 0


# ── the registries ───────────────────────────────────────────────────────────


def test_both_detectors_are_registered_and_only_one_has_a_repair():
    assert "translation-outside-card" in DETECTORS
    assert "translation-fused-with-prose" in DETECTORS
    assert "translation-outside-card" in FIXES
    assert "translation-fused-with-prose" not in FIXES


def test_the_live_corpus_splits_the_way_the_repair_assumes():
    """A guard on the real books, not a fixture: the fused shape must stay the larger
    half, because that is the evidence for refusing to repair it. If a future edit made
    the repairable pattern greedy enough to swallow those, this is what would notice."""
    repairable = fused = 0
    for book in sorted((REPO / "content").glob("*/*/book/book.md")):
        md = book.read_text(encoding="utf-8")
        repairable += len(translation_outside_card(md))
        fused += len(translation_fused_with_prose(md))
    assert repairable + fused > 0, "no book in the corpus shows the defect — has the shape changed?"
    assert fused >= 40, f"only {fused} fused instances — the pattern may have become greedy"
