"""Characterisation of `_tts_sanitize` — 607 lines that shape every word NotebookLM's voices speak.

NotebookLM reads chapter sources literally, so a diacritic left in a token can be spelled letter by letter and a
curly quote can become a spoken pause. These pin what the sanitiser does TODAY on the inputs that matter, so a rule
change that alters what listeners hear shows up as a red test. They document behaviour, not endorse every choice
(see the note on `Tawhid` below).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _tts_sanitize as t  # noqa: E402


def clean(text: str):
    return t.sanitize_text(text)


def test_plain_english_is_untouched_and_the_report_is_all_zero():
    out, report = clean("A plain English sentence, nothing to do.")
    assert out == "A plain English sentence, nothing to do."
    assert (report.typographic_normalized, report.diacritics_stripped, report.surahs_substituted) == (0, 0, 0)
    assert report.arabic_terms_substituted == {} and report.english_subs == {}


def test_typographic_punctuation_becomes_ascii_and_is_counted():
    out, report = clean("He wrote “x” and ‘y’ … then left now.")
    assert out == "He wrote \"x\" and 'y' ... then left now."
    assert report.typographic_normalized == 6


def test_diacritics_are_stripped_to_plain_letters():
    out, report = clean("Ḥasan and ʿAlī met at Karbalāʾ.")
    assert out == "Hasan and Ali met at Karbala."
    assert report.diacritics_stripped == 5


def test_a_pass_that_creates_a_doubled_article_is_cleaned_up_after_itself():
    out, _ = clean("the the apparent and a an idea")
    assert out == "the apparent and an idea"


def test_the_three_residual_pronunciation_cases_the_module_documents():
    """The RCA in the module docstring: names TTS mangled even after diacritics went."""
    out, _ = clean("Ma'add ibn Isma'il taught soteriology.")
    assert "Maad ibn Ismail" in out, "the hyphen-laden name must not survive as a phantom pause"
    assert "the theology of salvation" in out and "soteriology" not in out


def test_tawhid_is_replaced_by_an_english_phrase_not_left_to_be_slurred():
    # The module docstring says `Tawhid` is forced to `Taw-heed`; the live substitution table renders it in English
    # ("Divine Oneness"). Pinned as it behaves today — if the docstring is right and the table is wrong, this is
    # the test that will say so.
    out, _ = clean("The doctrine of Tawhid is central.")
    assert "Tawhid" not in out and "Divine Oneness" in out


def test_the_sanitiser_is_idempotent_on_already_clean_text():
    once, _ = clean("Ḥasan and ʿAlī said “hello” … and left.")
    twice, report = clean(once)
    assert twice == once
    assert report.typographic_normalized == 0 and report.diacritics_stripped == 0


def test_quran_citations_are_left_readable():
    out, _ = clean("See Quran 2:255 for the throne verse.")
    assert "2" in out and "255" in out and out.startswith("See Quran")


def test_the_report_type_is_the_documented_one():
    _, report = clean("x")
    assert isinstance(report, t.SubstitutionReport)
