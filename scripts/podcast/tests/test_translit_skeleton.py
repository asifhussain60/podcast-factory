"""Is this Latin string a romanization of this Arabic script?

Every case is drawn from the nine live glossaries as they stood on 2026-08-03,
when a post-merge sweep found that `_book_substitution` was ready to print "and
do not الْمُبَاشَرَة them during that time" — because its only defence was a
ninety-word denylist of English words, and `approach` was not on it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _translit_skeleton import romanizes  # noqa: E402

# ─── The P0: English words a denylist will never finish enumerating ──────────
NOT_ARABIC = [
    ("approach", "الْمُبَاشَرَة"),  # mukhtasar-ul-asar-1, the sweep's own case
    ("pole", "قُطْب"),  # degrees-of-excellence
    ("water", "مَاء"),
    ("blind", "أَعْمَى"),
    ("knowledge", "عِلْم"),
    ("light", "نُور"),
    ("Path", "طَرِيق"),
    ("Curse", "لَعْنَة"),
]


@pytest.mark.parametrize(("phonetic", "script"), NOT_ARABIC)
def test_an_english_word_does_not_romanize_its_own_translation(phonetic: str, script: str) -> None:
    assert romanizes(phonetic, script) is False


def test_letters_arabic_does_not_have_are_decisive_on_their_own() -> None:
    """No corpus needed: Arabic makes no `p`, no `v`, no `x`, no bare `c`."""
    for word in ("approach", "pole", "vault", "complex", "except"):
        assert romanizes(word, "كِتَاب") is False


# ─── Real romanizations the gate must not cost the page ─────────────────────
IS_ARABIC = [
    ("hudud", "حُدُود"),
    ("mahram", "مَحْرَم"),
    ("khums", "اَلْخُمْس"),
    ("muruwwa", "اَلْمُرُوَّة"),
    ("hadi", "هَدِي"),
    ("bab", "بَاب"),
    ("Kun", "كُن"),
    ("mudghah", "مُضْغَة"),
    ("alaqah", "عَلَقَة"),
    ("hadd", "حَدّ"),
    ("tazir", "تَعْزِير"),
    ("awliya", "أَوْلِيَاء"),
]


@pytest.mark.parametrize(("phonetic", "script"), IS_ARABIC)
def test_a_real_romanization_is_recognised(phonetic: str, script: str) -> None:
    assert romanizes(phonetic, script) is True


# ─── The four shapes a naive left-to-right scan gets wrong ──────────────────
def test_the_article_the_romanization_leaves_off() -> None:
    """`natiq` is a perfect romanization of `الناطق` and spells no `l` at all."""
    assert romanizes("natiq", "اَلنَّاطِق")
    assert romanizes("duat", "الدُّعَاة")
    assert romanizes("Tur", "اَلطُّور")
    assert romanizes("Iraq", "العراق")


def test_the_article_behind_a_joined_proclitic() -> None:
    """`وَالنَّهْي` is `wa'l-nahy`, and the book writes `Wa Nahi`."""
    assert romanizes(
        "'Amr bil Maroof Wa Nahi Anil Munkar",
        "الْأَمْر بِالْمَعْرُوف وَالنَّهْي عَن الْمُنْكَر",
    )


def test_a_digraph_may_be_two_letters() -> None:
    """`Fathiyyah` is fa-t-h-, not fa-th-; `Ashab` is a-s-h-, not a-sh-."""
    assert romanizes("Fathiyyah", "فَتْحِيَّة")
    assert romanizes("Ashab al-Jazair", "أَصْحَابُ الْجَزَائِر")
    # and the digraph reading still works where it is the right one
    assert romanizes("shariah", "شَرِيعَة")
    assert romanizes("khums", "خُمْس")


def test_shadda_may_or_may_not_be_written_twice() -> None:
    """`taqiyya` writes both y's of `تقيّة`; `natiq` writes neither n of `النَّاطِق`."""
    assert romanizes("Taqiyya", "تقيّة")
    assert romanizes("natiq", "اَلنَّاطِق")
    assert romanizes("hujja", "الْحُجَّة")


def test_gemination_the_script_leaves_unmarked() -> None:
    """`al-haqq` doubles a `q` that plain `الحق` writes once."""
    assert romanizes("marifat imam al-haqq", "معرفة إمام الحق")


def test_tanween_is_a_letter_the_romanization_may_spell() -> None:
    """The `n` of `-un` is carried by a mark, and the marks are stripped."""
    assert romanizes("Taubatun Nasuh", "تَوْبَةٌ نَصُوح")


def test_an_english_plural_of_an_arabic_term() -> None:
    assert romanizes("natiqs", "النُّطَقَاءُ")


def test_ta_marbuta_reads_as_h_or_t() -> None:
    """`دعاة` is `duat` in construct and `dawah` in pause."""
    assert romanizes("duat", "دُعَاة")
    assert romanizes("dawah", "دَعْوَة")


# ─── Glossary errors the gate catches as a side effect ──────────────────────
def test_a_script_that_is_a_different_word_is_refused() -> None:
    """`asaas-al-taveel` pairs `Qasim al-Nar` with `قَيِّم النَّار` — *Qayyim*, not
    *Qasim*. Substituting would print a word the book never used."""
    assert romanizes("Qasim al-Nar", "قَيِّم النَّار") is False


def test_a_script_longer_than_the_term_is_refused() -> None:
    """`duat` paired with `دَاعِي الدُّعَاة` (*da'i al-du'at*) would print the whole
    phrase wherever the book wrote one word of it."""
    assert romanizes("duat", "دَاعِي الدُّعَاة") is False


def test_a_truncated_title_is_refused() -> None:
    """`ayyuhal-walad` pairs `Ihya Ulum ad-Din` with a script missing `ad-Din`."""
    assert romanizes("Ihya Ulum ad-Din", "إِحْيَاءُ الْعُلُوم") is False


def test_a_malformed_glossary_row_is_refused() -> None:
    """Two terms in one field, and a phonetic that is really a gloss."""
    assert romanizes("hadd / hudud", "اَلْحُدُود") is False
    assert romanizes("pen (qalam)", "اَلْقَلَم") is False


# ─── Degenerate input ───────────────────────────────────────────────────────
def test_empty_and_scriptless_input_is_refused_not_crashed() -> None:
    for phonetic, script in (("", "كِتَاب"), ("kitab", ""), ("", ""), ("kitab", "kitab")):
        assert romanizes(phonetic, script) is False


def test_the_search_does_not_blow_up_on_a_long_phrase() -> None:
    """Memoized, so the digraph/skip/gemination branching cannot go exponential."""
    import time

    phonetic = " ".join(["al-mustashriqun"] * 12)
    script = " ".join(["الْمُسْتَشْرِقُون"] * 12)
    start = time.monotonic()
    assert romanizes(phonetic, script) is True
    assert time.monotonic() - start < 1.0
