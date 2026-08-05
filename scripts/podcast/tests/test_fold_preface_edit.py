"""Tests for the one-time sidecar migration behind the front-matter fold.

The fold at assembly time is refused when a Composer edit is keyed to the
front-matter heading, because the replay would delete the folded opening a step
later without reporting it. This migration is the way out: merge the human's
front matter into the human's chapter 1 in the sidecar, so exactly one place
holds each piece of prose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _book_edits import load_edits, record_edit
from fold_preface_edit import apply_drop, apply_fold, coverage, plan_drop, plan_fold

_MACHINE = (
    "<!-- edition-intro:begin -->\nThis is a work of argument, not of story.\n"
    "\n### The book's own opening\n<!-- edition-intro:end -->"
)
_AUTHOR_OPENING = "The imamate is the pole and the foundation of religion."
_CHAPTER_ONE = "In the Name of God, the All-Compassionate, the All-Merciful."


def _book(tmp_path: Path, *, toc_preface: bool = True) -> Path:
    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "book_title": "Degrees",
                "preface": {"include": toc_preface, "title": "The Question of Leadership"},
                "chapters": [{"bk_index": 1, "title": "The Pole and Foundation of Religion"}],
            }
        ),
        encoding="utf-8",
    )
    record_edit(bd, chapter_key="the question of leadership", body_md=f"{_MACHINE}\n\n{_AUTHOR_OPENING}")
    record_edit(bd, chapter_key="the pole and foundation of religion", body_md=_CHAPTER_ONE)
    return bd


def _plan(bd: Path) -> dict:
    return plan_fold(bd, "The Question of Leadership", "The Pole and Foundation of Religion")


def test_the_authors_opening_moves_and_the_machine_preface_does_not(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    apply_fold(_plan(bd), log=lambda _m: None)
    edits = {e["chapter_key"]: e["body_md"] for e in load_edits(bd)["edits"]}

    assert "the question of leadership" not in edits
    merged = edits["the pole and foundation of religion"]
    assert merged.startswith(_AUTHOR_OPENING)
    assert _CHAPTER_ONE in merged
    # The pipeline's own preface is what this whole change removes — it does not
    # get carried into a chapter under cover of the migration.
    assert "a work of argument" not in merged
    assert "edition-intro" not in merged
    assert "The book's own opening" not in merged


def test_the_toc_entry_is_dropped_so_the_opening_is_not_emitted_twice(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    apply_fold(_plan(bd), log=lambda _m: None)
    toc = json.loads((bd / "book" / "book-toc.json").read_text(encoding="utf-8"))

    assert toc["preface"]["include"] is False


def test_keep_toc_preface_leaves_the_toc_alone(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    apply_fold(_plan(bd), keep_toc_preface=True, log=lambda _m: None)
    toc = json.loads((bd / "book" / "book-toc.json").read_text(encoding="utf-8"))

    assert toc["preface"]["include"] is True


def test_a_chapter_that_already_opens_on_the_text_refuses(tmp_path: Path) -> None:
    """Belt to the deletion's braces: a half-finished migration is not doubled.

    Deleting the front-matter edit is what normally makes a second run impossible.
    This covers the shape where the merge landed and the delete did not — an
    interrupted run, or a hand edit — where re-merging would print the opening
    twice inside one chapter.
    """
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="the pole and foundation of religion", body_md=f"{_AUTHOR_OPENING}\n\n{_CHAPTER_ONE}")

    with pytest.raises(SystemExit, match="already run"):
        _plan(bd)


def test_it_refuses_when_there_is_no_front_matter_edit(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    apply_fold(_plan(bd), log=lambda _m: None)

    with pytest.raises(SystemExit, match="nothing to migrate"):
        plan_fold(bd, "The Question of Leadership", "The Pole and Foundation of Religion")


def test_it_refuses_when_chapter_one_is_not_authored(tmp_path: Path) -> None:
    """Then no migration is needed — the assembly folds it directly."""
    bd = tmp_path / "b"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book-toc.json").write_text(json.dumps({"chapters": []}), encoding="utf-8")
    record_edit(bd, chapter_key="the question of leadership", body_md=_AUTHOR_OPENING)

    with pytest.raises(SystemExit, match="only needs migrating when BOTH"):
        plan_fold(bd, "The Question of Leadership", "The Pole and Foundation of Religion")


def test_no_words_are_lost_in_the_merge(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    plan = _plan(bd)

    assert plan["merged_words"] == plan["preface_words"] + plan["chapter_words"]
    assert plan["preface_words"] == len(_AUTHOR_OPENING.split())


# --- the DROP path: a front-matter section the chapters already say -----------
#
# `degrees-of-excellence` had a front-matter section carved out of source lines
# its chapter 1 range still covered, so the passage was rendered TWICE — once in
# plain transliteration as front matter and once with the Arabic script as the
# chapter. Folding would have printed it twice inside one chapter. Deleting it
# lost nothing, and the deletion had to be evidence-gated rather than asserted.

# The front-matter rendering: two sentences, Arabic given as transliteration.
_RENDERING_A = (
    "The imamate is the pole (qutb) and the foundation of religion (asas al-din). "
    "All religious and worldly affairs turn upon it, and it is a benefit for this present life."
)
# The chapter's rendering of the SAME source lines: one sentence, Arabic in script.
_RENDERING_B = (
    "The imamate is the pole (قُطْب) and the foundation of religion (أَسَاسُه), around which "
    "all religious and worldly affairs turn, and it is a benefit for this present life."
)


def test_coverage_sees_one_passage_rendered_twice() -> None:
    """The whole point: two renderings share a passage, not a sentence.

    They differ in the two ways that defeated the first metric — one side's two
    sentences are the other's one, and the same term appears as `qutb` here and
    `قُطْب` there — and this must still read as fully covered.
    """
    assert coverage(_RENDERING_A, _RENDERING_B)["ratio"] == 1.0


def test_a_parenthetical_transliteration_never_votes_against_its_own_match() -> None:
    """Guard the load-bearing step. With brackets compared, `asas al-din` is a
    word the chapter never says and `أَسَاسُه` is one this side cannot read, so the
    most distinctive term in the sentence argues AGAINST a match it should have
    settled."""
    from fold_preface_edit import _content_words

    assert "qutb" not in _content_words(_RENDERING_A)
    assert "imamate" in _content_words(_RENDERING_A)


def test_coverage_reports_a_passage_the_chapters_never_say() -> None:
    absent = "The compiler withheld this book from the press for forty years in the cave of taqiyya."

    result = coverage(f"{_RENDERING_A}\n\n{absent}", _RENDERING_B)

    assert result["already_said"] == 2
    assert any("cave of taqiyya" in sentence for _ratio, sentence in result["missing"])


def test_coverage_ignores_machine_fence_markers() -> None:
    assert coverage(f"<!-- editorial:begin -->\n{_RENDERING_A}", _RENDERING_B)["ratio"] == 1.0


def test_the_drop_deletes_the_edit_and_the_toc_entry(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    plan = plan_drop(bd, "The Question of Leadership")
    apply_drop(plan, log=lambda _m: None)
    edits = {e["chapter_key"] for e in load_edits(bd)["edits"]}
    toc = json.loads((bd / "book" / "book-toc.json").read_text(encoding="utf-8"))

    assert "the question of leadership" not in edits
    assert "the pole and foundation of religion" in edits  # every other chapter untouched
    assert toc["preface"]["include"] is False


def test_the_drop_measures_before_it_deletes(tmp_path: Path) -> None:
    """The evidence is computed and returned, so a human reads it first."""
    bd = _book(tmp_path)

    plan = plan_drop(bd, "The Question of Leadership")

    assert plan["preface_words"] == len(_AUTHOR_OPENING.split())
    assert "sentences" in plan["coverage"] and "missing" in plan["coverage"]


def test_the_drop_refuses_when_there_is_nothing_to_drop(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    apply_drop(plan_drop(bd, "The Question of Leadership"), log=lambda _m: None)

    with pytest.raises(SystemExit, match="nothing to drop"):
        plan_drop(bd, "The Question of Leadership")
