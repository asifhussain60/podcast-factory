"""Tests for the retired machine preface and the cleanup that survives it.

The authoring half of this module was removed on 2026-08-03 — no book gets a
machine-written preface any more. What is left is the removal, and it has to keep
working for a long time: five editions carry a fence the retired path wrote, and
one carries it inside a Composer edit that is replayed on every compose.
"""

from __future__ import annotations

from pathlib import Path

from _book_frontmatter import (
    INTRO_CLOSE,
    INTRO_OPEN,
    clear_introduction,
    strip_introduction,
)

_INTRO = " ".join(["This edition translates a tenth-century teaching dialogue."] * 20)


def _book(tmp_path: Path) -> Path:
    bd = tmp_path / "book"
    (bd / "_system" / "source" / "text").mkdir(parents=True)
    (bd / "book").mkdir(parents=True)
    return bd


def _with_preface(source_opening: str = "The source's first words.") -> str:
    """A book.md in the shape the retired injector produced."""
    return (
        "# Title\n\n## How to Read This\n\n"
        f"{INTRO_OPEN}\n{_INTRO}\n\n### The book's own opening\n{INTRO_CLOSE}\n\n"
        f"{source_opening}\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"
    )


def test_the_machine_preface_goes_and_the_source_opening_stays() -> None:
    out = strip_introduction(_with_preface())

    assert INTRO_OPEN not in out and INTRO_CLOSE not in out
    assert "This edition translates" not in out
    # Everything the SOURCE said is untouched — that is the whole distinction.
    assert "The source's first words." in out
    assert "The chapter's own first sentence." in out


def test_the_invented_subheading_goes_too() -> None:
    """`### The book's own opening` names a distinction the edition no longer draws.

    It normally sits inside the fence and leaves with it. It is asserted
    separately because `the-master-and-the-disciple` was split by hand before the
    fence existed, so the label can also stand alone.
    """
    hand_split = "# Title\n\n## How to Read This\n\nA human's note.\n\n### The book's own opening\n\nSource words.\n"

    out = strip_introduction(hand_split)

    assert "The book's own opening" not in out
    assert "Source words." in out


def test_stripping_is_idempotent() -> None:
    once = strip_introduction(_with_preface())

    assert strip_introduction(once) == once


def test_a_book_that_never_had_one_is_left_byte_identical() -> None:
    clean = "# Title\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"

    assert strip_introduction(clean) == clean


def test_a_flattened_fence_is_still_found() -> None:
    """A Composer save serializes the HTML comment back as a bare text line.

    A pass that cannot see the fence does not fail loudly — it leaves the machine
    preface on the page and reports success.
    """
    flattened = (
        "# Title\n\n## How to Read This\n\nedition-intro:begin\n"
        f"{_INTRO}\nedition-intro:end\n\nThe source's first words.\n"
    )

    out = strip_introduction(flattened)

    assert "This edition translates" not in out
    assert "The source's first words." in out


def test_clear_writes_the_file_and_reports_the_words(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text(_with_preface(), encoding="utf-8")

    report = clear_introduction(bd, log=lambda _m: None)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["removed"] is True
    assert report["words"] > 0
    assert INTRO_OPEN not in body
    assert "The source's first words." in body


def test_clear_on_an_already_clean_book_writes_nothing(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    clean = "# Title\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"
    (bd / "book" / "book.md").write_text(clean, encoding="utf-8")
    before = (bd / "book" / "book.md").stat().st_mtime_ns

    report = clear_introduction(bd, log=lambda _m: None)

    assert report == {"removed": False}
    assert (bd / "book" / "book.md").stat().st_mtime_ns == before
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == clean


def test_clear_without_a_book_never_raises(tmp_path: Path) -> None:
    assert clear_introduction(_book(tmp_path), log=lambda _m: None) == {"removed": False, "reason": "no book.md"}


def test_the_authoring_path_is_really_gone() -> None:
    """Named so a future reader sees the retirement was deliberate, not a slip.

    The `edition-intro` fence KIND stays registered (see
    `test_fence_kinds_cross_language.py`) — de-registering it while books still
    carry fences would make those markers print as literal text.
    """
    import _book_frontmatter as fm

    for gone in ("author_introduction", "apply_introduction", "inject_introduction", "introduction_prompt"):
        assert not hasattr(fm, gone), f"{gone} was retired on 2026-08-03"
    assert fm.INTRO_OPEN == "<!-- edition-intro:begin -->"
