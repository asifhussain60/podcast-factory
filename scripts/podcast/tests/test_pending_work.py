"""The backlog a status card prints.

Work noticed in conversation is invisible once the session ends. These tests pin
the file that fixes that, and the card's obligation to show it.
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
from book_status_card import build_card, render_card  # noqa: E402


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


# ─── the card's obligation ───────────────────────────────────────────────────
def test_the_card_prints_the_backlog_inside_its_frame(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    text = render_card({**build_card(bd), "pending": [{"status": STATUS_DOING, "title": "a thing still owed"}]})
    lines = text.split("\n")

    assert "Pending" in text
    assert "a thing still owed" in text
    assert {len(line) for line in lines} == {52}, "the backlog must not break the frame"


def test_a_long_backlog_is_capped_with_a_count(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )
    many = [{"status": STATUS_OPEN, "title": f"item {n}"} for n in range(9)]

    text = render_card({**build_card(bd), "pending": many})

    assert "+4 more" in text, "a card that scrolls stops being a card"


def test_an_empty_backlog_leaves_the_card_alone(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )
    assert "Pending" not in render_card({**build_card(bd), "pending": []})


def test_the_repo_backlog_is_where_the_card_looks() -> None:
    """The shipped file and the reader must agree, or the card shows an empty list."""
    assert backlog_path().name == "pending-work.yaml"
    assert backlog_path().exists(), "the repo backlog is tracked, not created on demand"
    assert read_items(), "and it is not empty while work is outstanding"
