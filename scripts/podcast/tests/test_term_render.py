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
    # Counted from the canonical header down, because the file also carries a
    # prose table of probe evidence that is deliberately NOT override rows.
    bd = Path(__file__).resolve().parents[3] / "content" / "Islamic" / "degrees-of-excellence"
    if not (bd / "_system" / "pronunciation.md").exists():
        pytest.skip("book not present in this checkout")
    lines = (bd / "_system" / "pronunciation.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Term | Phonetic")) + 1
    rows = [ln for ln in lines[start:] if ln.startswith("| ") and not ln.startswith("|--")]
    assert len(tr.parse_book_override_table(bd)) == len(rows)


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


# ------------------------------------------------ withdrawn rows (2026-08-01)
def test_a_withdrawn_row_keeps_its_term_but_asserts_nothing(tmp_path):
    # `plain` means "this term matters in this book, but nothing is claimed
    # about how it sounds". The row must survive for the probe's inventory and
    # must NOT fire rung 0.
    bd = _override_book(tmp_path, "| arkan | plain | withdrawn; was ar-KAAN |\n| tawhid | tow-HEED | |\n")
    assert [t for t, _v in tr.parse_book_override_table(bd)] == ["arkan", "tawhid"]
    assert list(tr.load_book_overrides(bd)) == [tr.normalize_key("tawhid")]
    assert render("arkan", book_overrides=tr.load_book_overrides(bd)).tier == tr.TIER_TRANSLIT


def test_every_withdrawal_spelling_is_recognised(tmp_path):
    for marker in ("plain", "PLAIN", "-", "—", "(plain)", "n/a"):
        assert tr.is_withdrawn(marker), marker
    for real in ("ar-KAAN", "Cain", "substitute *the pillars*"):
        assert not tr.is_withdrawn(real), real


# ------------------------------------------- only the override table is read
def test_a_table_in_the_prose_is_not_read_as_overrides(tmp_path):
    # These files carry prose about pronunciation, and such prose carries
    # tables. An evidence table of "Told to say / Came out as" put rows like
    # `told to say -> Came out as` into rung 0 and outranked every real
    # override with them.
    sysdir = tmp_path / "_system"
    sysdir.mkdir(parents=True)
    (sysdir / "pronunciation.md").write_text(
        "# Pronunciation\n\n"
        "What the probe found:\n\n"
        "| Told to say | Came out as | |\n|---|---|---|\n"
        '| `wa-LAA-ya` | "wa la ya" | wrong |\n\n'
        "| Term | Phonetic | Notes |\n|---|---|---|\n"
        "| tawhid | tow-HEED | |\n",
        encoding="utf-8",
    )
    assert tr.load_book_overrides(tmp_path) == {tr.normalize_key("tawhid"): "tow-HEED"}


def test_a_list_after_the_table_does_not_leak_in(tmp_path):
    bd = _override_book(tmp_path, "| tawhid | tow-HEED | |\n\n- **arkan** was `ar-KAAN` (not heard)\n")
    assert list(tr.load_book_overrides(bd)) == [tr.normalize_key("tawhid")]


def test_a_headerless_table_still_parses(tmp_path):
    # A book whose table predates the canonical header must keep working.
    sysdir = tmp_path / "_system"
    sysdir.mkdir(parents=True)
    (sysdir / "pronunciation.md").write_text("| arkan | ar-KAAN |\n", encoding="utf-8")
    assert tr.load_book_overrides(tmp_path) == {tr.normalize_key("arkan"): "ar-KAAN"}


def test_no_unproven_respelling_is_active_in_the_live_book():
    """Every ACTIVE value in this book's table has evidence behind it.

    Not a count — counts move as the probe settles terms. The invariant is that
    a value only governs the audio once a human has heard it: either a
    respelling a probe confirmed, or an explicit `substitute` standing in for a
    term no written form could carry. A bare respelling appearing here again
    means 41 unheard guesses have crept back in, which is where this began.
    """
    bd = Path(__file__).resolve().parents[3] / "content" / "Islamic" / "degrees-of-excellence"
    if not (bd / "_system" / "pronunciation.md").exists():
        pytest.skip("book not present in this checkout")
    proven = {tr.normalize_key("tawhid"), tr.normalize_key("tashbih")}
    unproven = [
        f"{term} -> {value}"
        for term, value in tr.parse_book_override_table(bd)
        if not tr.is_withdrawn(value)
        and not value.lower().startswith("substitute")
        and tr.normalize_key(term) not in proven
    ]
    assert unproven == []
    # And the terms themselves stay on the list, so the probe still knows them.
    assert len(tr.parse_book_override_table(bd)) == 40


# ------------------------------------- gloss direction (found by probe 2, 2026-08-01)
def test_an_english_word_is_never_glossed_with_the_arabic():
    # "God called Adam a vicegerent (khalīfa)" matches BOTH parenthetical
    # patterns, and the left one mined it as vicegerent -> khalīfa. That reached
    # the probe bundle as `Said aloud: khalifa` for the term "vicegerent" —
    # answering an English word with an Arabic one, the opposite of a gloss.
    assert tr.mine_glosses("God called Adam a vicegerent (khalīfa), and the title") == {}


def test_an_apostrophe_marks_the_arabic_side_too():
    # Same reversal without a macron to signal it.
    assert tr.mine_glosses("the honey-producing bee — indeed their chief (ya'sub) — are") == {}
    assert tr.mine_glosses("The word 'bestowal' (fay') means 'return'") == {}


def test_direction_is_undecidable_without_a_transliteration_signal():
    """KNOWN LIMITATION, pinned so it is not mistaken for a fix.

    `English (translit)` and `translit (English)` are the same shape, so the
    only way to tell them apart here is a mark the Arabic side carries — a
    macron, an under-dot, an ayn/hamza apostrophe. Strip those and the guess
    goes the wrong way: "their chief (yasub)" mines chief -> yasub.

    Every instance that actually reached the probe bundle carried such a mark
    (khalīfa, ya'sub, fay'), so the live defect is closed. Deciding the rest
    needs an English lexicon or the book's own term list, which belongs with
    the caller that has one — not in this heuristic.
    """
    assert tr.mine_glosses("indeed their chief (yasub) stands apart") == {"chief": "yasub"}


def test_the_legitimate_glosses_still_survive_all_of_that():
    assert tr.mine_glosses("the first is qutb (the pole), the pivot") == {"qutb": "the pole"}
    assert tr.mine_glosses("the batin (inner meaning) of the verse") == {"batin": "inner meaning"}
    assert tr.mine_glosses("differs from tafsir (exegesis) here")["tafsir"] == "exegesis"
