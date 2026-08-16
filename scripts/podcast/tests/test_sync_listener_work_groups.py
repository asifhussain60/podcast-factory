#!/usr/bin/env python3
"""Grouping SQL for `sync_listener_work_groups.py`, executed against real SQLite.

Mirrors `test_publish_to_listener.py`'s pattern (real migrations, real sqlite —
a passing grep proves nothing about whether the emitted SQL actually runs and
does the right thing). Three properties matter most here because they are the
whole point of the script: (1) a fresh, ungrouped pair of volumes gets linked
and a work parent created, (2) re-running against the now-grouped state is a
genuine no-op — no duplicate rows, nothing rewritten, and (3) a volume already
grouped under a DIFFERENT work_slug is left alone rather than clobbered.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync_listener_work_groups import Group, plan_for_group  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parents[3] / "listener" / "migrations"


def db_with_schema() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    for path in sorted(MIGRATIONS.glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))
    return conn


def units_from(conn: sqlite3.Connection) -> dict:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT slug, kind, work_slug, sort_order, bucket, title FROM content_unit").fetchall()
    return {r["slug"]: dict(r) for r in rows}


def seed_two_volumes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES "
        "('vol-a', 'Islamic', 'Volume A', 'book', NULL, 10, 'published')"
    )
    conn.execute(
        "INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES "
        "('vol-b', 'Islamic', 'Volume B', 'book', NULL, 20, 'published')"
    )
    conn.commit()


def a_group() -> Group:
    return Group(
        work_slug="a-work",
        title="A Work",
        bucket="Islamic",
        volumes=[{"slug": "vol-a", "order": 1}, {"slug": "vol-b", "order": 2}],
        source=Path("content/Islamic/_listener-groups/a-work.yml"),
    )


def test_fresh_pair_gets_grouped_and_a_parent_row_created():
    conn = db_with_schema()
    seed_two_volumes(conn)

    statements, notes = plan_for_group(a_group(), units_from(conn))
    assert notes == []
    for s in statements:
        conn.executescript(s)
    conn.commit()

    units = units_from(conn)
    assert units["a-work"]["kind"] == "work"
    assert units["a-work"]["sort_order"] == 9  # one below the lowest volume's sort_order
    assert units["vol-a"]["work_slug"] == "a-work"
    assert units["vol-b"]["work_slug"] == "a-work"
    # Privilege bits untouched — never named in the emitted SQL at all.
    assert all("status" not in s and "open_to_all" not in s for s in statements)


def test_rerun_against_already_grouped_state_is_a_true_no_op():
    conn = db_with_schema()
    seed_two_volumes(conn)
    statements, _ = plan_for_group(a_group(), units_from(conn))
    for s in statements:
        conn.executescript(s)
    conn.commit()
    before = units_from(conn)

    statements_again, notes_again = plan_for_group(a_group(), units_from(conn))
    assert statements_again == []
    assert notes_again == []

    after = units_from(conn)
    assert before == after


def test_volume_already_grouped_elsewhere_is_reported_not_overwritten():
    conn = db_with_schema()
    seed_two_volumes(conn)
    conn.execute("UPDATE content_unit SET work_slug = 'someone-else' WHERE slug = 'vol-a'")
    conn.commit()

    statements, notes = plan_for_group(a_group(), units_from(conn))
    assert any("someone-else" in n for n in notes)
    assert not any("vol-a" in s and "UPDATE" in s for s in statements)


def test_slug_collision_with_a_non_work_row_refuses_to_touch_anything():
    conn = db_with_schema()
    seed_two_volumes(conn)
    conn.execute(
        "INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order) VALUES "
        "('a-work', 'Islamic', 'Unrelated Book', 'book', NULL, 5)"
    )
    conn.commit()

    statements, notes = plan_for_group(a_group(), units_from(conn))
    assert statements == []
    assert any("a-work" in n and "refusing" in n for n in notes)


def test_missing_volume_is_skipped_not_inserted():
    conn = db_with_schema()
    conn.execute(
        "INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES "
        "('vol-a', 'Islamic', 'Volume A', 'book', NULL, 10, 'published')"
    )
    conn.commit()  # vol-b never published

    statements, notes = plan_for_group(a_group(), units_from(conn))
    assert any("vol-b" in n and "skipped" in n for n in notes)
    assert not any("vol-b" in s for s in statements)
