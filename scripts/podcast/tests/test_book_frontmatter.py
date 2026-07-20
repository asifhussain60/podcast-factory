"""Tests for the edition introduction — apparatus, authored, not translated."""

from __future__ import annotations

from pathlib import Path

from _book_frontmatter import (
    INTRO_CLOSE,
    INTRO_OPEN,
    facts_for_introduction,
    gate_introduction,
    inject_introduction,
    strip_introduction,
)

_GOOD = " ".join(["This edition translates a tenth-century teaching dialogue."] * 25)


def _book(tmp_path: Path) -> Path:
    bd = tmp_path / "book"
    (bd / "_system" / "source" / "text").mkdir(parents=True)
    (bd / "book").mkdir(parents=True)
    return bd


def test_facts_come_from_files_and_absences_are_omitted(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    (bd / "meta.yml").write_text(
        "title: The Master and the Disciple\ndoctrinal_context:\n  author: Ja'far\n  school: Ismaili\n",
        encoding="utf-8",
    )
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        "The Book\n\nAuthor: Sayyidina Ja'far ibn Mansur al-Yaman\n\n(1) We have been informed…\n",
        encoding="utf-8",
    )

    facts = facts_for_introduction(bd)

    assert facts["title"] == "The Master and the Disciple"
    assert facts["doctrinal_context"]["school"] == "Ismaili"
    # The source's OWN attribution — stronger evidence than a note about it.
    assert "Sayyidina Ja'far" in facts["source_attribution_line"]
    # Nothing invented for what the files do not carry.
    assert "chapters" not in facts
    assert "glossary_terms" not in facts


def test_a_book_with_no_files_invents_nothing_about_its_content(tmp_path: Path) -> None:
    facts = facts_for_introduction(_book(tmp_path))

    # The route knobs always resolve — they have defaults and describe the RUN,
    # not the book — so they are present. Nothing about the work itself is.
    assert facts["slug"] == "book"
    assert set(facts) - {"slug"} == {"narrative_frame", "book_voice", "book_augmentation"}


def test_the_gate_refuses_an_asserted_absence() -> None:
    # Both false claims an audit caught in a hand-written introduction were of
    # this shape: telling the reader what the book never says, which is an
    # absence the author cannot have verified.
    ok, reasons = gate_introduction(_GOOD + " What it never says outright is that they belong together.")

    assert not ok
    assert any("absence" in r for r in reasons)


def test_the_gate_refuses_an_essay_and_a_stub() -> None:
    assert not gate_introduction("Too short.")[0]
    assert not gate_introduction(" ".join(["word"] * 900))[0]
    assert gate_introduction(_GOOD)[0]


def test_injection_places_it_above_the_sources_own_opening() -> None:
    book = "# Title\n\n## How to Read This\n\nWe have been informed that some believers came…\n"

    out = inject_introduction(book, _GOOD)

    assert out.index(INTRO_OPEN) < out.index("We have been informed")
    assert "### The book's own opening" in out
    assert out.index("### The book's own opening") < out.index("We have been informed")


def test_injection_is_idempotent() -> None:
    book = "# Title\n\n## How to Read This\n\nThe source's first words.\n"

    once = inject_introduction(book, _GOOD)
    twice = inject_introduction(once, _GOOD)

    assert once == twice
    assert twice.count(INTRO_OPEN) == 1


def test_a_rejected_introduction_leaves_the_book_alone() -> None:
    book = "# Title\n\n## How to Read This\n\nThe source's first words.\n"

    out = inject_introduction(book, "Too short to orient anyone.")

    assert INTRO_OPEN not in out
    assert "The source's first words." in out


def test_strip_removes_a_previous_injection_cleanly() -> None:
    book = "# Title\n\n## How to Read This\n\nThe source's first words.\n"

    assert strip_introduction(inject_introduction(book, _GOOD)).count(INTRO_CLOSE) == 0
