"""The probe must notice a book that has been stuck for weeks, and a findings ledger nobody triages.

2026-09-19 audit: eight books sat in failed/halted/pending states — kunooz-al-hikmah's render had been failed
since 2026-06-14, three finalize halts, a publish pending since 08-05 — and the findings ledger held ~740 open
top-severity rows, and NOTHING said so. Both are P2 (they never block a commit): a stale halt can be a
deliberate wait for a human, and an old finding can still be true. What they must not be is invisible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import repo_surgeon_health as health  # noqa: E402
from _harness import ids, make_probe, write  # noqa: E402

OLD = "2020-01-01T00:00:00Z"


def _state(tmp_path: Path, slug: str, **state) -> None:
    body = {"slug": slug, "phase": "0book-render", "phase_status": "failed", "status": "draft", **state}
    write(tmp_path, f"content/Islamic/{slug}/_system/orchestrator-state.json", json.dumps(body))


def _aged(phase_ts: str) -> dict:
    return {"phases": {"0book-render": {"status": "failed", "ts_started": phase_ts, "ts_completed": phase_ts}}}


# ---------- stuck books ----------
def test_a_book_failed_long_ago_is_reported_by_name_and_age(tmp_path):
    _state(tmp_path, "kunooz", **_aged(OLD))
    probe = make_probe(tmp_path, {})
    health.check_stuck_books(probe)
    assert ids(probe) == ["HL-STUCK"]
    assert "kunooz" in probe.findings[0].summary and probe.findings[0].severity == "P2"


def test_a_recently_active_book_is_not_stuck(tmp_path):
    import datetime as dt

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _state(tmp_path, "fresh", **_aged(now))
    probe = make_probe(tmp_path, {})
    health.check_stuck_books(probe)
    assert ids(probe) == []


def test_a_finished_or_published_book_is_never_stuck(tmp_path):
    _state(tmp_path, "done", phase="done", phase_status="completed", **_aged(OLD))
    _state(tmp_path, "shipped", status="published", **_aged(OLD))
    probe = make_probe(tmp_path, {})
    health.check_stuck_books(probe)
    assert ids(probe) == []


def test_archived_books_are_out_of_scope(tmp_path):
    write(
        tmp_path,
        "content/_archive/old/_system/orchestrator-state.json",
        json.dumps({"phase": "x", "phase_status": "failed", "status": "draft", **_aged(OLD)}),
    )
    probe = make_probe(tmp_path, {})
    health.check_stuck_books(probe)
    assert ids(probe) == []


def test_no_content_tree_cannot_crash_the_check(tmp_path):
    probe = make_probe(tmp_path, {})
    health.check_stuck_books(probe)
    assert ids(probe) == []


# ---------- findings backlog ----------
def _ledger(tmp_path: Path, *rows: dict) -> None:
    write(tmp_path, "_learning/findings.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n")


def test_old_open_top_severity_findings_are_reported_once_with_the_command_to_triage(tmp_path):
    _ledger(
        tmp_path,
        {"severity": "P0", "resolution": "flagged", "ts": OLD},
        {"severity": "P0", "resolution": "carried", "ts": OLD},
    )
    probe = make_probe(tmp_path, {})
    health.check_findings_backlog(probe)
    assert ids(probe) == ["HL-BACKLOG"]
    assert "2 " in probe.findings[0].summary and "findings_triage.py" in probe.findings[0].summary


def test_resolved_superseded_and_recent_findings_are_not_a_backlog(tmp_path):
    import datetime as dt

    recent = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _ledger(
        tmp_path,
        {"severity": "P0", "resolution": "fixed", "ts": OLD},
        {"severity": "P0", "resolution": "superseded", "ts": OLD},
        {"severity": "P0", "resolution": "flagged", "ts": recent},
        {"severity": "P2", "resolution": "flagged", "ts": OLD},
    )
    probe = make_probe(tmp_path, {})
    health.check_findings_backlog(probe)
    assert ids(probe) == []


def test_a_missing_or_garbled_ledger_cannot_crash_the_check(tmp_path):
    probe = make_probe(tmp_path, {})
    health.check_findings_backlog(probe)
    write(tmp_path, "_learning/findings.jsonl", "not json\n{\n")
    health.check_findings_backlog(probe)
    assert ids(probe) == []


# ---------- always-loaded doc budgets ----------
def test_a_doc_over_its_budget_is_reported_with_where_the_rationale_belongs(tmp_path):
    write(tmp_path, "CLAUDE.md", "x" * (health.DOC_BUDGETS["CLAUDE.md"] + 1))
    probe = make_probe(tmp_path, {})
    health.check_doc_budgets(probe)
    assert ids(probe) == ["HL-DOC-BUDGET"]
    assert "CLAUDE.md" in probe.findings[0].summary and "docs/decisions" in probe.findings[0].summary


def test_docs_within_budget_and_absent_docs_are_quiet(tmp_path):
    write(tmp_path, "CLAUDE.md", "x" * 100)
    probe = make_probe(tmp_path, {})
    health.check_doc_budgets(probe)
    assert ids(probe) == []


def test_the_live_repos_docs_are_within_their_budgets():
    root = Path(__file__).resolve().parents[1]
    over = {n: (root / n).stat().st_size for n, b in health.DOC_BUDGETS.items() if (root / n).stat().st_size > b}
    assert over == {}, f"always-loaded docs outgrew their budgets: {over} — move rationale to docs/decisions/"
