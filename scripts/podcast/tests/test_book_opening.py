"""Tests for folding the source's own opening into chapter 1, on disk.

The assembly folds when a book is composed. This folds a book already written,
and it exists because the compose route is not a cheap way to reach one: on
2026-08-03 re-composing `ayyuhal-walad` to change its front matter cost 615 words
of teaching and 38 quotation-length Arabic runs, and no gate failed.
"""

from __future__ import annotations

import json
from pathlib import Path

from _book_opening import apply_opening_fold, fold_opening, preface_title

_BOOK = (
    "# The Book of the Road\n\n"
    "## A Letter Across the Centuries\n\n"
    "Know that one of the master's students had remained in his service for years.\n\n"
    "## 1. Knowledge That Will Not Save You\n\n"
    "In the Name of God, the Most Compassionate.\n\n"
    "## 2. The Striving That Mercy Meets\n\n"
    "The second chapter's own words.\n"
)


def _book(tmp_path: Path, *, title: str = "A Letter Across the Centuries", body: str = _BOOK) -> Path:
    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    (bd / "book" / "book-toc.json").write_text(
        json.dumps({"preface": {"include": True, "title": title}, "chapters": []}), encoding="utf-8"
    )
    return bd


def test_the_opening_moves_into_chapter_one_and_its_heading_goes() -> None:
    out, words = fold_opening(_BOOK, "A Letter Across the Centuries")

    assert "## A Letter Across the Centuries" not in out
    assert words == 14
    # Inside chapter 1, above the chapter's own first sentence.
    ch1 = out.index("## 1. Knowledge That Will Not Save You")
    assert ch1 < out.index("Know that one of the master's") < out.index("In the Name of God")
    # Chapter 2 is untouched and still after chapter 1.
    assert out.index("## 2. The Striving") > out.index("In the Name of God")


def test_no_word_of_the_source_is_lost() -> None:
    out, _ = fold_opening(_BOOK, "A Letter Across the Centuries")

    before = [w for w in _BOOK.split() if not w.startswith("#")]
    after = [w for w in out.split() if not w.startswith("#")]
    # Only the front-matter HEADING's own words leave; every word of prose stays.
    assert sorted(after) == sorted(w for w in before if w not in {"A", "Letter", "Across", "the", "Centuries"}) or set(
        before
    ) - set(after) <= {"A", "Letter", "Across", "the", "Centuries"}
    assert "Know that one of the master's students had remained in his service for years." in out


def test_folding_twice_changes_nothing_the_first_did_not() -> None:
    once, _ = fold_opening(_BOOK, "A Letter Across the Centuries")
    twice, words = fold_opening(once, "A Letter Across the Centuries")

    assert twice == once
    assert words == 0


def test_a_book_the_assembly_already_folded_is_a_no_op() -> None:
    """The two paths compose: each looks for a section the other removed."""
    already = "# T\n\n## 1. Knowledge\n\nThe opening, then the chapter.\n"

    assert fold_opening(already, "A Letter Across the Centuries") == (already, 0)


def test_an_opening_with_no_numbered_chapter_is_never_dropped() -> None:
    """Losing the source's words to a book with no chapters is worth refusing over."""
    orphan = "# T\n\n## A Letter Across the Centuries\n\nThe source's first words.\n"

    out, words = fold_opening(orphan, "A Letter Across the Centuries")

    assert out == orphan and words == 0
    assert "The source's first words." in out


def test_an_empty_front_matter_section_is_not_folded() -> None:
    empty = "# T\n\n## A Letter Across the Centuries\n\n## 1. Knowledge\n\nThe chapter.\n"

    assert fold_opening(empty, "A Letter Across the Centuries")[1] == 0


def test_the_heading_is_matched_the_way_the_composer_matches_it() -> None:
    """Through `anchor_key`, so casing and stray markup cannot orphan the fold."""
    out, words = fold_opening(_BOOK, "  a letter ACROSS the centuries ")

    assert words == 14
    assert "## A Letter Across the Centuries" not in out


def test_apply_writes_the_file_and_reports(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    report = apply_opening_fold(bd, log=lambda _m: None)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["folded"] is True and report["words"] == 14
    assert "## A Letter Across the Centuries" not in body
    assert "Know that one of the master's" in body


def test_apply_is_silent_and_writes_nothing_on_a_folded_book(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    apply_opening_fold(bd, log=lambda _m: None)
    mtime = (bd / "book" / "book.md").stat().st_mtime_ns

    assert apply_opening_fold(bd, log=lambda _m: None)["folded"] is False
    assert (bd / "book" / "book.md").stat().st_mtime_ns == mtime


def test_a_book_whose_toc_declares_no_preface_is_left_alone(tmp_path: Path) -> None:
    bd = _book(tmp_path, title="")

    assert apply_opening_fold(bd, log=lambda _m: None)["folded"] is False
    assert preface_title(bd) == ""


def test_the_step_is_classified_as_page_altering() -> None:
    """A skipped fold means the edition begins on front matter — gate B8 blocks."""
    from _compose_skips import ADVISORY_STEPS, PAGE_ALTERING_STEPS

    assert "opening-fold" in PAGE_ALTERING_STEPS
    assert "opening-fold" not in ADVISORY_STEPS


# --- the fold is not complete until chapter 1 owns the opening's source lines --


def _toc(bd: Path) -> dict:
    return json.loads((bd / "book" / "book-toc.json").read_text(encoding="utf-8"))


def _ranged(tmp_path: Path) -> Path:
    bd = _book(tmp_path)
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "preface": {"include": True, "title": "A Letter Across the Centuries", "source_line_ranges": [[8, 13]]},
                "chapters": [
                    {"bk_index": 1, "title": "Knowledge That Will Not Save You", "source_line_ranges": [[14, 22]]},
                    {"bk_index": 2, "title": "The Striving That Mercy Meets", "source_line_ranges": [[23, 69]]},
                ],
            }
        ),
        encoding="utf-8",
    )
    return bd


