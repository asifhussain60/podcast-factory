"""Tests for the retired machine preface and the cleanup that survives it.

The authoring half of this module was removed on 2026-08-03 — no book gets a
machine-written preface any more. What is left is the removal, and it has to keep
working for a long time: five editions carry a fence the retired path wrote, and
one carries it inside a Composer edit that is replayed on every compose.
"""

from __future__ import annotations

import re
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


def test_the_fence_kind_stays_registered() -> None:
    """De-registering it while books carry fences would print the markers as text —
    the 2026-07-21 regression run backwards. See test_fence_kinds_cross_language."""
    import _book_frontmatter as fm

    assert fm.INTRO_OPEN == "<!-- edition-intro:begin -->"


# --- the short, honestly-titled introduction (Asif, 2026-08-03) ---------------


_SHORT = " ".join(["The book is a dialogue between a teacher and a seeker."] * 18)


def test_the_introduction_is_its_own_unnumbered_section_above_chapter_one() -> None:
    """Unnumbered is structural, not typographic: every entry in the toc's chapter
    list carries the source lines it was translated from, and an introduction has
    none. Numbering it would also renumber every chapter in the book."""
    from _book_frontmatter import INTRO_HEADING, inject_introduction

    book = "# Title\n\n## 1. The Call and the Covenant\n\nThe chapter's own first sentence.\n"

    out = inject_introduction(book, _SHORT)

    assert out.index(INTRO_HEADING) < out.index("## 1. The Call and the Covenant")
    assert "## 1. The Call and the Covenant\n\nThe chapter's own first sentence." in out
    assert not re.search(r"(?m)^##\s+\d+\.\s+Introduction", out)


def test_the_cap_is_250_words_and_an_essay_is_refused() -> None:
    from _book_frontmatter import MAX_INTRO_WORDS, gate_introduction

    assert MAX_INTRO_WORDS == 250
    assert gate_introduction(" ".join(["word"] * 400))[0] is False
    assert any("essay" in r for r in gate_introduction(" ".join(["word"] * 400))[1])
    assert gate_introduction(_SHORT)[0] is True


def test_the_gate_refuses_a_stub_an_asserted_absence_and_bullets() -> None:
    from _book_frontmatter import gate_introduction

    assert not gate_introduction("Too short.")[0]
    assert any("absence" in r for r in gate_introduction(_SHORT + " What it never says is why.")[1])
    assert any("bullets" in r for r in gate_introduction("- a bullet\n" + _SHORT)[1])


def test_injection_is_idempotent_and_the_strip_leaves_no_orphan() -> None:
    from _book_frontmatter import INTRO_HEADING, inject_introduction, strip_introduction

    book = "# Title\n\n## 1. The Call\n\nThe chapter.\n"

    once = inject_introduction(book, _SHORT)
    twice = inject_introduction(once, _SHORT)

    assert once == twice and twice.count(INTRO_HEADING) == 1
    # Stripped, no orphan heading is left for the next run to fill back in, and
    # the chapters are untouched.
    assert strip_introduction(once) == book


def test_no_numbered_chapter_means_no_introduction(tmp_path: Path) -> None:
    """Refusing beats guessing a position in a book whose shape we do not know."""
    from _book_frontmatter import INTRO_HEADING, inject_introduction

    assert INTRO_HEADING not in inject_introduction("# T\n\n## Appendix\n\nText.\n", _SHORT)


def test_the_register_comes_from_the_articulation_standard_not_a_second_copy() -> None:
    """Asif's rule: the introduction must not stand out as a different prose. A
    register defined twice is how it drifts into a different voice later."""
    from _book_frontmatter import introduction_prompt
    from _book_voice_prompts import ARTICULATION_REGISTER

    prompt = introduction_prompt({"title": "A Book"})

    assert ARTICULATION_REGISTER in prompt
    assert "REQ-BA-010" in prompt


def test_the_brief_shows_the_book_its_own_prose_to_match(tmp_path: Path) -> None:
    from _book_frontmatter import introduction_prompt, style_exemplar

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text(
        "# T\n\n## 1. The Call\n\n> a quotation, skipped\n\nThe chapter's own articulated prose.\n",
        encoding="utf-8",
    )

    exemplar = style_exemplar(bd)

    assert exemplar == "The chapter's own articulated prose."
    assert exemplar in introduction_prompt({}, exemplar=exemplar)


def test_an_author_the_files_do_not_record_is_never_invented() -> None:
    """Three of the five Islamic editions record no author, and for al-anwaar that
    is the truth rather than a gap — it was compiled from many sources."""
    from _book_frontmatter import introduction_prompt

    prompt = introduction_prompt({"title": "A Book"})

    assert "If no author is recorded" in prompt
    assert "no single author" in prompt


def test_a_failed_author_never_takes_down_a_compose(tmp_path: Path) -> None:
    from _book_frontmatter import apply_introduction, author_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## 1. The Call\n\nThe chapter.\n", encoding="utf-8")

    def explode(_prompt: str) -> str:
        raise RuntimeError("model unavailable")

    assert author_introduction(bd, log=lambda _m: None, author=explode) == ""
    assert apply_introduction(bd, log=lambda _m: None, author=explode)["applied"] is False
    assert (bd / "book" / "book.md").read_text(encoding="utf-8").endswith("The chapter.\n")


