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


def test_audit_resolves_canonical_verses_to_the_mushaf_tier() -> None:
    from _book_arabic_audit import RESOLUTION_MUSHAF, audit_book_arabic

    book = "## One\n\n> لَيْسَ كَمِثْلِهِ شَيْءٌ\n\nThere is nothing like Him.\n"
    result = audit_book_arabic(book, arabic_src="")
    runs = result["chapters"][0]["runs"]
    assert runs and runs[0]["resolution"] == RESOLUTION_MUSHAF
