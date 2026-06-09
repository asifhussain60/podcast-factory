"""Tests for the deterministic pronunciation generalizer (knowledge/term_render.py).

The contract: render_for_audio NEVER returns a hyphen-CAPS respelling — only an
English substitute or a plain transliteration — and the four-tier classifier
(loanword > exonym > gloss > transliteration) resolves in priority order.
"""
import sys
from pathlib import Path

import pytest

_KNOW = Path(__file__).resolve().parents[1] / "knowledge"
sys.path.insert(0, str(_KNOW))

import term_render as tr  # noqa: E402

# Real corpus tables (loaded from content/knowledge-base/).
TABLES = tr.load_tables()


def render(translit, **kw):
    kw.setdefault("tables", TABLES)
    return tr.render_for_audio(translit, **kw)


# ---------------------------------------------------------------- tier 1: loanword
def test_loanword_kept():
    r = render("Allah")
    assert r.text == "Allah" and r.tier == tr.TIER_LOANWORD and not r.is_english


def test_loanword_article_fallback():
    # al-Kaaba should still reach the "kaaba" loanword entry.
    assert render("al-Kaaba").text == "Kaaba"


# ---------------------------------------------------------------- tier 2: exonym
def test_exonym_basic():
    r = render("Qabil")
    assert r.text == "Cain" and r.tier == tr.TIER_EXONYM and r.is_english


def test_exonym_article_fallback():
    # al-Shaytan -> Satan via the bare-key fallback.
    assert render("al-Shaytan").text == "Satan"


def test_exonym_prophet_name():
    assert render("Ibrahim").text == "Abraham"


# ---------------------------------------------------------------- tier 3: gloss
def test_ledger_gloss_wins_over_translit():
    entry = {"gloss": "the elite missionaries", "phonetic": "DAA-ee"}
    r = render("da'i", ledger_entry=entry)
    assert r.text == "the elite missionaries" and r.tier == tr.TIER_GLOSS_LEDGER


def test_book_gloss_applies_to_concept_segment():
    r = render("tafsir", segment="terms", book_glosses={"tafsir": "exegesis"})
    assert r.text == "exegesis" and r.tier == tr.TIER_GLOSS_BOOK


def test_book_gloss_skipped_for_personal_names():
    # A name segment must never be replaced by a common-noun gloss.
    r = render("Tabari", segment="names", book_glosses={"tabari": "the historian"})
    assert r.text == "Tabari" and r.tier == tr.TIER_TRANSLIT


# ---------------------------------------------------------------- tier 4: translit
def test_plain_transliteration_default():
    r = render("al-Tabari")
    assert r.text == "al-Tabari" and r.tier == tr.TIER_TRANSLIT and not r.is_english


def test_diacritics_stripped():
    assert render("al-Ṭabarī").text == "al-Tabari"


def test_never_returns_phonetic_respelling():
    # Even with a phonetic on the ledger entry, the render is the plain term.
    entry = {"phonetic": "is-raa-FEEL", "gloss": ""}
    r = render("Israfil", ledger_entry=entry)
    assert r.text == "Israfil"
    assert "-" not in r.text or r.text.islower() is False  # no hyphen-CAPS pattern
    assert r.text != "is-raa-FEEL"


# ---------------------------------------------------------------- mine_glosses
def test_mine_simple_parenthetical():
    g = tr.mine_glosses("inner interpretation differs from tafsir (exegesis) here")
    assert g.get("tafsir") == "exegesis"


def test_mine_rejects_citation():
    g = tr.mine_glosses("Ibn Khallikan translated his life in al-Wafayat (2/166)")
    assert "al-wafayat" not in g


def test_mine_rejects_comma_fragment():
    g = tr.mine_glosses("the Imams, the Pilgrims (al-hujaj) gathered")
    # the captured English side has a comma -> rejected as a sentence fragment
    assert "al-hujaj" not in g


def test_mine_rejects_stopword_lead():
    g = tr.mine_glosses("and they are the preachers (al-du'at) of the cause")
    assert "al-du'at" not in g and "al-duat" not in g


def test_mine_keeps_short_clean_gloss():
    g = tr.mine_glosses("the authority of tanzil (revelation) to the Speaker")
    assert g.get("tanzil") == "revelation"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