def test_a_rejected_answer_falls_back_to_the_cached_one(tmp_path: Path) -> None:
    """A book that HAS a good introduction must not lose it to one bad re-run."""
    from _book_frontmatter import CACHE_NAME, author_introduction

    bd = _book(tmp_path)
    (bd / "_system" / CACHE_NAME).write_text(_SHORT + "\n", encoding="utf-8")

    assert author_introduction(bd, log=lambda _m: None, force=True, author=lambda _p: "Too short.") == _SHORT


def test_the_model_is_asked_once_per_book(tmp_path: Path) -> None:
    from _book_frontmatter import author_introduction

    bd = _book(tmp_path)
    calls: list[str] = []

    def author(prompt: str) -> str:
        calls.append(prompt)
        return _SHORT

    author_introduction(bd, log=lambda _m: None, author=author)
    author_introduction(bd, log=lambda _m: None, author=author)

    assert len(calls) == 1


def test_the_earlier_longer_introduction_is_reused_as_raw_material(tmp_path: Path) -> None:
    from _book_frontmatter import CACHE_NAME, author_introduction

    bd = _book(tmp_path)
    (bd / "_system" / CACHE_NAME).write_text(" ".join(["essay"] * 400) + "\n", encoding="utf-8")
    seen: list[str] = []

    author_introduction(bd, log=lambda _m: None, author=lambda p: (seen.append(p), _SHORT)[1])

    assert "RAW MATERIAL" in seen[0]
    assert "essay essay" in seen[0]


def test_apply_writes_the_introduction_into_the_book(tmp_path: Path) -> None:
    from _book_frontmatter import INTRO_HEADING, apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## 1. The Call\n\nThe chapter.\n", encoding="utf-8")

    report = apply_introduction(bd, log=lambda _m: None, author=lambda _p: _SHORT)
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["applied"] is True and report["words"] == len(_SHORT.split())
    assert body.index(INTRO_HEADING) < body.index("## 1. The Call")


def test_an_over_length_answer_is_retried_once_with_the_finding_named(tmp_path: Path) -> None:
    """The first three books came back at 256, 262 and 270 against a 250 limit.

    That is a trim, not a rewrite, and refusing outright threw away a good
    introduction over two percent. The retry names the actual finding, because a
    retry that repeats the original brief re-runs the model against instructions
    it already followed.
    """
    from _book_frontmatter import author_introduction

    bd = _book(tmp_path)
    prompts: list[str] = []

    def author(prompt: str) -> str:
        prompts.append(prompt)
        return " ".join(["word"] * 400) if len(prompts) == 1 else _SHORT

    assert author_introduction(bd, log=lambda _m: None, author=author) == _SHORT
    assert len(prompts) == 2
    assert "failed these checks" in prompts[1] and "essay" in prompts[1]


def test_the_retry_happens_at_most_once(tmp_path: Path) -> None:
    from _book_frontmatter import author_introduction

    bd = _book(tmp_path)
    calls: list[str] = []

    assert (
        author_introduction(bd, log=lambda _m: None, author=lambda p: (calls.append(p), " ".join(["word"] * 400))[1])
        == ""
    )
    assert len(calls) == 2


# --- the reader must be able to SEE it, and their edit must win ---------------


def test_the_introduction_carries_no_machine_marker_at_all() -> None:
    """Two defects, one root: the fence.

    The Composer skips any heading INSIDE an `edition-intro` span, so an
    introduction fenced heading-and-all never appeared in the chapter list — Asif
    looked for it and it was not there. Moved outside, it appeared, and the
    editor then rendered the marker as a visible label: the book's first line read
    `edition-intro:begin`. The fence's only job was telling the strip what to
    remove, and the section regex does that from the heading.
    """
    from _book_frontmatter import INTRO_HEADING, inject_introduction

    out = inject_introduction("# T\n\n## 1. The Call\n\nThe chapter.\n", _SHORT)

    assert "edition-intro" not in out
    assert out.index(INTRO_HEADING) < out.index("## 1. The Call")
    assert _SHORT in out


def test_the_section_is_stripped_even_when_the_fence_is_gone() -> None:
    """A save that loses the markers must not produce a SECOND introduction."""
    from _book_frontmatter import INTRO_HEADING, strip_introduction

    unfenced = f"# T\n\n{INTRO_HEADING}\n\nAn introduction with no markers left.\n\n## 1. The Call\n\nThe chapter.\n"

    out = strip_introduction(unfenced)

    assert INTRO_HEADING not in out
    assert "An introduction with no markers" not in out
    assert "## 1. The Call\n\nThe chapter." in out


