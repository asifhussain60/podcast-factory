#!/usr/bin/env python3
"""Five reading-edition defects the post-articulation route lets through (2026-08-09).

Asif found every one of them BY EYE in a shipped edition, which is the failure each
records: the student-reader pass reads each chapter after articulation and flagged none
of them. They are executable here so the next book cannot introduce them silently.

THREE OF THE FIVE NOW STAND AT ZERO across every book — see `KNOWN` for how each was
cured. Their gates assert zero rather than carrying a ceiling, which makes each one
end-to-end proof, over real content, that its fix holds.

  DUPLICATED ARABIC       a lead-in gives an Arabic quotation inline and the blockquote
                          under it repeats the identical run — the same words twice in
                          two consecutive lines. One instance, repaired in the Composer.

  PROPHET'S HONORIFIC     the Prophet carrying `(ع)`, the honorific of the Imams —
                          `The Messenger of Allah (ع)`, 52 times in one book. Wrong under
                          any reading of the convention, so it did not wait on the cap
                          policy. 130 repaired; his own ligature now stands in its place.

  ENGLISH SET RIGHT-TO-LEFT
                          FIXED at the renderer 2026-08-09, and this file is now the
                          proof over real content. Both renderers used to classify a
                          quotation line as Arabic if it CONTAINED one Arabic character,
                          so an English sentence carrying `(ع)` — or an editorial note
                          naming a root like `ح-س-ن` — was set in the Arabic face with
                          its quotation marks thrown to the wrong ends. Five instances
                          across three books, the worst 626 Latin characters flipped by
                          three Arabic ones. The rule now weighs which script the line
                          is MOSTLY in, which repaired all five with no re-compose.

  ROMANIZED ARABIC        a whole Arabic sentence printed in the English character set.
                          Asif's rule of 2026-08-02 — quoted verbatim in
                          `_book_inline_arabic` — is that book.md carries zero English
                          transliteration of Arabic "terms, words, paragraphs,
                          sentences, etc.". `_book_substitution` implements it for
                          glossary TERMS only, gated on a term being classed `teach`, so
                          a whole SENTENCE matches nothing and 14 of them run in two
                          shipped editions.

  HONORIFIC OVERUSE       `(ع)` after every occurrence of every name — 54 in one chapter
                          of Spiritual Ethos, 78 unattributed in one chapter of
                          Mukhtasar 2. Capped at once per figure per chapter (Asif,
                          2026-08-09). The Prophet's is deliberately not counted: his is
                          mandatory rather than capped, so counting it would report the
                          convention working as though it were the defect.

HOW THIS FILE IS ARRANGED, AND WHY

  The detectors themselves live in `_book_defects`, not here. Three callers need the
  same answer — this file, the compose review gate, and the `pf-compose-fix` skill — and
  a private copy is how two of them start disagreeing about what a defect is.

  A LIVE test per defect runs over every book, ceilinged by `KNOWN`. That registry is
  now EMPTY — every defect stands at zero — so each gate asserts zero and is end-to-end
  proof over real content that its fix holds. A new instance, from a compose or an edit,
  turns one of them red. `KNOWN` exists for the next defect recorded before it is fixed,
  not as a list that rots.

  Nothing in this file mutates content.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_defects import (  # noqa: E402
    duplicated_arabic,
    english_set_right_to_left,
    honorific_overuse,
    is_arabic_quote_line,
    is_romanized_arabic,
    orphaned_heading,
    prophet_wrong_honorific,
    romanized_arabic,
)

# Overridable so these gates can be FALSIFIED against a scratch copy of a book rather
# than against `content/` itself — the same escape the compose-lane gates use.
CONTENT = Path(os.environ.get("PODCAST_CONTENT_ROOT") or REPO / "content")

#: The fixtures that pin the quotation-line rule against the two renderers.
QUOTE_LINE_FIXTURES = REPO / "plan-dashboard" / "scripts" / "lib" / "arabic-quote-line.fixtures.json"


def _books() -> list[Path]:
    found = sorted(CONTENT.glob("*/*/book/book.md")) + sorted(CONTENT.glob("*/*/*/book/book.md"))
    return [p for p in found if p.is_file()]


BOOKS = _books()
IDS = ["/".join(p.relative_to(CONTENT).parts[:-2]) for p in BOOKS]


#: What stands TODAY, by book. Each non-zero entry is an expected failure below.
#:
#: `romanized` counts sentences; `honorific` counts (chapter, figure) pairs that exceed
#: one use per chapter — NOT raw honorifics, which run into the hundreds. Neither can be
#: repaired without editing prose, and Asif's instruction of 2026-08-09 stands: no book
#: goes back through the pipeline for now. So they are recorded, not fixed.
KNOWN: dict[str, dict[str, int]] = {
    # EMPTY, and that is the point: all five defects now stand at zero across every book,
    # so every gate above asserts zero rather than carrying a ceiling. Each is therefore
    # end-to-end proof, over real content, that its fix holds — and each goes red the
    # moment a compose or an edit reintroduces the defect.
    #
    #   english-rtl      a RENDERER defect, not a content one. Weighing which script a
    #                    line is mostly in repaired all five instances across three books.
    #   duplicated       one instance, repaired in the Book Composer.
    #   romanized        14 sayings across two books, put back into Arabic script by
    #                    `_book_romanization`'s ladder: nine confirmed against sourced
    #                    wordings, five rendered from the transliteration the book itself
    #                    printed. Every one agrees with those consonants.
    #   prophet          130 mentions across six books; the Prophet now carries his own
    #                    ligature instead of the Imams' honorific.
    #   honorific        1,674 compact honorifics down to 327 — once per figure per
    #                    chapter (Asif, 2026-08-09).
    #
    # `orphaned-heading`, added 2026-08-14: five instances found in
    # `Sessions/surah-al-fateha` (a heading whose own intro sentence was misfiled
    # under its first child, plus three empty divider labels and one blank heading
    # marker) were corrected through the Book Composer the same day, so that book
    # carries no ceiling. Two more of the same shape, in a translation edition
    # rather than a Sessions-lane hand-off, were left as recorded debt — a
    # different cause, not investigated as part of this sweep.
    "Islamic/mukhtasar-ul-asar-2": {"orphaned-heading": 2},
}


def _known(book_id: str, key: str) -> int:
    return KNOWN.get(book_id, {}).get(key, 0)


def _book_id(book: Path) -> str:
    return "/".join(book.relative_to(CONTENT).parts[:-2])


# ── live gates: pass today, fail on anything NEW ─────────────────────────────


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_duplicated_arabic(book: Path) -> None:
    hits = duplicated_arabic(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "duplicated")
    assert len(hits) <= allowed, (
        f"{len(hits)} blockquote(s) repeat Arabic their lead-in already gave, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {r[:40]}" for t, r in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_english_set_right_to_left(book: Path) -> None:
    hits = english_set_right_to_left(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "rtl")
    assert len(hits) <= allowed, (
        f"{len(hits)} translation paragraph(s) will render right-to-left in the Arabic "
        f"face, {allowed} recorded: " + "; ".join(f"{t}: {p[:40]}" for t, p in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_romanized_arabic(book: Path) -> None:
    hits = romanized_arabic(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "romanized")
    assert len(hits) <= allowed, (
        f"{len(hits)} Arabic sentence(s) printed in the English character set, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {r[:40]}" for t, r in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_honorific_overuse(book: Path) -> None:
    hits = honorific_overuse(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "honorific")
    assert len(hits) <= allowed, (
        f"{len(hits)} figure(s) carry a compact honorific more than once in a chapter, "
        f"{allowed} recorded: " + "; ".join(f"{t}/{f}×{n}" for t, f, n in hits[:5])
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_prophet_wrong_honorific(book: Path) -> None:
    hits = prophet_wrong_honorific(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "prophet")
    assert len(hits) <= allowed, (
        f"{len(hits)} mention(s) give the Prophet a honorific that is not his, "
        f"{allowed} recorded: " + "; ".join(m for _, m in hits[:5])
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_orphaned_heading(book: Path) -> None:
    hits = orphaned_heading(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "orphaned-heading")
    assert len(hits) <= allowed, (
        f"{len(hits)} heading(s) carry no body of their own before the next heading, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {h[:40]}" for t, h in hits[:5])
    )


def test_is_arabic_quote_line_matches_the_shared_fixtures() -> None:
    """The Python leg of the quotation-line mirror.

    The two renderers are pinned to each other by `arabic-quote-line.test.mjs`; this is
    the third copy reading the SAME fixtures, so a rule change has to move all three or
    fail here.
    """
    cases = json.loads(QUOTE_LINE_FIXTURES.read_text(encoding="utf-8"))["cases"]
    assert cases, "fixture file is empty"
    for case in cases:
        assert is_arabic_quote_line(case["text"]) is case["arabic"], case["why"]


# ── the detectors themselves must be able to fail ────────────────────────────


class TestTheDetectorsWork:
    """A gate nobody has seen fail is a gate nobody should trust."""

    def test_duplication_is_detected(self) -> None:
        md = '## One\n\nHe said "as my own soul (عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي)":\n\n> عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي\n'
        assert len(duplicated_arabic(md)) == 1

    def test_the_correct_shape_is_not_flagged(self) -> None:
        md = "## One\n\nHe said, and the words are these:\n\n> أنْتَ مِنِّی وَ أَنَا مِنْکَ\n"
        assert duplicated_arabic(md) == []

    def test_a_short_glossed_term_is_not_flagged(self) -> None:
        md = "## One\n\nThe gate (بَاب) opens.\n\n> بَاب\n"
        assert duplicated_arabic(md) == []

    def test_the_honorific_no_longer_flips_the_translation(self) -> None:
        # The exact passage Asif photographed. Under the old rule the English line was
        # classified Arabic because of the single (ع); under the new one it is a
        # translation, so nothing is reported.
        md = (
            "## One\n\nHe said:\n\n"
            "> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n>\n"
            '> "Ali is with the Quran and the Quran is with Ali (ع). They will not separate."\n'
        )
        assert english_set_right_to_left(md) == []

    def test_a_mostly_arabic_line_is_still_arabic(self) -> None:
        # The fix must not demote real Arabic: a short quotation has few characters and
        # would fail an absolute threshold, which is why the rule is proportional.
        assert is_arabic_quote_line("بَاب") is True
        assert is_arabic_quote_line("إِنَّ عَلِيًّا مَعَ الْقُرْآنِ") is True

    def test_a_pure_arabic_blockquote_is_not_flagged(self) -> None:
        md = "## One\n\nHe said:\n\n> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n"
        assert english_set_right_to_left(md) == []

    def test_the_sentence_asif_photographed_is_detected(self) -> None:
        md = (
            '## One\n\nThe epigraph names it: "I am the city of knowledge and Ali (ع) is '
            "its gate\" (Ana madinatul-ilm wa 'Ali babuha; Fa-man aradal-ilm fal-yatil-bab).\n"
        )
        hits = romanized_arabic(md)
        assert len(hits) == 1 and hits[0][1].startswith("Ana madinatul-ilm")

    def test_a_persons_name_is_never_reported_as_romanized(self) -> None:
        # The false positive that the first draft produced on Kitab al-Riyad. A name
        # stays romanized by the annotation policy; substituting one would be a defect.
        assert is_romanized_arabic("al-Numan ibn Muhammad ibn Hayyun al-Maghribi") is False

    def test_english_prose_in_brackets_is_not_romanized_arabic(self) -> None:
        assert is_romanized_arabic("the argument of the chapter, which is that") is False
        assert is_romanized_arabic("a narrow approach to the material") is False

    def test_a_single_glossed_term_is_left_to_the_annotation_policy(self) -> None:
        # One or two romanized words are a TERM. Which terms carry an inline annotation
        # is the annotation policy's decision, and this check must not reach into it.
        assert is_romanized_arabic("mawaddah") is False
        assert is_romanized_arabic("nafi al-jins") is False

    def test_arabic_script_is_never_reported_as_romanized(self) -> None:
        assert is_romanized_arabic("أنا مدينة العلم وعليٌّ بابها") is False

    # ---- The saying's own script beside the bracket (Asif, 2026-08-09) --------------
    #
    # Eleven passages in Spiritual Ethos sat one word-list hit under the bar for months,
    # including the one he photographed — `(anta minni wa ana minka)`, whose Arabic is
    # the display line immediately beneath it, and which the whole-book romanization pass
    # rewrote the surrounding chapter without touching. Adjacent script is the strongest
    # evidence available that a bracket holds a saying, so it stands in for the second
    # hit. Lowering the bar to one hit instead returns 58 findings across the seven
    # books, 47 of them blessings, citations and glossed terms.

    def test_one_marker_is_enough_when_the_arabic_stands_beside_it(self) -> None:
        assert is_romanized_arabic("anta minni wa ana minka") is False
        assert is_romanized_arabic("anta minni wa ana minka", arabic_beside=True) is True

    def test_one_marker_alone_is_still_not_enough(self) -> None:
        # Without the script beside it the word list is all there is, and one hit is
        # exactly what the English in this corpus produces by accident.
        md = "## One\n\nHe said it plainly (anta minni wa ana minka).\n"
        assert romanized_arabic(md) == []

    def test_the_photographed_sentence_is_detected(self) -> None:
        md = (
            '## One\n\nThe Prophet said to Ali, "You are from me, and I am from you '
            '(anta minni wa ana minka)":\n\n> أنْتَ مِنِّی وَ أَنَا مِنْکَ\n'
        )
        hits = romanized_arabic(md)
        assert [h[1] for h in hits] == ["anta minni wa ana minka"], hits

    def test_an_english_possessive_is_not_arabic_evidence(self) -> None:
        # `'s` counted as a transliterated hamza, so every `(may Allah's blessings be
        # upon him)` in Mukhtasar ul-Asar — forty of them, each beside real Arabic —
        # scored as a romanized sentence the moment adjacency counted.
        md = "## One\n\n> رَبَّنَا\n\nThe Prophet (may Allah's blessings be upon him) said.\n"
        assert romanized_arabic(md) == []

    def test_an_opening_quote_before_an_english_word_is_not_a_hamza(self) -> None:
        # The apostrophe rule is for `ta'wil`, always lower-case after. Compiled
        # case-insensitively it also matched `('Glory to me')`.
        md = "## One\n\n> سُبْحَانِي\n\nHe cried out ('Glory to me') in that state.\n"
        assert romanized_arabic(md) == []
        assert is_romanized_arabic("ta'wil of the verse", arabic_beside=True) is False

    def test_a_verse_citation_is_never_a_saying(self) -> None:
        # Every book cites in this shape, and the surah name is transliterated Arabic.
        md = "## One\n\n> رَبَّنَا\n\nThe verse is plain (Surah al-Talaq, 65:1) on the point.\n"
        assert romanized_arabic(md) == []

    def test_a_wholly_italic_bracket_is_a_term_gloss(self) -> None:
        # The books' own mark for a technical term. Which terms carry an annotation is
        # the annotation policy's decision, not this check's.
        md = "## One\n\n> رَبَّنَا\n\nThe forbidden sale (*ribh ma lam yudman*) is named.\n"
        assert romanized_arabic(md) == []

    def test_honorific_overuse_is_detected_and_capped_per_chapter(self) -> None:
        md = "## One\n\nAli (ع) said. Later Ali (ع) said again.\n\n## Two\n\nAli (ع) said once.\n"
        hits = honorific_overuse(md)
        assert hits == [("One", "Ali", 2)], hits

    def test_the_prophets_ligature_is_not_counted_as_overuse(self) -> None:
        # His is mandatory rather than capped (Asif, 2026-08-09), so counting it here
        # would report the convention working as though it were the defect.
        md = "## One\n\nThe Prophet Muhammad ﷺ said. Again the Prophet Muhammad ﷺ said.\n"
        assert honorific_overuse(md) == []

    def test_the_prophet_carrying_someone_elses_honorific_is_detected(self) -> None:
        md = "## One\n\nThe Messenger of Allah (ع) said, and the Prophet (ع) confirmed it.\n"
        assert len(prophet_wrong_honorific(md)) == 2

    def test_an_imam_named_muhammad_keeps_his_own_honorific(self) -> None:
        # The reason the rule matches how the edition NAMES the Prophet rather than the
        # bare word: this corpus also carries Jafar ibn Muhammad and Abu Jafar Muhammad
        # ibn Ali, for whom `(ع)` is correct.
        md = "## One\n\nAl-Sadiq Jafar ibn Muhammad (ع) said, and Abu Jafar Muhammad ibn Ali (ع) agreed.\n"
        assert prophet_wrong_honorific(md) == []

    def test_the_prophets_own_ligature_is_not_a_wrong_honorific(self) -> None:
        assert prophet_wrong_honorific("## One\n\nThe Messenger of Allah ﷺ said.\n") == []

    def test_the_photographed_pair_is_detected(self) -> None:
        # The exact shape found in Surah Al-Fateha: an empty topic-label heading
        # directly above its would-be first child, same level, nothing between.
        md = "## One\n\n### Meanings Of Word ILAH\n\n### YALAA\n\nThe word carries several meanings.\n"
        hits = orphaned_heading(md)
        assert hits == [("One", "Meanings Of Word ILAH")], hits

    def test_a_blank_heading_marker_is_detected(self) -> None:
        md = "## One\n\nSome prose.\n\n###\n\n## Two\n\nMore prose.\n"
        hits = orphaned_heading(md)
        assert hits == [("One", "blank heading marker (###)")], hits

    def test_a_heading_with_its_own_body_is_not_flagged(self) -> None:
        md = "## One\n\n### First\n\nIt has a paragraph.\n\n### Second\n\nSo does this one.\n"
        assert orphaned_heading(md) == []

    def test_a_chapter_diving_straight_into_its_first_subsection_is_not_flagged(self) -> None:
        # Parent immediately followed by child (## then ###) is ordinary book
        # structure — over a third of this book's own chapters open this way.
        md = "## One\n\n### First Subsection\n\nText here.\n"
        assert orphaned_heading(md) == []
