"""Titles, contents and file names are plain English letters (isaf-al-talib, 2026-09-19)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _latin_plain as lp  # noqa: E402


def test_diacritics_and_ayn_hamza_are_folded() -> None:
    assert lp.plain_title("Iṣāf al-Ṭālib fī Jamīʿ al-Maṭālib") == "Isaf al-Talib fi Jami al-Matalib"
    assert lp.plain_title("Three Questions from the King of Rūm") == "Three Questions from the King of Rum"


def test_transliteration_apostrophes_go_but_english_ones_stay() -> None:
    assert lp.plain_title("Is'af al-Talib fi Jami' al-Matalib") == "Isaf al-Talib fi Jami al-Matalib"
    assert lp.plain_title("Sharh al-Masa'il") == "Sharh al-Masail"
    assert lp.plain_title("The Student's Aid; Students' Guide; Don't Panic") == (
        "The Student's Aid; Students' Guide; Don't Panic"
    )


def test_arabic_script_is_never_touched() -> None:
    mixed = "Wudūʾ كِتَابُ الزِّينَةِ ʿAlī"
    out = lp.plain_latin(mixed)
    assert "كِتَابُ الزِّينَةِ" in out
    assert out.startswith("Wudu ") and out.endswith(" Ali")


def test_plain_titles_are_idempotent() -> None:
    once = lp.plain_title("Iṣāf al-Ṭālib fī Jamīʿ (The Student's Aid)")
    assert lp.plain_title(once) == once
    assert lp.title_violations(once) == []


def test_sanitize_toc_cleans_titles_themes_and_rationales() -> None:
    toc = {
        "book_title": "Iṣāf al-Ṭālib",
        "chapters": [{"title": "Rūm", "theme": "wudūʾ basics", "rationale": "ʿAlī's answers"}],
    }
    lp.sanitize_toc(toc)
    assert toc["book_title"] == "Isaf al-Talib"
    assert toc["chapters"][0] == {"title": "Rum", "theme": "wudu basics", "rationale": "Ali's answers"}


def _book(tmp_path: Path, *, title: str, toc_title: str, prose: str) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "meta.yml").write_text(f'title: "{title}"\n', encoding="utf-8")
    (tmp_path / "book" / "book-toc.json").write_text(
        json.dumps({"book_title": toc_title, "chapters": []}, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "book" / "book.md").write_text(f"## 1. Faith\n\n{prose}\n", encoding="utf-8")
    return tmp_path


def test_gate_flags_each_source_and_passes_a_plain_book(tmp_path: Path) -> None:
    dirty = (
        _book(tmp_path / "a", title="Is'af al-Talib", toc_title="Iṣāf al-Ṭālib", prose="Wudūʾ is required.")
        if ((tmp_path / "a").mkdir() is None)
        else None
    )
    found = lp.book_latin_findings(dirty)
    assert any("meta.yml" in f for f in found)
    assert any("book-toc" in f for f in found)
    assert any("book.md prose" in f for f in found)
    (tmp_path / "b").mkdir()
    clean = _book(tmp_path / "b", title="Isaf al-Talib", toc_title="Isaf al-Talib", prose="Wudu is required. كِتَابٌ")
    assert lp.book_latin_findings(clean) == []


def test_quotation_marks_around_a_word_survive() -> None:
    assert lp.plain_title("The Two Letters of 'Be'") == "The Two Letters of 'Be'"
    assert lp.plain_title("The Du'at of Najran") == "The Duat of Najran"
    assert lp.plain_title("'Ali and Fatima") == "Ali and Fatima"
