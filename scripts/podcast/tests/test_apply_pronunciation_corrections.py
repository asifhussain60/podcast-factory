"""Tests for apply_pronunciation_corrections.py — where a listening verdict lands.

This is the write end of the probe loop: a human hears the probe, marks each term
ok / respell / unfixable, and this module puts that judgement everywhere it has
to go — the cross-book ledger so later books inherit it, and the book's own
surfaces so THIS book stops saying the thing that was just rejected.

The cross-book library is patched to a tmp file in every test; the repo's real
`content/knowledge-base/pronunciations.jsonl` must never be touched by a test run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))
if str(_SCRIPTS_PODCAST / "knowledge") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST / "knowledge"))

import apply_pronunciation_corrections as apc  # noqa: E402
import term_render  # noqa: E402

OVERRIDES = "| arkan | ar-KAAN | the pillars |\n| masbuq | mas-BOOQ | |\n"

GLOSSARY = """\
schema_version: 1
entries:
- phonetic: arkan
  transliteration: arkan
  arabic_script: أركان
  audio_phonetic: ar-KAAN
"""


@pytest.fixture
def book(tmp_path, monkeypatch):
    """A book with an override table + glossary, and a tmp-backed ledger."""
    bd = tmp_path / "a-book"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "pronunciation.md").write_text(
        "| Term | Phonetic | Notes |\n|---|---|---|\n" + OVERRIDES, encoding="utf-8"
    )
    (bd / "_system" / "glossary.yml").write_text(GLOSSARY, encoding="utf-8")
    lib = apc.ledger.load(tmp_path / "ledger.jsonl")
    monkeypatch.setattr(apc.ledger, "load", lambda path=None: lib)
    return bd


def _apply(book, corrections):
    return apc.apply_corrections(book, {"book_slug": "a-book", "corrections": corrections}, confirmed_date="2026-08-01")


# ------------------------------------------------- the break this closes
def test_a_respell_verdict_reaches_the_override_table(book):
    # Without this the ledger and glossary are corrected while the override —
    # rung 0, which beats both — keeps asserting the rejected form, and the
    # hosts keep saying exactly what the listener just marked wrong.
    res = _apply(book, [{"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN"}])
    assert res["overrides_updated"] == 1
    assert "| arkan | ar-KAAHN |" in (book / "_system" / "pronunciation.md").read_text()


def test_the_corrected_form_is_what_the_ladder_now_resolves(book):
    # End to end: the verdict changes what the framing compiler will emit.
    _apply(book, [{"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN"}])
    r = term_render.render_for_audio("arkan", book_overrides=term_render.load_book_overrides(book))
    assert r.text == "ar-KAAHN"


def test_an_unfixable_verdict_turns_the_override_into_a_substitution(book):
    _apply(book, [{"term": "masbuq", "status": "unfixable", "gloss": "the one preceded"}])
    assert "| masbuq | substitute *the one preceded* |" in (book / "_system" / "pronunciation.md").read_text()
    r = term_render.render_for_audio("masbuq", book_overrides=term_render.load_book_overrides(book))
    assert r.text == "the one preceded" and r.is_english


def test_an_ok_verdict_leaves_the_override_alone(book):
    # Nothing was wrong, so nothing is rewritten.
    res = _apply(book, [{"term": "arkan", "status": "ok", "phonetic": "ar-KAAN"}])
    assert res["overrides_updated"] == 0
    assert "| arkan | ar-KAAN |" in (book / "_system" / "pronunciation.md").read_text()


def test_a_term_the_human_never_listed_gets_no_invented_row(book):
    # The override table is the human's file. New rows are proposed in the
    # report, not written into it.
    res = _apply(book, [{"term": "tiryaq", "status": "respell", "phonetic": "tir-YAAQ"}])
    assert res["overrides_updated"] == 0
    assert "tiryaq" not in (book / "_system" / "pronunciation.md").read_text()


def test_the_notes_column_survives_a_correction(book):
    _apply(book, [{"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN"}])
    assert "the pillars" in (book / "_system" / "pronunciation.md").read_text()


# ------------------------------------------------- the cross-book half
def test_every_verdict_reaches_the_cross_book_ledger(book):
    _apply(
        book,
        [
            {"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN"},
            {"term": "masbuq", "status": "unfixable", "gloss": "the one preceded"},
            {"term": "qutb", "status": "ok", "phonetic": "KOOTB"},
        ],
    )
    lib = apc.ledger.load()
    assert lib.lookup("arkan").phonetic == "ar-KAAHN"
    assert lib.lookup("arkan").status == "confirmed"
    assert lib.lookup("masbuq").status == "unfixable"
    assert lib.lookup("masbuq").gloss == "the one preceded"
    assert lib.lookup("qutb").status == "confirmed"


def test_a_confirmed_entry_is_reusable_by_a_book_with_no_override_table(book, tmp_path):
    # The whole point of the ledger: the next Arabic book inherits the answer.
    _apply(book, [{"term": "qutb", "status": "ok", "phonetic": "KOOTB"}])
    entry = apc.ledger.load().lookup("qutb")
    r = term_render.render_for_audio(
        "qutb", ledger_entry={"phonetic": entry.phonetic, "gloss": entry.gloss, "status": entry.status}
    )
    assert r.text == "KOOTB" and r.tier == term_render.TIER_LEDGER_CONFIRMED


def test_heard_misreadings_seed_the_mangle_map(book):
    res = _apply(
        book,
        [{"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN", "mangled_variants": ["Archon", "are can"]}],
    )
    assert res["mangle_map_added"] == 1
    assert "Archon" in (book / "_system" / "mangle-map.md").read_text()


def test_a_verdict_missing_its_payload_is_skipped_not_guessed(book):
    res = _apply(
        book,
        [
            {"term": "arkan", "status": "respell"},  # no phonetic
            {"term": "masbuq", "status": "unfixable"},  # no gloss
            {"term": "", "status": "ok", "phonetic": "x"},  # no term
        ],
    )
    assert res["counts"]["skipped"] == 3
    assert res["overrides_updated"] == 0


def test_a_book_with_no_override_table_still_applies(tmp_path, monkeypatch):
    bd = tmp_path / "bare"
    (bd / "_system").mkdir(parents=True)
    lib = apc.ledger.load(tmp_path / "ledger.jsonl")
    monkeypatch.setattr(apc.ledger, "load", lambda path=None: lib)
    res = _apply(bd, [{"term": "arkan", "status": "respell", "phonetic": "ar-KAAHN"}])
    assert res["overrides_updated"] == 0
    assert res["counts"]["respelled"] == 1
