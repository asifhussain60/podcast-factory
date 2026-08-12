"""The project-wide backlog (the Snag List): `_workspace/plan/pending-work.yaml`.

Work noticed in conversation is invisible once the session ends. These tests pin
the file that fixes that.

A book's own status card does NOT show this backlog (reversed 2026-08-12, Asif):
the card answers "how is this run going," a different question from "what is
still owed on the project" — mixing the two put pipeline-wide items (a corpus
translation, an unrelated book's compose gap) under a book's own progress card,
where they read as part of that run rather than the separate list they are. The
Snag List surfaces through its own dashboard view instead; see
`plan-dashboard/src/pages/snag-list.astro`.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _pending_work import (  # noqa: E402
    SCOPE_PIPELINE,
    STATUS_DOING,
    STATUS_DONE,
    STATUS_OPEN,
    backlog_path,
    open_items,
    read_items,
    resolve,
    write_items,
)


def seed(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / "pending-work.yaml"
    write_items(items, path)
    return path


def test_a_missing_backlog_is_an_empty_backlog(tmp_path: Path) -> None:
    assert read_items(tmp_path / "nope.yaml") == []


def test_an_unreadable_backlog_never_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("{[not yaml", encoding="utf-8")
    assert read_items(bad) == []


def test_finished_work_leaves_the_card(tmp_path: Path) -> None:
    path = seed(
        tmp_path,
        [
            {"id": "a", "scope": "book", "status": STATUS_OPEN, "title": "still owed"},
            {"id": "b", "scope": "book", "status": STATUS_DONE, "title": "already handled"},
        ],
    )
    assert [i["id"] for i in open_items("book", path)] == ["a"]


def test_in_progress_work_is_listed_first(tmp_path: Path) -> None:
    path = seed(
        tmp_path,
        [
            {"id": "a", "scope": "book", "status": STATUS_OPEN, "title": "queued"},
            {"id": "b", "scope": "book", "status": STATUS_DOING, "title": "happening now"},
        ],
    )
    assert [i["id"] for i in open_items("book", path)] == ["b", "a"]


def test_a_books_card_carries_pipeline_work_too(tmp_path: Path) -> None:
    """A pipeline gap stands between this book and being finished just as much."""
    path = seed(
        tmp_path,
        [
            {"id": "a", "scope": "the-book", "status": STATUS_OPEN, "title": "book work"},
            {"id": "b", "scope": SCOPE_PIPELINE, "status": STATUS_OPEN, "title": "machinery work"},
            {"id": "c", "scope": "another-book", "status": STATUS_OPEN, "title": "someone else's"},
        ],
    )
    assert {i["id"] for i in open_items("the-book", path)} == {"a", "b"}


def test_resolving_an_item_takes_it_off_the_card(tmp_path: Path) -> None:
    path = seed(tmp_path, [{"id": "a", "scope": "book", "status": STATUS_OPEN, "title": "owed"}])

    assert resolve("a", path) is True
    assert open_items("book", path) == []


def test_resolving_an_unknown_item_reports_failure(tmp_path: Path) -> None:
    path = seed(tmp_path, [{"id": "a", "scope": "book", "status": STATUS_OPEN, "title": "owed"}])
    assert resolve("nope", path) is False


def test_a_round_trip_preserves_every_field(tmp_path: Path) -> None:
    items = [{"id": "a", "scope": "book", "status": STATUS_OPEN, "title": "owed", "noticed": "2026-07-19"}]
    path = seed(tmp_path, items)
    assert read_items(path) == items


def test_the_repo_backlog_file_is_tracked_and_populated() -> None:
    """The shipped file is where the Snag List view reads from, and is not empty
    while work is outstanding — no card renders it any more (see module docstring)."""
    assert backlog_path().name == "pending-work.yaml"
    assert backlog_path().exists(), "the repo backlog is tracked, not created on demand"
    assert read_items(), "and it is not empty while work is outstanding"
