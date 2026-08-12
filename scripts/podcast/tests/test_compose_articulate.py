#!/usr/bin/env python3
"""`pf-compose-articulator`'s engine: chapter resolution, the fidelity gate,
the Sessions-lane guard, and the install path.

The first real install (done by hand, before this tool existed) got three
things wrong: it trusted the hand-off file's own heading instead of the
book's, it never ran the pipeline's own fidelity gate, and nothing guarded
against a live Composer. These tests pin the fixes for all three.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import compose_articulate as ca  # noqa: E402

BOOK = """# A Series

## Introduction to the Book

Apparatus, not a chapter.

## The Stages Of Love

The first level is attachment. It is a small thing, and it grows.

## Linguistic Meaning Of Allah

A different chapter about a different word entirely, unrelated to love.
"""


@pytest.fixture()
def book_dir(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    (tmp_path / "_system" / "sessions-articulation.json").write_text(json.dumps({"chapters": {}}), encoding="utf-8")
    (tmp_path / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_session\nnarrative_frame: first_person_expository\n",
        encoding="utf-8",
    )
    return tmp_path


def handoff(tmp_path: Path, text: str, name: str = "handoff.md") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ─── the Sessions-lane guard ──────────────────────────────────────────────


def test_refuses_a_book_with_no_sessions_ledger(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    with pytest.raises(PermissionError, match="Sessions-lane only"):
        ca._require_sessions_lane(tmp_path, "some-translation-edition")


def test_a_sessions_lane_book_is_accepted(book_dir: Path) -> None:
    ca._require_sessions_lane(book_dir, "surah-al-fateha")  # does not raise


# ─── chapter resolution — never the hand-off file's own heading ──────────


def test_resolves_by_exact_key(book_dir: Path) -> None:
    heading = ca.resolve_chapter(book_dir / "book" / "book.md", "the stages of love")
    assert heading == "The Stages Of Love"


def test_resolves_by_fragment(book_dir: Path) -> None:
    heading = ca.resolve_chapter(book_dir / "book" / "book.md", "Stages")
    assert heading == "The Stages Of Love"


def test_no_match_lists_every_chapter(book_dir: Path) -> None:
    with pytest.raises(ValueError, match="no chapter matches") as exc:
        ca.resolve_chapter(book_dir / "book" / "book.md", "nonexistent")
    assert "Linguistic Meaning Of Allah" in str(exc.value)


def test_the_handoff_files_own_heading_is_never_trusted(book_dir: Path, tmp_path: Path) -> None:
    """The exact bug the first manual install hit: the hand-off file said
    'Stages of Love' (lowercase 'of'), the book says 'Stages Of Love'."""
    off = handoff(tmp_path, "## Stages of Love\n\nA small attachment. It is a small thing, and it grows more.\n")
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["heading"] == "The Stages Of Love"  # the book's casing, not the hand-off's


# ─── the fidelity gate ─────────────────────────────────────────────────────


def test_a_faithful_rewrite_is_clean(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["clean"] is True
    assert result["findings"] == []


def test_unrelated_content_is_refused(book_dir: Path, tmp_path: Path) -> None:
    """Installing under the wrong chapter — the content shares nothing with
    the chapter it would replace."""
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.check(book_dir, "linguistic meaning of allah", off, log=lambda *_: None)
    assert result["clean"] is False
    assert result["findings"]


# ─── install ───────────────────────────────────────────────────────────────


def test_install_refuses_on_a_finding_without_force(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.install(book_dir, "linguistic meaning of allah", off, log=lambda *_: None)
    assert result["installed"] is False
    # book.md must be untouched
    assert "A different chapter about a different word entirely" in (book_dir / "book" / "book.md").read_text()


def test_install_writes_book_md_and_records_the_composer_edit(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    result = ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["installed"] is True

    text = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    assert "The first level is attachment" in text
    assert "## Linguistic Meaning Of Allah" in text  # the next chapter survives untouched

    edits = json.loads((book_dir / "_system" / "composer-edits.json").read_text(encoding="utf-8"))
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert "the stages of love" in keys

    ledger = json.loads((book_dir / "_system" / "sessions-articulation.json").read_text(encoding="utf-8"))
    assert ledger["chapters"]["the stages of love"]["status"] == "adapted"

    assert (book_dir / "book" / "book.md.bak").exists()


def test_force_installs_despite_a_finding(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.install(book_dir, "linguistic meaning of allah", off, force=True, log=lambda *_: None)
    assert result["installed"] is True
    assert result["findings"]  # still reported, never silently dropped
    text = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    assert "The first level is attachment." in text


def test_installing_twice_does_not_duplicate_the_composer_edit(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    edits = json.loads((book_dir / "_system" / "composer-edits.json").read_text(encoding="utf-8"))
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert keys.count("the stages of love") == 1
