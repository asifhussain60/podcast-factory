"""Canonical-mushaf lookup, and the audit tier it feeds.

The corpus (content/knowledge-base/mirror.db, tracked in git) was in the repo for
months and never wired to verification. Before this, canonical verses resolved as
`ocr` by coincidental skeleton match — the audit could not tell a Quranic citation
from the source's own words, which is why a fabricated-vowelling guard was
impossible to write without crying wolf on every verse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _mushaf import is_quranic, mushaf_available  # noqa: E402

pytestmark = pytest.mark.skipif(not mushaf_available(), reason="mirror.db absent in this checkout")

# Verses this book actually quotes, in the orthography the book uses (simplified),
# against the mirror's Uthmani text — so these also guard the folding table.
_QURANIC = [
    ("لَيْسَ كَمِثْلِهِ شَيْءٌ", "Q 42:11"),
    ("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "basmala"),
    ("أَطِيعُوا اللَّهَ وَأَطِيعُوا الرَّسُولَ", "Q 4:59"),
    ("عَلَىٰ فَتْرَةٍ مِّنَ الرُّسُلِ", "Q 5:19"),
    ("وَلَا تَرْكَنُوا إِلَى الَّذِينَ ظَلَمُوا", "Q 11:113"),
]

_NOT_QURANIC = [
    ("شَهِدَ فُلَانٌ وَهُوَ عَدْلٌ مِنَ الْعُدُولِ", "a legal formula, not scripture"),
    # The source's own sentence, which ECHOES Q 55:29 but prefixes it. Classifying
    # this as Quranic would excuse its fabricated vowelling.
    ("وَإِنَّهُ كُلَّ يَوْمٍ هُوَ فِي شَأْنٍ", "source sentence with a Quranic echo"),
]


@pytest.mark.parametrize("span,label", _QURANIC)
def test_canonical_verses_are_recognized(span: str, label: str) -> None:
    assert is_quranic(span), label


@pytest.mark.parametrize("span,label", _NOT_QURANIC)
def test_non_scripture_is_not_claimed_as_quranic(span: str, label: str) -> None:
    assert not is_quranic(span), label


def test_short_fragments_do_not_match_by_accident() -> None:
    # Two letters appear everywhere in 6,236 verses; a hit there is coincidence.
    assert not is_quranic("في")
    assert not is_quranic("الله")


def test_eleven_letter_phrase_clears_the_floor() -> None:
    # Regression: a 12-letter floor silently rejected `ليس كمثله شيء` (11), one of
    # the most-quoted phrases in the corpus, making the whole check look broken.
    from _arabic_coverage import normalize_arabic

    assert len(normalize_arabic("لَيْسَ كَمِثْلِهِ شَيْءٌ")) == 11
    assert is_quranic("لَيْسَ كَمِثْلِهِ شَيْءٌ")


def test_the_shortest_and_most_quoted_formula_is_recognized() -> None:
    # Q 2:117 / 3:47 / 16:40 / 36:82. A 7-letter skeleton sat under the 10-letter
    # floor, so the corpus's single most-quoted formula came back NON-canonical and
    # landed on the fabricated-vowelling review list — the exact false positive
    # this module exists to remove. The book sets `فَيَكُونُ` as a run of its own,
    # so the one-word form has to work too.
    assert is_quranic("كُنْ فَيَكُونُ")
    assert is_quranic("فَيَكُونُ")


def test_uthmani_spelling_folds_onto_modern_spelling() -> None:
    # The mirror stores Q 1:2 defectively (`ٱلْعَلَمِينَ`); a modern typesetter or a
    # model writes `الْعَالَمِينَ`. As plain strings they never match, so the opening
    # chapter of the Quran failed the check outright.
    assert is_quranic("الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ")


def test_word_segmentation_differences_do_not_hide_a_verse() -> None:
    # The mushaf sets Q 7:26 as `يَٰبَنِىٓ ءَادَمَ` — one word where modern text has
    # two — so no amount of word alignment can see it.
    assert is_quranic("يَا بَنِي آدَمَ قَدْ أَنْزَلْنَا عَلَيْكُمْ لِبَاسًا")


def test_a_quotation_may_carry_a_connective_the_mushaf_lacks() -> None:
    # The book sets `فَسُبْحَانَ` where Q 36:36 reads `سُبْحَانَ`. One proclitic letter
    # broke alignment on the first word and nothing else.
    assert is_quranic("فَسُبْحَانَ الَّذِي خَلَقَ الْأَزْوَاجَ كُلَّهَا")


def test_a_lone_short_word_is_not_scripture() -> None:
    # `بلغنا` — "it has reached us" — is this book's transmitter formula and the
    # thing its whole narrative frame rests on. A one-word span has no internal
    # alignment evidence, so a short one must not resolve as canonical.
    assert not is_quranic("بلغنا")
    assert not is_quranic("العالم")


def test_audit_resolves_canonical_verses_to_the_mushaf_tier() -> None:
    from _book_arabic_audit import RESOLUTION_MUSHAF, audit_book_arabic

    book = "## One\n\n> لَيْسَ كَمِثْلِهِ شَيْءٌ\n\nThere is nothing like Him.\n"
    result = audit_book_arabic(book, arabic_src="")
    runs = result["chapters"][0]["runs"]
    assert runs and runs[0]["resolution"] == RESOLUTION_MUSHAF
