#!/usr/bin/env python3
"""The romanization ladder, and the three ways its first version put the wrong Arabic down.

All three were caught on 2026-08-09 by reading the output before it was committed, not by
a gate — which is why they are gates now. Each one wrote plausible, well-formed, fully
vowelled Arabic into a religious text, and each one wrote a DIFFERENT saying from the one
the book had printed. That is the failure mode this whole module exists to make
impossible, and it is invisible to anyone who cannot read Arabic.

  THE LONGEST RUN WINS      a research card explaining one saying also quotes its
                            neighbours, so "the longest Arabic run in the reply" picked
                            `مَا تُرِيدُونَ مِنْ عَلِيٍّ؟` — a different hadith — for
                            `inna Ali minni wa ana minhu`. The agreement check then
                            passed, because it was checking the wrong candidate.

  THE CHECK WAS CONDITIONAL `if rendered and overlap(...) < …` silently turned itself off
                            whenever the rendering failed, which is exactly when the
                            caller has nothing to check against and should refuse.

  CONTAINS IS NOT EQUALS    verse 65:2 holds `وَمَن يَتَّقِ ٱللَّهَ يَجْعَل لَّهُۥ مَخْرَجًا`
                            inside forty words of surrounding law. Overlap answers "does
                            this contain the saying"; it cannot answer "is this the
                            saying", and the whole verse went where six quoted words had.

No test here calls a model or the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_romanization import (  # noqa: E402
    LIBRARY,
    RECONSTRUCTED,
    Resolution,
    _best_matching_arabic,
    _only_arabic,
    _skeleton_words,
    find_by_research,
    same_extent,
)

#: The fragment the book quotes, and the verse that contains it. Real text from
#: Spiritual Ethos ch.9 and Qur'an 65:2 — the pair that produced the third failure.
FRAGMENT = "وَمَنْ يَتَّقِ اللَّهَ يَجْعَلْ لَهُ مَخْرَجًا"
CONTAINING_VERSE = (
    "فَإِذَا بَلَغْنَ أَجَلَهُنَّ فَأَمْسِكُوهُنَّ بِمَعْرُوفٍ أَوْ فَارِقُوهُنَّ بِمَعْرُوفٍ "
    "وَأَشْهِدُوا ذَوَيْ عَدْلٍ مِنْكُمْ وَأَقِيمُوا الشَّهَادَةَ لِلَّهِ ذَلِكُمْ يُوعَظُ بِهِ "
    "مَنْ كَانَ يُؤْمِنُ بِاللَّهِ وَالْيَوْمِ الْآخِرِ وَمَنْ يَتَّقِ اللَّهَ يَجْعَلْ لَهُ مَخْرَجًا"
)


class TestTheSkeletonIsPerWord:
    def test_a_run_yields_one_token_per_word(self) -> None:
        """`normalize_arabic` drops whitespace with the marks — it builds ONE join key.

        Normalising first and splitting after gave exactly one token for any run, so every
        overlap score came out nothing-or-everything and the library never matched.
        """
        words = _skeleton_words("أَنَا مَدِينَةُ الْعِلْمِ وَعَلِيٌّ بَابُهَا")
        assert len(words) == 5, words
        assert words[0] == "انا"


class TestContainsIsNotEquals:
    def test_the_containing_verse_is_not_the_saying(self) -> None:
        assert same_extent(FRAGMENT, CONTAINING_VERSE) is False

    def test_the_saying_matches_itself(self) -> None:
        assert same_extent(FRAGMENT, FRAGMENT) is True

    def test_a_differently_vowelled_printing_still_matches(self) -> None:
        bare = "ومن يتق الله يجعل له مخرجا"
        assert same_extent(FRAGMENT, bare) is True

    def test_a_fragment_of_the_saying_is_not_the_saying_either(self) -> None:
        assert same_extent(FRAGMENT, "وَمَنْ يَتَّقِ") is False

    def test_nothing_matches_nothing(self) -> None:
        assert same_extent("", FRAGMENT) is False
        assert same_extent(FRAGMENT, "") is False


class TestTheAgreeingRunWinsNotTheLongest:
    def test_a_card_quoting_its_neighbours_yields_the_right_saying(self) -> None:
        rendered = "إِنَّ عَلِيًّا مِنِّي وَأَنَا مِنْهُ"
        card = (
            "Some report مَا تُرِيدُونَ مِنْ عَلِيٍّ؟ مَا تُرِيدُونَ مِنْ عَلِيٍّ؟ مَا تُرِيدُونَ مِنْ عَلِيٍّ؟ "
            "but the tradition here is إِنَّ عَلِيًّا مِنِّي وَأَنَا مِنْهُ and it is well known."
        )
        assert _best_matching_arabic(card, rendered) == "إِنَّ عَلِيًّا مِنِّي وَأَنَا مِنْهُ"
        assert _only_arabic(card) != "إِنَّ عَلِيًّا مِنِّي وَأَنَا مِنْهُ", (
            "the old rule must still pick the wrong one — otherwise this test proves nothing"
        )

    def test_a_card_holding_no_agreeing_run_yields_nothing(self) -> None:
        rendered = "إِنَّ عَلِيًّا مِنِّي وَأَنَا مِنْهُ"
        card = "The scholars discuss مَا تُرِيدُونَ مِنْ عَلِيٍّ؟ at some length."
        assert _best_matching_arabic(card, rendered) == ""

    def test_no_rendering_yields_nothing_rather_than_the_first_run(self) -> None:
        assert _best_matching_arabic("قَالَ رَسُولُ اللَّهِ صَلَّى اللَّهُ", "") == ""


class TestTheWebRungRefusesWithoutSomethingToCheckAgainst:
    def test_it_refuses_outright_when_the_rendering_failed(self) -> None:
        """No network call is made — the guard returns before the bridge is reached.

        Written as `if rendered and …`, the agreement rule turned itself OFF in exactly
        the case where the caller has nothing to compare against.
        """
        assert find_by_research("Ana madinatul-ilm wa 'Ali babuha", rendered="") is None


class TestTheRecord:
    @pytest.mark.parametrize("provenance", [LIBRARY, RECONSTRUCTED])
    def test_a_resolution_reports_where_it_came_from(self, provenance: str) -> None:
        record = Resolution("man kuntu mawlahu", "مَنْ كُنْتُ مَوْلَاهُ", provenance).as_record()
        assert record["provenance"] == provenance
        assert record["romanization"] and record["arabic"]

    def test_an_empty_resolution_is_not_ok(self) -> None:
        assert Resolution("x", "", RECONSTRUCTED).ok is False
