"""Putting the Arabic script back beside an inline term, without damaging it.

Every case here is a defect the book-challenger found in a real edition on
2026-07-21. The pass writes into finished prose, so its failure mode is not an
exception — it is a book that looks fine and says something wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_inline_arabic import apply_inline_arabic  # noqa: E402


def book(tmp_path: Path, body: str, entries: list[dict]) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 1, "entries": entries}, allow_unicode=True),
        encoding="utf-8",
    )
    return bd


def read(bd: Path) -> str:
    return (bd / "book" / "book.md").read_text(encoding="utf-8")


ALLAH = {"phonetic": "Allah", "arabic_script": "الله"}
ABD_ALLAH = {"phonetic": "Abd Allah", "arabic_script": "عبد الله"}


def test_the_script_lands_beside_the_first_mention(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nHe called upon Allah in the morning.\n", [ALLAH])
    assert apply_inline_arabic(bd) == 1
    assert "Allah (الله)" in read(bd)


def test_only_the_first_mention_per_chapter_is_annotated(tmp_path: Path) -> None:
    """Repeating the script at every mention turns prose into a glossary."""
    bd = book(tmp_path, "## 1. A\n\nAllah, and again Allah, and Allah.\n", [ALLAH])
    assert apply_inline_arabic(bd) == 1
    assert read(bd).count("الله") == 1


def test_a_short_term_never_fires_inside_a_longer_name(tmp_path: Path) -> None:
    """The live defect: once "Abd Allah" had been annotated in an earlier line it
    left the pending set, so on a later line the standalone "Allah" entry matched
    the Allah INSIDE "son of Abd Allah" — printing "Abd Allah (الله)" and leaving
    one name carrying two different scripts in the same chapter."""
    body = "## 1. A\n\nHe met Abd Allah at the gate.\n\nI am free, son of Abd Allah.\n"
    bd = book(tmp_path, body, [ALLAH, ABD_ALLAH])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "Abd Allah (عبد الله)" in out
    assert "Abd Allah (الله)" not in out, "the short entry fired inside the name"


def test_a_mention_that_already_carries_its_script_is_left_alone(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nHe called upon Allah (الله) once.\n", [ALLAH])
    assert apply_inline_arabic(bd) == 0
    assert read(bd).count("الله") == 1


def test_an_intervening_quote_does_not_hide_an_existing_annotation(tmp_path: Path) -> None:
    """The live defect: the approved base wrote `"Kab al-Ahbar (كعب الأحبار)"`
    with the closing quote BETWEEN term and parenthetical. A strict `\\s*\\(`
    check walked straight past it and added the script a second time, eight
    characters away."""
    kab = {"phonetic": "Kab al-Ahbar", "arabic_script": "كعب الأحبار"}
    bd = book(tmp_path, '## 1. A\n\nHe said "Kab al-Ahbar (كعب الأحبار)" plainly.\n', [kab])
    assert apply_inline_arabic(bd) == 0
    assert read(bd).count("كعب الأحبار") == 1


def test_the_pass_is_idempotent(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nAllah and Abd Allah both appear.\n", [ALLAH, ABD_ALLAH])
    first = apply_inline_arabic(bd)
    assert first > 0
    assert apply_inline_arabic(bd) == 0
    once = read(bd)
    apply_inline_arabic(bd)
    assert read(bd) == once


def test_blockquotes_and_headings_are_never_annotated(tmp_path: Path) -> None:
    """Quoted Arabic already carries its own script; a heading is not prose."""
    body = "## Allah in the chapter title\n\n> Allah is named in this quote.\n"
    bd = book(tmp_path, body, [ALLAH])
    assert apply_inline_arabic(bd) == 0
    assert "الله" not in read(bd)


def test_honorific_formulas_and_name_particles_are_not_terms(tmp_path: Path) -> None:
    """A formula attached to a name is not a rendering OF the name, and "ibn" is
    grammatical glue — annotating it split a proper name in half."""
    entries = [
        {"phonetic": "Joseph", "arabic_script": "عليه السلام"},
        {"phonetic": "ibn", "arabic_script": "بن"},
    ]
    bd = book(tmp_path, "## 1. A\n\nSalih ibn Joseph spoke.\n", entries)
    assert apply_inline_arabic(bd) == 0


def test_a_term_with_no_script_is_skipped(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nThe Umma gathered.\n", [{"phonetic": "Umma", "arabic_script": ""}])
    assert apply_inline_arabic(bd) == 0


def test_a_missing_glossary_is_not_an_error(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("## 1. A\n\nText.\n", encoding="utf-8")
    assert apply_inline_arabic(bd) == 0
