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
from fold_preface_edit import apply_fold, plan_fold

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
