#!/usr/bin/env python3
"""The `pf-compose-fix` engine: chapter addressing, the repairs, and what it refuses.

Two things are worth more than the rest of this file:

  THE RESOLVER. Every other tool in this pipeline BANS printed chapter numbers, because
  the introduction is an unnumbered section and counting sections makes "chapter 3" land
  on section 4. This one accepts them by reading the number off the heading, which is a
  different operation — and the tests below are what keep it different. A resolver that
  quietly falls back to counting would rewrite the wrong chapter of a finished book.

  IDEMPOTENCE. Each repair runs on prose that a later run will see again, so a repair
  that is not idempotent doubles its own damage. Every one is asserted twice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_defect_fixes import (  # noqa: E402
    PROPHET_LIGATURE,
    cap_honorifics,
    drop_duplicated_inline_arabic,
    use_prophet_ligature,
)
from _book_defects import duplicated_arabic, honorific_overuse, prophet_wrong_honorific  # noqa: E402
from compose_fix import ChapterError, chapter_index, select_chapters  # noqa: E402

#: The shape every book in the corpus has: one unnumbered introduction, then numbered
#: chapters. Verified across all seven reading editions on 2026-08-09.
BOOK = (
    "# Title\n\n"
    "## Introduction to the Book\n\nOpening words.\n\n"
    "## 1. In the Prophet's Shadow\n\nFirst chapter.\n\n"
    "## 2. The People of the House\n\nSecond chapter.\n\n"
    "## 3. Intellect, Not Reason\n\nThird chapter.\n"
)


class TestChapterAddressing:
    def test_the_introduction_has_no_number_and_does_not_consume_one(self) -> None:
        index = chapter_index(BOOK)
        assert index[0]["number"] is None
        assert [c["number"] for c in index] == [None, 1, 2, 3]

    def test_chapter_three_is_the_one_printed_three_not_the_third_section(self) -> None:
        """The whole reason this resolver is allowed to take numbers.

        Section 3 is "The People of the House". Chapter 3 is "Intellect, Not Reason".
        A resolver that counted would rewrite the wrong chapter.
        """
        picked = select_chapters(chapter_index(BOOK), "3")
        assert [c["heading"] for c in picked] == ["3. Intellect, Not Reason"]

    def test_several_numbers_and_a_range(self) -> None:
        index = chapter_index(BOOK)
        assert [c["number"] for c in select_chapters(index, "1,3")] == [1, 3]
        assert [c["number"] for c in select_chapters(index, "2-3")] == [2, 3]

    def test_all_includes_the_unnumbered_introduction(self) -> None:
        assert len(select_chapters(chapter_index(BOOK), "all")) == 4

    def test_the_introduction_is_reachable_only_by_name(self) -> None:
        picked = select_chapters(chapter_index(BOOK), "Introduction")
        assert [c["heading"] for c in picked] == ["Introduction to the Book"]

    def test_a_number_the_book_does_not_have_is_refused(self) -> None:
        with pytest.raises(ChapterError, match="no chapter 9"):
            select_chapters(chapter_index(BOOK), "9")

    def test_an_ambiguous_title_is_refused_rather_than_guessed(self) -> None:
        with pytest.raises(ChapterError, match="matches 3 chapters"):
            select_chapters(chapter_index(BOOK), "The")

    def test_a_book_that_numbers_two_chapters_the_same_is_refused(self) -> None:
        """The one shape that makes a printed number stop identifying a chapter.

        No book in the corpus does this today. If one ever does, the resolver must stop
        rather than pick whichever came first.
        """
        broken = BOOK.replace("## 3. Intellect", "## 2. Intellect")
        with pytest.raises(ChapterError, match="numbers two chapters the same"):
            select_chapters(chapter_index(broken), "2")

    def test_the_selection_keeps_document_order(self) -> None:
        picked = select_chapters(chapter_index(BOOK), "3,1")
        assert [c["number"] for c in picked] == [1, 3]


class TestTheRepairs:
    def test_the_duplicated_inline_copy_goes_and_the_blockquote_stays(self) -> None:
        md = '## 1. One\n\nHe said "as my own soul (عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي)":\n\n> عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي\n'
        fixed, n = drop_duplicated_inline_arabic(md)
        assert n == 1
        assert duplicated_arabic(fixed) == []
        assert "> عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي" in fixed, "the blockquote must survive"
        assert 'He said "as my own soul":' in fixed

    def test_arabic_that_appears_once_is_never_removed(self) -> None:
        md = "## 1. One\n\nHe said (عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي) and nothing else.\n"
        fixed, n = drop_duplicated_inline_arabic(md)
        assert (fixed, n) == (md, 0)

    def test_a_short_glossed_term_is_never_removed(self) -> None:
        md = "## 1. One\n\nThe gate (بَاب) opens.\n\n> بَاب\n"
        assert drop_duplicated_inline_arabic(md)[1] == 0

    def test_the_prophet_gets_his_own_honorific(self) -> None:
        md = "## 1. One\n\nThe Messenger of Allah (ع) said, and the Prophet (ع) confirmed it.\n"
        fixed, n = use_prophet_ligature(md)
        assert n == 2
        assert prophet_wrong_honorific(fixed) == []
        assert f"The Messenger of Allah {PROPHET_LIGATURE}" in fixed

    def test_an_imam_named_muhammad_keeps_his(self) -> None:
        md = "## 1. One\n\nAl-Sadiq Jafar ibn Muhammad (ع) said.\n"
        assert use_prophet_ligature(md) == (md, 0)

    def test_the_cap_keeps_the_first_use_in_each_chapter(self) -> None:
        md = "## 1. One\n\nAli (ع) said, then Ali (ع) again, then Ali (ع).\n\n## 2. Two\n\nAli (ع) once.\n"
        fixed, n = cap_honorifics(md)
        assert n == 2
        assert honorific_overuse(fixed) == []
        assert fixed.count("(ع)") == 2, "one survives per chapter"
        assert fixed.startswith("## 1. One\n\nAli (ع) said, then Ali again")

    def test_two_different_figures_each_keep_one(self) -> None:
        md = "## 1. One\n\nAli (ع) and Husayn (ع) spoke; Ali (ع) again.\n"
        fixed, n = cap_honorifics(md)
        assert n == 1
        assert "Ali (ع) and Husayn (ع) spoke; Ali again." in fixed

    def test_the_sentence_closes_up_rather_than_printing_a_double_space(self) -> None:
        md = "## 1. One\n\nAli (ع) spoke. Ali (ع), later, spoke again.\n"
        fixed, _ = cap_honorifics(md)
        assert "Ali, later, spoke again." in fixed
        assert "  " not in fixed.split("\n")[2]

    @pytest.mark.parametrize(
        "repair",
        [drop_duplicated_inline_arabic, use_prophet_ligature, cap_honorifics],
        ids=["duplicated", "prophet", "cap"],
    )
    def test_every_repair_is_idempotent(self, repair) -> None:
        md = (
            "## 1. One\n\n"
            'The Messenger of Allah (ع) said "as my own soul (عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي)". '
            "Ali (ع) heard it, and Ali (ع) repeated it.\n\n"
            "> عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي\n"
        )
        once, first = repair(md)
        twice, second = repair(once)
        assert first > 0, "the fixture must exercise this repair"
        assert second == 0 and twice == once


class TestTheEngineRefuses:
    def test_romanized_arabic_has_no_automatic_repair(self) -> None:
        """The registry is the statement, so a caller cannot ask for one by accident.

        Two of the fourteen live instances have no Arabic anywhere on disk; supplying it
        would mean a model recalling scripture onto a religious edition.
        """
        from _book_defect_fixes import FIXES

        assert "romanized-arabic" not in FIXES
        assert "english-rtl" not in FIXES

    def test_every_repair_names_a_real_detector(self) -> None:
        from _book_defect_fixes import FIXES
        from _book_defects import DETECTORS

        assert set(FIXES) <= set(DETECTORS), "a repair for a defect nothing detects"
