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

from _mushaf import (  # noqa: E402
    is_quranic,
    is_quranic_sequence,
    mushaf_available,
    mushaf_reference,
    mushaf_reference_label,
)

pytestmark = pytest.mark.skipif(not mushaf_available(), reason="mirror.db absent in this checkout")

# Verses this book actually quotes, in the orthography the book uses (simplified),
# against the mirror's Uthmani text — so these also guard the folding table.
_QURANIC = [
    ("لَيْسَ كَمِثْلِهِ شَيْءٌ", "Q 42:11"),
    ("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "basmala"),
    ("أَطِيعُوا اللَّهَ وَأَطِيعُوا الرَّسُولَ", "Q 4:59"),
    ("عَلَىٰ فَتْرَةٍ مِّنَ الرُّسُلِ", "Q 5:19"),
    ("وَلَا تَرْكَنُوا إِلَى الَّذِينَ ظَلَمُوا", "Q 11:113"),
    # Uthmani MID-WORD maqsura+dagger-alif vs modern plain alif: the mushaf sets
    # `يُلَقَّىٰهَا` where a modern text writes `يُلَقَّاهَا`. Stripping the dagger as a
    # vowel mark left the maqsura to fold to ya, so the two spellings skeletonised
    # differently and this canonical verse false-positived on the
    # fabricated-vowelling review list on every audit of the-master-and-the-disciple.
    ("وَمَا يُلَقَّاهَا إِلَّا الَّذِينَ صَبَرُوا وَمَا يُلَقَّاهَا إِلَّا ذُو حَظٍّ عَظِيمٍ", "Q 41:35, modern spelling"),
    ("وَمَا يُلَقَّىٰهَآ إِلَّا ٱلَّذِينَ صَبَرُوا۟", "Q 41:35, Uthmani spelling"),
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


def test_a_span_under_three_words_is_never_called_scripture() -> None:
    """Alignment does not beat coincidence at two words, because the Quran is Arabic.

    Measured over 2,000 random two-word spans of this book's own non-Quranic
    prose, 17.4% aligned somewhere in the 6,236 verses — `ثم قال`, `قال له`,
    `هو الذي`. A span wrongly called scripture is EXCUSED from the
    fabricated-vowelling check, which is the defect this module exists to catch,
    so the floor is three words.

    Distinctiveness was tried instead and failed on measurement: `ثم قال` occurs
    in 1 verse and `كن فيكون` in 8, ranking the connective as more distinctive
    than the citation. Do not reintroduce a match-count heuristic here.

    The cost is real and accepted: `كُنْ فَيَكُونُ` no longer resolves as canonical.
    Nothing downstream needs it to — `ocr_vowelling_findings` declines to judge
    runs this short at all, rather than needing them excused.
    """
    for short in ("ثم قال", "قال له", "هو الذي", "من غير", "كُنْ فَيَكُونُ", "فَيَكُونُ"):
        assert not is_quranic(short), short


def test_folding_may_not_turn_a_negation_into_the_verse_that_denies_it() -> None:
    # Q 6:103 reads `لَا تُدْرِكُهُ الْأَبْصَارُ` — vision does NOT grasp Him. The book
    # asks the interrogative `أَتُدْرِكُهُ الْأَبْصَارُ`. Dropping every alif erased the
    # leading particle and matched the affirmation against the negation, so the
    # defective path is floored high enough that folding cannot flip a sense.
    assert is_quranic("لَا تُدْرِكُهُ الْأَبْصَارُ")
    assert not is_quranic("أَتُدْرِكُهُ الْأَبْصَارُ")
    assert not is_quranic("تُدْرِكُهُ الْأَبْصَارُ")


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


# ── Several ayat quoted in one breath ─────────────────────────────────────────
# Real text from the three books that carried the defect. Fifteen passages were
# filed as somebody's words because the corpus is searched one verse at a time
# and these runs cross two. Harmless while provenance chose only a typeface;
# a doctrinal misstatement the moment it chose a colour (2026-08-09).

#: Surah al-Falaq 113:1-2, as Spiritual Ethos prints it — Extended Arabic-Indic
#: ayah numbers between the verses.
FALAQ = "قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ ۱ مِن شَرِّ مَا خَلَقَ ۲"
#: Ar-Rahman 55:26-27, separated by the end-of-ayah rosette instead of a digit.
RAHMAN = "كُلُّ مَنْ عَلَيْهَا فَانٍۢ ۝ وَيَبْقَىٰ وَجْهُ رَبِّكَ ذُو ٱلْجَلَلِ وَٱلْإِكْرَامِ"
#: A saying of the Prophet about Ali. Not scripture, and must never become so.
HADITH = "عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي"


@pytest.mark.skipif(not mushaf_available(), reason="mirror.db unavailable")
class TestSeveralAyatQuotedTogether:
    def test_the_single_verse_check_cannot_see_across_an_ayah_number(self) -> None:
        """The premise. If this ever passes, the sequence check is redundant."""
        assert not is_quranic(FALAQ)
        assert not is_quranic(RAHMAN)

    @pytest.mark.parametrize("run", [FALAQ, RAHMAN])
    def test_but_the_sequence_check_recognises_them(self, run: str) -> None:
        assert is_quranic_sequence(run)

    def test_a_single_verse_still_resolves(self) -> None:
        assert is_quranic_sequence("لَيْسَ كَمِثْلِهِ شَيْءٌ")

    def test_a_saying_is_not_promoted(self) -> None:
        assert not is_quranic_sequence(HADITH)

    def test_one_scriptural_half_is_not_enough(self) -> None:
        """The error splitting invites: a saying that quotes a verse in passing.

        Torn at the number, one half is scripture and one half is a man's words.
        Unanimity is what refuses it.
        """
        mixed = f"{'لَيْسَ كَمِثْلِهِ شَيْءٌ'} ۝ {HADITH}"
        assert is_quranic(mixed.split("۝")[0].strip())
        assert not is_quranic_sequence(mixed)

    def test_a_fragment_too_short_to_be_evidence_refuses_for_all_of_it(self) -> None:
        """Each part faces `is_quranic`'s own floors; one refusal sinks the run."""
        assert not is_quranic_sequence("قُلْ ۝ هُوَ")

    def test_ascii_digits_are_not_ayah_numbers(self) -> None:
        """A year or a page reference must not tear a run into pieces."""
        assert not is_quranic_sequence(f"{HADITH} 1966 {HADITH}")


@pytest.mark.skipif(not mushaf_available(), reason="mirror.db unavailable")
def test_the_audit_files_a_multi_verse_quotation_as_scripture() -> None:
    from _book_arabic_audit import RESOLUTION_MUSHAF, audit_book_arabic

    result = audit_book_arabic(f"## One\n\n> {FALAQ}\n\nSay: I seek refuge.\n", arabic_src="")
    runs = result["chapters"][0]["runs"]
    assert runs and runs[0]["resolution"] == RESOLUTION_MUSHAF


class TestTheReference:
    """WHICH ayah, not merely whether — the reading edition has no card without it.

    Every test here is a fact about the corpus in `content/knowledge-base/mirror.db`,
    not about a model's recollection of where a verse sits.
    """

    def test_it_names_the_verse(self) -> None:
        assert mushaf_reference("ٱلنَّبِىُّ أَوْلَىٰ بِٱلْمُؤْمِنِينَ مِنْ أَنفُسِهِمْ") == (33, 6)

    def test_the_label_is_the_form_the_edition_already_prints(self) -> None:
        assert mushaf_reference_label("وَإِنَّكَ لَعَلَىٰ خُلُقٍ عَظِيمٍۢ") == "Al-Qalam: 4"

    def test_a_phrase_in_several_ayat_takes_the_earliest(self) -> None:
        """The basmala opens 114 chapters; a header can print one citation."""
        assert mushaf_reference("بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ") == (1, 1)

    def test_a_saying_has_no_reference(self) -> None:
        assert mushaf_reference(HADITH) is None
        assert mushaf_reference_label(HADITH) is None

    def test_several_ayat_in_one_breath_come_back_as_a_range(self) -> None:
        assert mushaf_reference_label(FALAQ) == "Al-Falaq: 1-2"

    def test_a_run_that_quotes_a_verse_in_passing_gets_no_range(self) -> None:
        """`is_quranic_sequence` refuses it; the label must refuse it too."""
        mixed = f"{'لَيْسَ كَمِثْلِهِ شَيْءٌ'} ۝ {HADITH}"
        assert not is_quranic_sequence(mixed)
        assert mushaf_reference_label(mixed) is None

    def test_every_verse_this_function_accepts_can_name_itself(self) -> None:
        """The invariant the Qur'an card depends on, stated as a test.

        A card headed by nothing is not a state the design allows, so anything the
        audit files as scripture must resolve here. Checked against the verses this
        file already pins rather than against the books, so it holds in a checkout
        with no content.
        """
        for run, _why in _QURANIC:
            assert is_quranic(run)
            assert mushaf_reference_label(run), run


@pytest.mark.skipif(not mushaf_available(), reason="mirror.db unavailable")
def test_the_audit_records_the_reference_beside_the_resolution() -> None:
    from _book_arabic_audit import RESOLUTION_MUSHAF, audit_book_arabic

    verse = "وَإِنَّكَ لَعَلَىٰ خُلُقٍ عَظِيمٍۢ"
    result = audit_book_arabic(f"## One\n\n> {verse}\n\nAnd so it was.\n", arabic_src="")
    run = result["chapters"][0]["runs"][0]
    assert run["resolution"] == RESOLUTION_MUSHAF
    assert run["reference"] == "Al-Qalam: 4"


@pytest.mark.skipif(not mushaf_available(), reason="mirror.db unavailable")
def test_a_non_scriptural_run_carries_no_reference_key() -> None:
    from _book_arabic_audit import audit_book_arabic

    result = audit_book_arabic(f"## One\n\n> {HADITH}\n\nHe said it.\n", arabic_src="")
    assert "reference" not in result["chapters"][0]["runs"][0]