def test_chapter_one_absorbs_the_openings_source_lines(tmp_path: Path) -> None:
    """Without this the aligner places the folded prose WRONG rather than failing.

    It reads `source_line_ranges` to decide which Arabic a chapter's English came
    from. On `the-master-and-the-disciple` the six folded paragraphs were all
    pinned to source paragraph 3 as `verified`, and the paragraph mirror then
    fused them and the chapter's own first paragraph into one 623-word block.
    """
    bd = _ranged(tmp_path)

    apply_opening_fold(bd, log=lambda _m: None)
    toc = _toc(bd)

    assert toc["chapters"][0]["source_line_ranges"] == [[8, 22]]
    assert toc["chapters"][1]["source_line_ranges"] == [[23, 69]]  # untouched
    assert toc["preface"]["include"] is False


def test_absorbing_is_idempotent(tmp_path: Path) -> None:
    bd = _ranged(tmp_path)

    apply_opening_fold(bd, log=lambda _m: None)
    once = _toc(bd)
    apply_opening_fold(bd, log=lambda _m: None)

    assert _toc(bd) == once


def test_the_range_is_absorbed_even_when_the_assembly_already_folded(tmp_path: Path) -> None:
    """On a compose the assembly folds, so book.md arrives here already done and
    only the toc is left to correct. Skipping it there would leave exactly the
    mis-alignment this exists to prevent, on the compose route instead."""
    bd = _ranged(tmp_path)
    (bd / "book" / "book.md").write_text(
        "# T\n\n## 1. Knowledge That Will Not Save You\n\nThe opening, then the chapter.\n", encoding="utf-8"
    )

    report = apply_opening_fold(bd, log=lambda _m: None)

    assert report["folded"] is False
    assert report["absorbed"] is True
    assert _toc(bd)["chapters"][0]["source_line_ranges"] == [[8, 22]]


def test_a_book_with_no_preface_range_is_left_alone(tmp_path: Path) -> None:
    from _book_opening import absorb_preface_range

    bd = _book(tmp_path)  # toc has a preface title but no ranges

    assert absorb_preface_range(bd, log=lambda _m: None)["absorbed"] is False


def test_overlapping_ranges_coalesce_rather_than_duplicate() -> None:
    from _book_opening import _coalesce

    assert _coalesce([[591, 622], [572, 623]]) == [[572, 623]]
    assert _coalesce([[8, 13], [14, 22]]) == [[8, 22]]
    assert _coalesce([[8, 13], [20, 22]]) == [[8, 13], [20, 22]]


# --- an EXCLUDED preface is deleted, not folded ------------------------------


def test_an_excluded_preface_is_deleted_rather_than_folded(tmp_path: Path) -> None:
    """The per-book distinction the plan drew: an opening that is the source's own
    first words is folded into chapter 1; an opening ABOUT the book is dropped.

    `al-anwaar-al-lateefah` is the second kind, and folding it proved the point
    rather than settling it — its 272 words are 158 about "what kind of book you
    are holding", wrapped in an invocation chapter 1 ALREADY opens with, so the
    fold printed the ta'awwudh and basmala twice, four paragraphs apart.
    """
    bd = _book(tmp_path)
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "preface": {"include": False, "title": "A Letter Across the Centuries"},
                "chapters": [{"bk_index": 1, "title": "Knowledge That Will Not Save You"}],
            }
        ),
        encoding="utf-8",
    )

    report = apply_opening_fold(bd, log=lambda _m: None)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["dropped"] is True
    assert "## A Letter Across the Centuries" not in body
    assert "Know that one of the master's" not in body
    # every chapter untouched
    assert "## 1. Knowledge That Will Not Save You\n\nIn the Name of God, the Most Compassionate." in body
    assert "## 2. The Striving That Mercy Meets" in body


def test_the_delete_is_idempotent(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    (bd / "book" / "book-toc.json").write_text(
        json.dumps({"preface": {"include": False, "title": "A Letter Across the Centuries"}, "chapters": []}),
        encoding="utf-8",
    )

    apply_opening_fold(bd, log=lambda _m: None)
    once = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert apply_opening_fold(bd, log=lambda _m: None)["dropped"] is False
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == once


def test_an_excluded_preface_with_no_section_left_is_a_no_op(tmp_path: Path) -> None:
    """degrees and asaas are already in this state — nothing to delete."""
    bd = _book(tmp_path, body="# T\n\n## 1. Knowledge\n\nThe chapter.\n")
    (bd / "book" / "book-toc.json").write_text(
        json.dumps({"preface": {"include": False, "title": "A Letter Across the Centuries"}, "chapters": []}),
        encoding="utf-8",
    )

    assert apply_opening_fold(bd, log=lambda _m: None)["dropped"] is False
