"""Tests for removing a chapter that is a modern editor's apparatus.

`asaas-al-taveel/vol-01` printed 5,552 words of a 1960 editor's front matter as
its chapter 1 — his own essay, his manuscript notes, his signature — while the
author it belongs to died in 363 AH.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _book_edits import record_edit
from drop_editorial_chapter import apply, drop_section, plan, renumber_headings

_BOOK = (
    "# Asas al-Taweel\n\n"
    "## 1. What Ismaili Interpretation Is\n\n"
    "I held this book back from the press for a long time.\n\n"
    "## 2. The Call to Inner Meaning\n\n"
    "In the name of God, the Most Gracious, the Most Merciful.\n\n"
    "## 3. The Four Limits of the Testimony\n\n"
    "The third chapter's own words.\n"
)


def _book(tmp_path: Path) -> Path:
    bd = tmp_path / "vol-01"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(_BOOK, encoding="utf-8")
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {"bk_index": 1, "title": "What Ismaili Interpretation Is", "source_line_ranges": [[1, 217]]},
                    {"bk_index": 2, "title": "The Call to Inner Meaning", "source_line_ranges": [[218, 442]]},
                    {"bk_index": 3, "title": "The Four Limits of the Testimony", "source_line_ranges": [[443, 590]]},
                ]
            }
        ),
        encoding="utf-8",
    )
    return bd


def _toc(bd: Path) -> list[dict]:
    return json.loads((bd / "book" / "book-toc.json").read_text(encoding="utf-8"))["chapters"]


def test_the_editors_chapter_goes_and_the_rest_move_up(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    apply(plan(bd, "What Ismaili Interpretation Is"), log=lambda _m: None)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert "What Ismaili Interpretation Is" not in body
    assert "I held this book back" not in body
    assert body.index("## 1. The Call to Inner Meaning") < body.index("## 2. The Four Limits")
    assert [(c["bk_index"], c["title"]) for c in _toc(bd)] == [
        (1, "The Call to Inner Meaning"),
        (2, "The Four Limits of the Testimony"),
    ]


def test_the_surviving_chapters_keep_their_own_words(tmp_path: Path) -> None:
    """The renumbering touches headings only — never a line of prose."""
    bd = _book(tmp_path)

    apply(plan(bd, "What Ismaili Interpretation Is"), log=lambda _m: None)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert "In the name of God, the Most Gracious, the Most Merciful." in body
    assert "The third chapter's own words." in body


def test_source_line_ranges_are_never_shifted(tmp_path: Path) -> None:
    """The numbering is presentation; the ranges point at the SOURCE and do not
    move because a chapter was dropped from the edition."""
    bd = _book(tmp_path)

    apply(plan(bd, "What Ismaili Interpretation Is"), log=lambda _m: None)

    assert [c["source_line_ranges"] for c in _toc(bd)] == [[[218, 442]], [[443, 590]]]


def test_a_composer_authored_chapter_is_refused(tmp_path: Path) -> None:
    """A chapter a human authored is not deleted on a script's say-so."""
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="what ismaili interpretation is", body_md="The author's own text.")

    with pytest.raises(SystemExit, match="Composer edit"):
        plan(bd, "What Ismaili Interpretation Is")


def test_a_chapter_that_is_not_there_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no chapter titled"):
        plan(_book(tmp_path), "A Chapter Nobody Wrote")


def test_the_crosswalk_and_manifest_follow_when_they_exist(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    rows = [
        {"index": 1, "title": "What Ismaili Interpretation Is"},
        {"index": 2, "title": "The Call to Inner Meaning"},
        {"index": 3, "title": "The Four Limits of the Testimony"},
    ]
    (bd / "book" / "source-crosswalk.json").write_text(json.dumps({"chapters": rows}), encoding="utf-8")
    (bd / "_system" / "translation-edition-manifest.json").write_text(json.dumps({"chapters": rows}), encoding="utf-8")

    apply(plan(bd, "What Ismaili Interpretation Is"), log=lambda _m: None)

    for rel in ("book/source-crosswalk.json", "_system/translation-edition-manifest.json"):
        got = json.loads((bd / rel).read_text(encoding="utf-8"))["chapters"]
        assert [(c["index"], c["title"]) for c in got] == [
            (1, "The Call to Inner Meaning"),
            (2, "The Four Limits of the Testimony"),
        ]


def test_a_book_without_a_crosswalk_is_not_a_failure(tmp_path: Path) -> None:
    """asaas has neither file — a book composed before they existed has not."""
    bd = _book(tmp_path)

    apply(plan(bd, "What Ismaili Interpretation Is"), log=lambda _m: None)

    assert not (bd / "book" / "source-crosswalk.json").exists()


def test_renumbering_leaves_unnumbered_headings_alone() -> None:
    md = "# T\n\n## Introduction to the Book\n\nApparatus.\n\n## 4. A Chapter\n\nProse.\n"

    out = renumber_headings(md)

    assert "## Introduction to the Book" in out
    assert "## 1. A Chapter" in out


def test_dropping_a_section_that_is_absent_changes_nothing() -> None:
    assert drop_section(_BOOK, "A Chapter Nobody Wrote") == (_BOOK, 0)
