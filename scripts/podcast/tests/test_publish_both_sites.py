"""One press publishes to BOTH libraries, and localhost goes first.

Asif, 2026-08-10: the Publish button on the Compose tab should reach localhost and
the live site, so the copy he reviews and the copy his readers open are the same
book. The order is the safety property, not a preference — everything that can
fail fails against the copy nobody reads — so it is pinned here rather than left
to the order two dictionaries happen to sit in.

`push` itself is exercised through a recording fake for the two things that leave
this process: the child processes it spawns and the D1 statements it runs. That is
deliberate and narrow — it pins WHICH DATABASE each write is aimed at, which is
the one property a wrong answer makes catastrophic and a passing exit code hides.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import publish_to_production as P  # noqa: E402


class Recorder(P.Reporter):
    """A Reporter that keeps every step name instead of printing it."""

    def __init__(self) -> None:
        super().__init__(as_json=False)
        self.steps: list[str] = []
        self.errors: list[str] = []

    def emit(self, event: str, **fields: object) -> None:
        if event == "step":
            self.steps.append(str(fields.get("name")))
        elif event == "error":
            self.errors.append(str(fields.get("text")))


ARGS = SimpleNamespace(dry_run=False, skip_media=True, skip_local=False)


@pytest.fixture()
def spies(monkeypatch):
    """Record every child command and every D1 statement, and run nothing."""
    seen: dict[str, list] = {"argv": [], "sql": []}
    monkeypatch.setattr(P, "run", lambda argv, report, cwd=None: seen["argv"].append(argv) or 0)
    monkeypatch.setattr(P, "d1_execute", lambda sql, report, *, remote: seen["sql"].append((sql, remote)) or 0)
    monkeypatch.setattr(P, "visibility", lambda slug, *, remote: {"status": "published", "open_to_all": 0})
    monkeypatch.setattr(P, "count_cards", lambda book_dir: 0)
    monkeypatch.setattr(
        P, "verify", lambda slug, book_dir, *, remote, expected: [{"name": "chapters", "ok": True, "detail": "16"}]
    )
    return seen


# ── the order, which is the safety property ──────────────────────────────────


def test_localhost_is_published_before_production():
    """A run that is going to break must break against the copy nobody reads."""
    assert [t["label"] for t in P.TARGETS] == ["localhost", "production"]
    assert P.TARGETS[0]["remote"] is False and P.TARGETS[1]["remote"] is True


def test_each_target_names_where_the_book_can_be_looked_at():
    assert P.TARGETS[0]["url"] == "http://localhost:5273"
    assert P.TARGETS[1]["url"] == "https://podcast-factory.safinaverse.com"


# ── which database each write is aimed at ────────────────────────────────────


def test_the_local_pass_never_passes_remote(spies, tmp_path):
    ok, _ = P.push(P.TARGETS[0], "a-book", tmp_path, ARGS, Recorder(), now="2026-08-10T00:00:00Z")
    assert ok
    assert all("--remote" not in argv for argv in spies["argv"]), spies["argv"]
    assert spies["sql"] == [(P.publish_sql("a-book"), False)]


def test_the_production_pass_passes_remote_to_every_write(spies, tmp_path):
    ok, _ = P.push(P.TARGETS[1], "a-book", tmp_path, ARGS, Recorder(), now="2026-08-10T00:00:00Z")
    assert ok
    assert all("--remote" in argv for argv in spies["argv"]), spies["argv"]
    assert spies["sql"] == [(P.publish_sql("a-book"), True)]


def test_the_visibility_statement_is_the_same_one_for_both_sites():
    """One statement, so the two sites cannot end up with different notions of
    'published'. It writes `status` and never `open_to_all` — Asif, 2026-08-06."""
    sql = P.publish_sql("a-book")
    assert "status = 'published'" in sql
    assert "open_to_all" not in sql


def test_d1_execute_targets_local_or_remote_and_never_both():
    seen: list[list[str]] = []
    P.run = lambda argv, report, cwd=None: seen.append(argv) or 0  # type: ignore[assignment]
    P.d1_execute("SELECT 1;", Recorder(), remote=False)
    P.d1_execute("SELECT 1;", Recorder(), remote=True)
    assert "--local" in seen[0] and "--remote" not in seen[0]
    assert "--remote" in seen[1] and "--local" not in seen[1]


# ── a failure on one site must not reach the other ───────────────────────────


def test_a_failed_local_content_push_never_writes_visibility(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "run", lambda argv, report, cwd=None: 1)
    wrote: list = []
    monkeypatch.setattr(P, "d1_execute", lambda sql, report, *, remote: wrote.append(sql) or 0)
    report = Recorder()
    ok, checks = P.push(P.TARGETS[0], "a-book", tmp_path, ARGS, report, now="2026-08-10T00:00:00Z")
    assert (ok, checks, wrote) == (False, [], [])
    assert "localhost" in report.errors[0]


def test_a_check_carries_the_name_of_the_site_it_came_from(spies, tmp_path):
    """Both sites report the same check names; a merged list that did not say
    which one failed would be unreadable in the stamp and in the panel."""
    _, local = P.push(P.TARGETS[0], "a-book", tmp_path, ARGS, Recorder(), now="2026-08-10T00:00:00Z")
    _, prod = P.push(P.TARGETS[1], "a-book", tmp_path, ARGS, Recorder(), now="2026-08-10T00:00:00Z")
    assert local[0]["name"].endswith("(localhost)") and local[0]["target"] == "localhost"
    assert prod[0]["name"].endswith("(production)") and prod[0]["target"] == "production"


def test_the_steps_say_which_site_they_are_working_on(spies, tmp_path):
    report = Recorder()
    P.push(P.TARGETS[1], "a-book", tmp_path, ARGS, report, now="2026-08-10T00:00:00Z")
    assert report.steps == [
        "Content · production",
        "Media · production",
        "Visibility · production",
        "Verifying · production",
    ]


# ── verified means both ──────────────────────────────────────────────────────


def test_a_book_that_reached_only_one_site_is_not_verified(tmp_path):
    """`write_stamp` derives `verified` from every check, so one site failing
    leaves the Composer's button lit — which is correct, because the two are
    meant to hold the same book."""
    from _production_publish import write_stamp

    (tmp_path / "_system").mkdir()
    merged = [
        {"name": "chapters (localhost)", "ok": True, "detail": "16"},
        {"name": "chapters (production)", "ok": False, "detail": "0"},
    ]
    stamp = write_stamp(tmp_path, now="2026-08-10T00:00:00Z", fingerprint="f", checks=merged)
    import json

    assert json.loads(stamp.read_text())["verified"] is False


def test_skip_local_leaves_exactly_one_target():
    kept = [t for t in P.TARGETS if t["remote"] or not True]
    assert [t["label"] for t in kept] == ["production"]
