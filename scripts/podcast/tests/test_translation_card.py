#!/usr/bin/env python3
"""The English rendering belongs INSIDE its quotation card — detection and the fold.

Asif reported it on 2026-08-09 from the Book Composer: the verse drew as a card and its
translation printed underneath, outside the panel. It is a CONTENT defect — `book.md`
carries the rendering as the next paragraph of body prose — and every card on the
approved specimen page carries it inside the blockquote.

WHAT THESE TESTS ARE REALLY PROTECTING are the two lines between three shapes, because
carrying the author's prose inside a quotation panel on a religious edition would be a
worse defect than the one being repaired:

  FOLD   the paragraph is the rendering and nothing else — it moves in whole.
  SPLIT  the paragraph OPENS on the rendering and continues into a sentence of the
         author's own — the rendering moves in, the sentence stays, and the boundary is
         punctuation he already placed.
  NEVER  what follows is a connective his sentence depends on (`(Al-Araf: 156), and`) or
         an interjection between two halves of one verse. Separating those means WRITING
         something, which is authorship rather than repair.

Every shape below is real text lifted out of the books, and each is asserted from both
sides: the repair that should take it fires, and the ones that should not stay silent.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_defect_fixes import (  # noqa: E402
    FIXES,
    fold_translation_into_card,
    split_translation_into_card,
)
from _book_defects import (  # noqa: E402
    DETECTORS,
    translation_fused_with_prose,
    translation_leads_a_paragraph,
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


# ── the shape that is SPLIT rather than folded ───────────────────────────────


def test_a_rendering_followed_by_a_whole_sentence_is_split_not_folded():
    """Real text from spiritual-ethos. The rendering opens the paragraph and the author's
    own sentence follows it, so the boundary is punctuation he already placed."""
    rendering = '"And who despaireth of the mercy of his Lord except those who stray in error?" (Al-Hijr: 56).'
    gloss = "The Quran's assurances of mercy come fully alive in souls like his."
    md = chapter(f"> {ARABIC}", f"{rendering} {gloss}")
    assert translation_outside_card(md) == []
    assert translation_fused_with_prose(md) == []
    assert [t[1] for t in translation_leads_a_paragraph(md)] == [rendering]
    # the WHOLE-paragraph fold must refuse it — that repair would carry the gloss inside
    assert fold_translation_into_card(md)[1] == 0

    out, split = split_translation_into_card(md)
    assert split == 1
    assert f"> {ARABIC}\n>\n> {rendering}\n\n{gloss}" in out
    assert out.count(gloss) == 1


def test_the_split_is_idempotent():
    md = chapter(f"> {ARABIC}", '"A rendering." (Al-Hijr: 56). And then a sentence of his own.')
    once, first = split_translation_into_card(md)
    twice, second = split_translation_into_card(once)
    assert (first, second) == (1, 0)
    assert twice == once


# ── the shape that must NEVER be touched by either repair ────────────────────


def test_a_dangling_connective_is_never_repaired():
    """The author strung two verses together across two blockquotes. Moving the rendering
    out leaves `, and` — prose that no longer parses, so a repair would have to write."""
    md = chapter(f"> {ARABIC}", '"My mercy encompasseth all things" (Al-Araf: 156), and')
    assert translation_outside_card(md) == []
    assert translation_leads_a_paragraph(md) == []
    assert len(translation_fused_with_prose(md)) == 1
    assert fold_translation_into_card(md)[1] == 0
    assert split_translation_into_card(md)[1] == 0


def test_an_interjection_between_two_quoted_spans_is_not_repaired():
    """Real text from spiritual-ethos: the author speaks between two halves of a verse."""
    fused = (
        '"And the life of this world is nothing but sport and play," says the Quran, '
        '"and verily, the abode of the Hereafter, that is true life."'
    )
    md = chapter(f"> {ARABIC}", fused)
    assert translation_outside_card(md) == []
    assert translation_leads_a_paragraph(md) == []
    assert len(translation_fused_with_prose(md)) == 1
    assert fold_translation_into_card(md)[1] == 0
    assert split_translation_into_card(md)[1] == 0


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
    assert "translation-leads-a-paragraph" in DETECTORS
    assert "translation-fused-with-prose" in DETECTORS
    assert "translation-outside-card" in FIXES
    assert "translation-leads-a-paragraph" in FIXES
    assert "translation-fused-with-prose" not in FIXES


def test_the_live_corpus_splits_the_way_the_repair_assumes():
    """A guard on the real books, not a fixture: the fused shape must stay the larger
    half, because that is the evidence for refusing to repair it. If a future edit made
    the repairable pattern greedy enough to swallow those, this is what would notice."""
    seen = {"fold": 0, "split": 0, "fused": 0}
    for book in sorted((REPO / "content").glob("*/*/book/book.md")):
        md = book.read_text(encoding="utf-8")
        seen["fold"] += len(translation_outside_card(md))
        seen["split"] += len(translation_leads_a_paragraph(md))
        seen["fused"] += len(translation_fused_with_prose(md))
    assert sum(seen.values()) > 0, "no book shows the defect at all — has the shape changed?"
    # The three are mutually exclusive by construction; this is the guard that they stay
    # so, and that the fused bucket never empties into a repair by a pattern going greedy.
    assert seen["fused"] > 0, "nothing is fused any more — a repair pattern has widened"


def test_this_module_can_be_imported_before_book_defects():
    """A circular import that only bites in ONE order, which is why it survived a green
    suite: `_book_defects` imports the three detectors for its registry, so a module-level
    import back is a cycle that resolves when `_book_defects` goes first — as every caller
    and every test above happens to do — and raises ImportError otherwise. Run in a fresh
    interpreter because this one has both modules loaded already."""
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-c", "import _book_translation_cards as T; print(len(T.QUOTE_SHAPES))"],
        cwd=REPO / "scripts" / "podcast",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "3"


# ── nested quotations: the case that cut a verse in half ─────────────────────

NESTED = (
    "'And when thy Lord brought forth from the children of Adam, from their loins, "
    'their seed, and made them testify against their souls [saying], "Am I not your '
    'Lord?" They said, "Yea, we testify"\' (Al-Araf: 172).'
)


def test_a_verse_quoting_speech_inside_it_is_one_rendering():
    """Al-Araf 172 in Spiritual Ethos: single-quoted, with God's speech in double quotes
    INSIDE it. Taking simply the next mark stopped at that inner quote, and because the
    remainder began on a capital ("Am") it passed the sentence test and was SPLIT there —
    half the verse in the card, half outside. Caught 2026-08-09 by a prose-invariance
    check after the run, and reverted."""
    md = chapter(f"> {ARABIC}", NESTED)
    # the whole verse is the rendering: it folds, it never splits
    assert [t[1] for t in translation_outside_card(md)] == [NESTED]
    assert translation_leads_a_paragraph(md) == []
    assert translation_fused_with_prose(md) == []
    out, folded = fold_translation_into_card(md)
    assert folded == 1
    assert out.count("Am I not your Lord?") == 1
    assert split_translation_into_card(md)[1] == 0


def test_the_inner_quotation_survives_the_fold_intact():
    md = chapter(f"> {ARABIC}", NESTED)
    out, _ = fold_translation_into_card(md)
    assert f"> {NESTED}" in out


# ── the single-quoted style reads by the same rules ──────────────────────────


def test_a_single_quoted_rendering_folds_like_a_double_quoted_one():
    """Four cards in chapter 2 of Spiritual Ethos sat with no English at all because the
    rule only accepted double quotes — found by reading what the Library had stored."""
    rendering = "'Say: I ask you for no reward, save love of the near of kin' (Ash-Shura: 23)."
    md = chapter(f"> {ARABIC}", rendering)
    assert [t[1] for t in translation_outside_card(md)] == [rendering]
    assert fold_translation_into_card(md)[1] == 1


def test_an_apostrophe_inside_a_word_is_not_a_quotation_mark():
    rendering = "'God's mercy encompasseth all that the Prophet's people sought' (Al-Araf: 156)."
    md = chapter(f"> {ARABIC}", rendering)
    assert [t[1] for t in translation_outside_card(md)] == [rendering]


def test_a_single_quoted_rendering_splits_when_a_sentence_follows():
    rendering = "'Truly man is rebellious, in that he deemeth himself independent' (Al-Alaq: 6-7)."
    gloss = "The conscience is what answers that rebellion."
    md = chapter(f"> {ARABIC}", f"{rendering} {gloss}")
    assert [t[1] for t in translation_leads_a_paragraph(md)] == [rendering]
    out, split = split_translation_into_card(md)
    assert split == 1
    assert f"> {rendering}\n\n{gloss}" in out


def test_an_unclosed_quotation_is_refused_rather_than_guessed():
    """How the same Al-Araf 172 passage is actually printed: it opens on a single mark and
    never closes one. Where the author's punctuation does not say where the quotation ends,
    neither can the tool — it falls through to the shape a person resolves."""
    unclosed = (
        "'And when thy Lord brought forth from the children of Adam their seed, "
        '[saying], "Am I not your Lord?" They said, "Yes, verily, we testify." '
        '[This was] lest ye say, "Truly, of this we were unaware" (Al-Araf: 172). '
        "The moment He created them He made them witness His glory."
    )
    md = chapter(f"> {ARABIC}", unclosed)
    assert translation_outside_card(md) == []
    assert translation_leads_a_paragraph(md) == []
    assert len(translation_fused_with_prose(md)) == 1
    assert fold_translation_into_card(md)[1] == 0
    assert split_translation_into_card(md)[1] == 0
