"""Tests for the deterministic pronunciation generalizer (knowledge/term_render.py).

The contract: below the override rung render_for_audio NEVER returns a
hyphen-CAPS respelling — only an English substitute or a plain transliteration —
and the classifier (book-override > loanword > exonym > gloss > transliteration)
resolves in priority order. Rung 0 is the deliberate exception: a value a human
typed into BOOK_DIR/_system/pronunciation.md is passed through verbatim.
"""

import sys
from pathlib import Path

import pytest

_KNOW = Path(__file__).resolve().parents[1] / "knowledge"
sys.path.insert(0, str(_KNOW))

import term_render as tr

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


def test_never_returns_an_unheard_respelling():
    # An "unfixable" phonetic is a record of what FAILED, never a candidate.
    entry = {"phonetic": "is-raa-FEEL", "gloss": "the archangel", "status": "unfixable"}
    r = render("Israfil", ledger_entry=entry)
    assert r.text == "the archangel" and r.tier == tr.TIER_GLOSS_LEDGER
    assert r.text != "is-raa-FEEL"


def test_unfixable_without_a_gloss_falls_back_to_the_plain_term():
    entry = {"phonetic": "is-raa-FEEL", "gloss": "", "status": "unfixable"}
    assert render("Israfil", ledger_entry=entry).text == "Israfil"


# ------------------------------------------------------- tier 3: ledger-confirmed
def test_confirmed_ledger_phonetic_is_used():
    # This is what closes the probe -> listen -> correct loop: a form somebody
    # heard come out right must reach the next book's framing.
    entry = {"phonetic": "gha-zaa-lee", "gloss": "", "status": "confirmed"}
    r = render("al-Ghazali", ledger_entry=entry)
    assert r.text == "gha-zaa-lee" and r.tier == tr.TIER_LEDGER_CONFIRMED and not r.is_english


def test_confirmed_phonetic_equal_to_the_term_is_not_an_entry():
    # "arkan confirmed as arkan" carries no instruction — it must fall through
    # to the plain transliteration rather than emit a no-op respelling.
    entry = {"phonetic": "Arkan", "gloss": "", "status": "confirmed"}
    assert render("arkan", ledger_entry=entry).tier == tr.TIER_TRANSLIT


def test_a_statusless_entry_resolves_exactly_as_before_the_rung_existed():
    # Every row the ledger writes stamps a status; a hand-built dict without one
    # must keep its pre-2026-08-01 behaviour, which is gloss-over-phonetic.
    entry = {"phonetic": "DAA-ee", "gloss": "the elite missionaries"}
    assert render("da'i", ledger_entry=entry).tier == tr.TIER_GLOSS_LEDGER


def test_loanword_outranks_a_confirmed_phonetic():
    # Forcing a respelling onto a loanword is how "Imam" became "e-Maam" live.
    entry = {"phonetic": "i-MAAM", "gloss": "", "status": "confirmed"}
    assert render("imam", ledger_entry=entry).tier == tr.TIER_LOANWORD


def test_book_override_outranks_a_confirmed_phonetic(tmp_path):
    bd = _override_book(tmp_path, "| al-Ghazali | al-gha-ZAA-lee | |\n")
    entry = {"phonetic": "gha-zaa-lee", "gloss": "", "status": "confirmed"}
    r = render("al-Ghazali", ledger_entry=entry, book_overrides=tr.load_book_overrides(bd))
    assert r.text == "al-gha-ZAA-lee" and r.tier == tr.TIER_BOOK_OVERRIDE


# ------------------------------------------------------- tier 0: book override
def _override_book(tmp_path, table_body):
    sysdir = tmp_path / "_system"
    sysdir.mkdir(parents=True)
    (sysdir / "pronunciation.md").write_text(
        "# Pronunciation — Test\n\nProse above the table is ignored.\n\n"
        "| Term | Phonetic | Notes |\n|---|---|---|\n" + table_body,
        encoding="utf-8",
    )
    return tmp_path


def test_override_beats_every_lower_tier(tmp_path):
    # "Allah" is a loanword and "Qabil" an exonym — the human still wins.
    bd = _override_book(tmp_path, "| Allah | ahl-LAAH | |\n| Qabil | Kayin | |\n")
    ov = tr.load_book_overrides(bd)
    assert render("Allah", book_overrides=ov).tier == tr.TIER_BOOK_OVERRIDE
    assert render("Allah", book_overrides=ov).text == "ahl-LAAH"
    assert render("Qabil", book_overrides=ov).text == "Kayin"


def test_override_passes_a_respelling_through_verbatim(tmp_path):
    # The one place a hyphen-CAPS form is allowed to reach the audio.
    bd = _override_book(tmp_path, "| arkan | ar-KAAN | the pillars |\n")
    r = render("arkan", book_overrides=tr.load_book_overrides(bd))
    assert r.text == "ar-KAAN" and not r.is_english


def test_override_substitute_prefix_marks_english(tmp_path):
    bd = _override_book(tmp_path, "| nafs | substitute *the lower self* | |\n")
    r = render("nafs", book_overrides=tr.load_book_overrides(bd))
    assert r.text == "the lower self" and r.is_english


def test_override_notes_column_is_never_spoken(tmp_path):
    bd = _override_book(tmp_path, "| qutb | KOOTB | The pole. One syllable. |\n")
    assert render("qutb", book_overrides=tr.load_book_overrides(bd)).text == "KOOTB"


def test_override_article_fallback(tmp_path):
    bd = _override_book(tmp_path, "| zahir | ZAH-hir | |\n")
    r = render("al-zahir", book_overrides=tr.load_book_overrides(bd))
    assert r.text == "ZAH-hir"


def test_missing_or_empty_table_yields_no_overrides(tmp_path):
    assert tr.load_book_overrides(None) == {}
    assert tr.load_book_overrides(tmp_path) == {}  # no _system/pronunciation.md
    bd = _override_book(tmp_path, "")  # header + separator only
    assert tr.load_book_overrides(bd) == {}


def test_malformed_rows_are_skipped_not_fatal(tmp_path):
    bd = _override_book(tmp_path, "| lonely-cell |\n|  | KOOTB | |\n| qutb | KOOTB | ok |\n")
    ov = tr.load_book_overrides(bd)
    assert list(ov) == [tr.normalize_key("qutb")]


def test_real_book_table_parses_every_data_row():
    # The live table degrees-of-excellence carries — a regression here means a
    # row a human wrote is being silently dropped before it reaches the audio.
    bd = Path(__file__).resolve().parents[3] / "content" / "Islamic" / "degrees-of-excellence"
    if not (bd / "_system" / "pronunciation.md").exists():
        pytest.skip("book not present in this checkout")
    rows = [
        ln
        for ln in (bd / "_system" / "pronunciation.md").read_text(encoding="utf-8").splitlines()
        if ln.startswith("| ") and not ln.startswith("| Term") and not ln.startswith("|--")
    ]
    assert len(tr.load_book_overrides(bd)) == len(rows)


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
