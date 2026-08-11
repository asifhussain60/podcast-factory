#!/usr/bin/env python3
"""Every book must OPEN by telling the reader what is in it.

The defect this pins was found by Asif on 2026-08-11, on the first Sessions book
to reach the Podcast Factory Library. Chapter one was the speaker's own spoken
opening — his name, his years of study, greetings to the elders in the room, and
a request to his teacher for permission to begin. All of it true, all of it
rightly said aloud, and none of it a preface: a reader who opened the book was
told nothing whatever about what was in it.

The rule that came out of it applies to every route, not only this one: a
reading edition opens with an introduction addressed to the READER.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _book_frontmatter import INTRO_HEADING, facts_for_introduction, introduction_prompt  # noqa: E402
from _book_preface import preface_findings, sections, spoken_opening_markers  # noqa: E402

SPOKEN = """# Love Of The Prophet

## Personal Intro

Assalaam alaykum everyone. Thank you for taking the time to join these sessions.
For those of you who do not know me, my name is Asif Hussain, and I have been
studying religion since 2001. In today's session I would like us to step back.

## Love Based Religion

Love is a seed that must be nurtured.
"""

PREFACED = f"""# Love Of The Prophet

{INTRO_HEADING}

{"This series walks through five sessions on the person of the Prophet. " * 8}

## Love Based Religion

Love is a seed that must be nurtured.
"""


def _codes(book_md: str) -> list[str]:
    return [code for code, _ in preface_findings(book_md)]


def test_a_spoken_opening_is_reported_as_one() -> None:
    assert _codes(SPOKEN) == ["spoken-opening"]


def test_the_finding_says_WHICH_markers_it_saw() -> None:
    """A finding a person cannot check is a finding they have to take on trust."""
    _, sentence = preface_findings(SPOKEN)[0]
    assert "Personal Intro" in sentence
    assert "thank you for taking the time" in sentence


def test_a_real_preface_is_clean() -> None:
    assert preface_findings(PREFACED) == []


def test_a_book_that_opens_straight_into_chapter_one_is_reported() -> None:
    """Distinct from a spoken opening, and the cure is the same: write one."""
    plain = "# A Book\n\n## The First Teaching\n\nThe argument begins here.\n"
    assert _codes(plain) == ["missing-preface"]


def test_a_heading_with_nothing_under_it_is_not_a_preface() -> None:
    stub = f"# A Book\n\n{INTRO_HEADING}\n\nShort.\n\n## One\n\nBody.\n"
    assert _codes(stub) == ["empty-preface"]


def test_one_occasion_marker_is_not_enough() -> None:
    """ "Let us begin" opens plenty of legitimate prose. Two markers is the signal,
    so an ordinary chapter that happens to carry one is never called an opening."""
    ordinary = (
        "# A Book\n\n## The First Teaching\n\nLet us begin with what the word means.\n"
        + "The argument runs on from there. " * 20
    )
    assert _codes(ordinary) == ["missing-preface"]
    assert len(spoken_opening_markers(ordinary)) == 1


def test_sections_are_read_in_the_order_the_book_prints_them() -> None:
    titles = [t for t, _ in sections(SPOKEN)]
    assert titles == ["Personal Intro", "Love Based Religion"]


def test_deeper_headings_are_not_sections() -> None:
    """`###` is a heading INSIDE a chapter. Treating one as a section would make
    the first `###` of chapter one look like the book's opening."""
    nested = "# A Book\n\n## One\n\n### Inside\n\nBody.\n"
    assert [t for t, _ in sections(nested)] == ["One"]


# ---------------------------------------------------------------------------
# What the introduction is allowed to say about a book with no compose TOC
# ---------------------------------------------------------------------------


def test_the_chapter_list_is_read_from_the_book_when_there_is_no_toc(tmp_path) -> None:
    """`book-toc.json` is a COMPOSE artifact and the Sessions lane writes none.

    Without this fallback the brief's central instruction — say what the book is
    about, from the chapter list — has no chapter list to work from, and the
    introduction can only describe the book in the abstract.
    """
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text(PREFACED, encoding="utf-8")

    facts = facts_for_introduction(tmp_path)
    assert [c["title"] for c in facts["chapters"]] == ["Love Based Religion"]


def test_the_introduction_is_never_shown_its_own_output_as_a_chapter(tmp_path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text(PREFACED, encoding="utf-8")

    titles = [c["title"].lower() for c in facts_for_introduction(tmp_path)["chapters"]]
    assert "introduction to the book" not in titles


def test_a_spoken_book_is_briefed_as_a_series_of_talks_not_a_treatise() -> None:
    lecture = introduction_prompt({"source_medium": "audio_lecture", "title": "X"})
    printed = introduction_prompt({"source_medium": "printed_book", "title": "X"})

    assert "TRANSCRIPTS OF TALKS THAT WERE DELIVERED" in lecture
    assert "never a treatise" in lecture
    assert "TRANSCRIPTS OF TALKS" not in printed


def test_the_cap_and_the_prohibitions_are_the_same_either_way() -> None:
    """Only the SHAPE clause changes. An introduction to a set of talks is still
    front matter under one contract, not a second kind of document."""
    lecture = introduction_prompt({"source_medium": "audio_lecture"})
    printed = introduction_prompt({})

    for clause in ("ABSOLUTE PROHIBITIONS", "Do NOT invent an author", "UNDER 250 WORDS"):
        assert clause in lecture and clause in printed
