"""Tests for the deterministic corpus fill in fill_glossary_arabic.py.

The three guard rails against deterministic fabrication are each pinned:
class-fold match, uniqueness across all corpus lemmas, OCR grounding. Uses a
tiny morphology.db built from the test excerpt through the production builder.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import fill_glossary_arabic as fga  # noqa: E402
import quranic_morphology as qm  # noqa: E402

EXCERPT = REPO / "tests" / "fixtures" / "morphology-excerpt.txt"


@pytest.fixture()
def db_path(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(qm, "_assert_expected", lambda counts: None)
    path = tmp_path / "morphology.db"
    qm.build_db(db_path=path, source_path=EXCERPT)
    return path


def _rows(*phonetics: str) -> list[dict[str, str]]:
    return [{"phonetic": p, "arabic_script": ""} for p in phonetics]


def test_unique_match_grounded_in_ocr_fills(db_path: Path) -> None:
    # "sabr" folds to صبر (lemma Sabor), and the OCR carries the word.
    fills = fga.corpus_fill(_rows("sabr"), "قال في الصبر فضل عظيم", db_path=db_path)
    assert fills == {"sabr": "صبر"}


def test_al_prefix_is_stripped_before_matching(db_path: Path) -> None:
    fills = fga.corpus_fill(_rows("al-sabr"), "الصبر جميل", db_path=db_path)
    assert fills == {"al-sabr": "صبر"}


def test_not_in_ocr_declines_even_on_unique_match(db_path: Path) -> None:
    # Unique corpus match, but the book's own pages never carry the word.
    fills = fga.corpus_fill(_rows("sabr"), "نص لا يحمل الكلمة المطلوبة", db_path=db_path)
    assert fills == {}


def test_substring_inside_longer_word_never_grounds(db_path: Path) -> None:
    # صبر appears INSIDE يصبرون but the book never prints the word standalone.
    # Live regression (2026-07-28): a substring check grounded نقب inside
    # النقباء and filled a different word than the term. Whole-word only.
    fills = fga.corpus_fill(_rows("sabr"), "هم يصبرون دائما", db_path=db_path)
    assert fills == {}


def test_unknown_term_declines(db_path: Path) -> None:
    fills = fga.corpus_fill(_rows("xyzzy"), "صبر", db_path=db_path)
    assert fills == {}


def test_ambiguous_match_declines(db_path: Path, monkeypatch, tmp_path: Path) -> None:
    # Force ambiguity: register a second, different skeleton whose fold collides
    # with sabr's (ص and س share the fold class "s").
    conn_path = tmp_path / "ambig.db"
    import shutil

    shutil.copy(db_path, conn_path)
    import sqlite3

    conn = sqlite3.connect(conn_path)
    conn.execute("INSERT INTO lemmas VALUES ('sabar2', 'سبر', 'سبر', 'Sbr', 'N', 1)")
    conn.commit()
    conn.close()
    fills = fga.corpus_fill(_rows("sabr"), "الصبر و السبر معا", db_path=conn_path)
    assert fills == {}


def test_vowelled_lemma_fills_bare_printable_script(db_path: Path) -> None:
    # rahman's corpus lemma is fully vowelled (رَّحْمَٰن); the fill must be bare
    # letters only — a vowelled fill would land on the fabricated-vowelling
    # review list.
    fills = fga.corpus_fill(_rows("rahman"), "بسم الله الرحمن الرحيم", db_path=db_path)
    assert fills == {"rahman": "رحمن"}
    assert not any("ً" <= c <= "ٰ" for c in fills["rahman"])


def test_absent_db_degrades_to_empty(tmp_path: Path) -> None:
    assert fga.corpus_fill(_rows("sabr"), "الصبر", db_path=tmp_path / "none.db") == {}
