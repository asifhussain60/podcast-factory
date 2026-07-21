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


def test_it_never_gets_injected_into_a_numbered_chapter() -> None:
    """With `toc.preface.include` false, the first `## ` section IS Chapter 1.

    The introduction used to be dropped into that chapter's body regardless, which
    manufactured a "the book's own opening" subheading in the middle of Chapter 1
    and told the reader the chapter's first page was front matter.
    """
    book = "# Title\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"

    out = inject_introduction(book, _GOOD)

    assert out.index(INTRO_OPEN) < out.index("## 1. The Call and the Covenant")
    assert "### The book's own opening" not in out
    # The chapter is intact and still opens on its own words.
    assert "## 1. The Call and the Covenant\n\nThe chapter's own first sentence." in out


def test_injection_above_a_numbered_chapter_is_idempotent() -> None:
    book = "# Title\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"

    once = inject_introduction(book, _GOOD)
    twice = inject_introduction(once, _GOOD)

    assert once == twice
    assert twice.count(INTRO_OPEN) == 1


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


def test_the_brief_carries_only_facts_read_from_files() -> None:
    from _book_frontmatter import introduction_prompt

    prompt = introduction_prompt({"title": "A Book", "doctrinal_context": {"author": "Someone"}})

    assert "this list is exhaustive" in prompt
    assert '"author": "Someone"' in prompt
    # The two prohibitions earned by real false claims.
    assert "never says" in prompt
    assert "unvowelled" in prompt


def test_a_failed_author_never_takes_down_a_compose(tmp_path: Path) -> None:
    # A book without an introduction is missing apparatus — the state every book
    # was in before this existed. Losing a finished translation over it would be
    # the worse trade by far.
    from _book_frontmatter import apply_introduction, author_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## Preface\n\nSource words.\n", encoding="utf-8")

    def explode(_prompt: str) -> str:
        raise RuntimeError("model unavailable")

    assert author_introduction(bd, log=lambda _m: None, author=explode) == ""
    assert apply_introduction(bd, log=lambda _m: None, author=explode) == {
        "applied": False,
        "reason": "no introduction",
    }
    assert (bd / "book" / "book.md").read_text(encoding="utf-8").endswith("Source words.\n")


def test_a_good_introduction_is_cached_and_reused(tmp_path: Path) -> None:
    from _book_frontmatter import CACHE_NAME, author_introduction

    bd = _book(tmp_path)
    calls = []

    def author(prompt: str) -> str:
        calls.append(prompt)
        return _GOOD

    assert author_introduction(bd, log=lambda _m: None, author=author) == _GOOD
    assert (bd / "_system" / CACHE_NAME).exists()
    assert author_introduction(bd, log=lambda _m: None, author=author) == _GOOD
    assert len(calls) == 1  # second run reused the cache


def test_apply_writes_the_introduction_into_the_book(tmp_path: Path) -> None:
    from _book_frontmatter import apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## Preface\n\nSource words.\n", encoding="utf-8")

    report = apply_introduction(bd, log=lambda _m: None, author=lambda _p: _GOOD)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["applied"] is True
    assert INTRO_OPEN in body
    assert body.index(INTRO_OPEN) < body.index("Source words.")


def test_a_hand_split_front_matter_is_left_alone(tmp_path: Path) -> None:
    # One book was given its introduction by hand before this step existed,
    # stored as a Composer edit and replayed on every compose. Authoring another
    # would print two introductions, one of them a stranger's.
    from _book_frontmatter import apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text(
        "# T\n\n## Preface\n\nA human's introduction.\n\n### The book's own opening\n\nSource words.\n",
        encoding="utf-8",
    )

    report = apply_introduction(bd, log=lambda _m: None, author=lambda _p: _GOOD)

    assert report == {"applied": False, "reason": "front matter already split by hand"}
    assert "A human's introduction." in (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert INTRO_OPEN not in (bd / "book" / "book.md").read_text(encoding="utf-8")
