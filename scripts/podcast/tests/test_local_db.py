"""A publish to the LOCAL Library database must not fail on a stale schema.

isaf-al-talib, 2026-09-19: the local database was three migrations behind (0019-0021), so the publish
died with "table unit_detail has no column named author". The git hooks that apply local migrations only
fire when `develop` moves, and the book was on its own branch. The publish now checks first: pending
migrations are applied to the LOCAL database (never remote), and if that fails it says the exact command.
It never deletes anything under listener/.wrangler/state.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _local_db as ldb  # noqa: E402

NONE = "No migrations to apply!\n"
PENDING = """Migrations to be applied:
┌───────────────────────────┐
│ name                      │
├───────────────────────────┤
│ 0019_study_track_philosophy.sql │
├───────────────────────────┤
│ 0020_unit_author.sql      │
└───────────────────────────┘
"""


class Fake:
    def __init__(self, listing, apply_rc=0, apply_out="applied"):
        self.listing, self.apply_rc, self.apply_out = listing, apply_rc, apply_out
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if "list" in argv:
            return subprocess.CompletedProcess(argv, 0, self.listing, "")
        return subprocess.CompletedProcess(argv, self.apply_rc, self.apply_out, "boom" if self.apply_rc else "")


def test_a_current_database_is_left_alone(tmp_path):
    fake = Fake(NONE)
    assert ldb.ensure_local_migrations(tmp_path, run=fake) is None
    assert all("apply" not in c for c in fake.calls)


def test_pending_migrations_are_named_and_applied(tmp_path):
    fake = Fake(PENDING)
    assert ldb.pending_migrations(tmp_path, run=fake) == ["0019_study_track_philosophy.sql", "0020_unit_author.sql"]
    assert ldb.ensure_local_migrations(tmp_path, run=Fake(PENDING)) is None
    applying = Fake(PENDING)
    ldb.ensure_local_migrations(tmp_path, run=applying)
    assert any("apply" in c for c in applying.calls)


def test_only_the_local_database_is_ever_touched(tmp_path):
    fake = Fake(PENDING)
    ldb.ensure_local_migrations(tmp_path, run=fake)
    assert fake.calls and all("--local" in c and "--remote" not in c for c in fake.calls)


def test_a_failed_apply_reports_the_exact_remedy_and_nothing_is_deleted(tmp_path):
    problem = ldb.ensure_local_migrations(tmp_path, run=Fake(PENDING, apply_rc=1))
    assert problem and "npm run db:migrate" in problem and "0019_study_track_philosophy.sql" in problem
    assert "never delete" in problem.lower() and ".wrangler/state" in problem


def test_an_unreadable_listing_is_a_problem_not_a_silent_pass(tmp_path):
    def broken(argv, **kw):
        raise OSError("npx not found")

    problem = ldb.ensure_local_migrations(tmp_path, run=broken)
    assert problem and "npm run db:migrate" in problem


def test_publish_to_listener_checks_the_local_schema_before_writing():
    text = (Path(__file__).resolve().parents[1] / "publish_to_listener.py").read_text(encoding="utf-8")
    assert "ensure_local_migrations(" in text
    assert text.index("ensure_local_migrations(") < text.index("load_book(slug")