def test_the_authors_own_introduction_is_never_re_written(tmp_path: Path) -> None:
    """Without this the sequence discards their work in silence EVERY run: the
    replay restores it at 5a, `clear_introduction` strips it at 5c, and this step
    writes the cached machine text back at 5e."""
    from _book_edits import record_edit
    from _book_frontmatter import CACHE_NAME, apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## 1. The Call\n\nThe chapter.\n", encoding="utf-8")
    (bd / "_system" / CACHE_NAME).write_text(_SHORT + "\n", encoding="utf-8")
    record_edit(bd, chapter_key="introduction to the book", body_md="The author's own introduction, in their words.")

    calls: list[str] = []
    report = apply_introduction(bd, log=lambda _m: None, author=lambda p: (calls.append(p), _SHORT)[1])
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert report["authored"] is True
    assert "The author's own introduction, in their words." in body
    assert _SHORT not in body  # the cached machine text did not come back
    assert calls == []  # and no model was asked


def test_an_authored_introduction_is_not_held_to_the_word_cap(tmp_path: Path) -> None:
    """The cap holds a MODEL to a brief. A human who writes four hundred words has
    decided something, and refusing it would be the pipeline overruling its author."""
    from _book_edits import record_edit
    from _book_frontmatter import apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## 1. The Call\n\nThe chapter.\n", encoding="utf-8")
    long_intro = " ".join(["deliberate"] * 400)
    record_edit(bd, chapter_key="introduction to the book", body_md=long_intro)

    apply_introduction(bd, log=lambda _m: None, author=lambda _p: _SHORT)

    assert long_intro in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_replacing_an_authored_introduction_stays_idempotent(tmp_path: Path) -> None:
    from _book_edits import record_edit
    from _book_frontmatter import INTRO_HEADING, apply_introduction

    bd = _book(tmp_path)
    (bd / "book" / "book.md").write_text("# T\n\n## 1. The Call\n\nThe chapter.\n", encoding="utf-8")
    record_edit(bd, chapter_key="introduction to the book", body_md="The author's own introduction.")

    apply_introduction(bd, log=lambda _m: None)
    once = (bd / "book" / "book.md").read_text(encoding="utf-8")
    apply_introduction(bd, log=lambda _m: None)

    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == once
    assert once.count(INTRO_HEADING) == 1


def test_the_earlier_shape_leaves_no_orphan_marker() -> None:
    """Books written this morning fenced the heading INSIDE the span.

    Strip by section first and the closing marker leaves with the section, which
    strands the opening marker above it — unpairable, and therefore permanent.
    All three finished books came back carrying exactly that. Fence first.
    """
    from _book_frontmatter import INTRO_CLOSE, INTRO_HEADING, INTRO_OPEN, strip_introduction

    earlier = (
        f"# T\n\n{INTRO_OPEN}\n{INTRO_HEADING}\n\nThe introduction.\n{INTRO_CLOSE}\n\n## 1. The Call\n\nThe chapter.\n"
    )

    out = strip_introduction(earlier)

    assert "edition-intro" not in out
    assert INTRO_HEADING not in out and "The introduction." not in out
    assert "## 1. The Call\n\nThe chapter." in out


def test_a_book_carrying_the_earlier_shape_re_injects_cleanly() -> None:
    from _book_frontmatter import INTRO_CLOSE, INTRO_HEADING, INTRO_OPEN, inject_introduction

    earlier = f"# T\n\n{INTRO_OPEN}\n{INTRO_HEADING}\n\nOld text.\n{INTRO_CLOSE}\n\n## 1. The Call\n\nThe chapter.\n"

    out = inject_introduction(earlier, _SHORT)

    assert "edition-intro" not in out  # the legacy fence leaves and none replaces it
    assert out.count(INTRO_HEADING) == 1
    assert "Old text." not in out and _SHORT in out


def test_a_title_page_attribution_is_found_however_it_is_phrased(tmp_path: Path) -> None:
    """`^Author:` alone missed `asaas-al-taveel`, whose title page reads "Authored
    by the Ismaili Da'i al-Nu'man ...". With no attribution in the facts the model
    correctly wrote around the absence — and printed "No single author is named
    here" in the finished edition of a book whose first page names him."""
    from _book_frontmatter import facts_for_introduction

    bd = _book(tmp_path)
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        "<!-- page 1 -->\n\n**Asas al-Ta'wil**\n\n"
        "Authored by the Ismaili Da'i al-Nu'man ibn Hayyun al-Tamimi\n"
        "Judge of the Fatimid Dynasty\n"
        "Died 363 AH\n",
        encoding="utf-8",
    )

    line = facts_for_introduction(bd)["source_attribution_line"]

    assert "al-Nu'man" in line
    assert "Judge of the Fatimid Dynasty" in line and "Died 363 AH" in line


def test_the_books_own_first_sentence_is_not_mistaken_for_attribution(tmp_path: Path) -> None:
    """A full sentence under the attribution is the book STARTING."""
    from _book_frontmatter import facts_for_introduction

    bd = _book(tmp_path)
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        "The Book\n\nAuthor: Sayyidina Ja'far ibn Mansur al-Yaman\n"
        "In the name of God, the Most Gracious, the Most Merciful.\n",
        encoding="utf-8",
    )

    line = facts_for_introduction(bd)["source_attribution_line"]

    assert line == "Author: Sayyidina Ja'far ibn Mansur al-Yaman"
