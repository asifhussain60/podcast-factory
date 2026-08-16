"""Tests for _articulation_reconcile.py — the durable memory + retry logic for
chapters the articulation pass reverted.

Locks two things that were live bugs on 2026-08-15:
  (1) a reverted window's gate-failure reason must survive the process exiting
      (it used to only ever exist in that one run's stdout);
  (2) a chapter's 1-based section number must account for a leading
      introduction section, or a retry silently re-runs the WRONG chapter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _articulation_reconcile as R


def _book(tmp_path: Path, book_md: str) -> Path:
    bd = tmp_path / "book_dir"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(book_md, encoding="utf-8")
    return bd


_WITH_INTRO = (
    "# The Book\n\n"
    "## Introduction\n\nAn introductory note.\n\n"
    "## 1. On Knowledge\n\nSeek knowledge from cradle to grave.\n\n"
    "## 2. On Patience\n\nPatience is light.\n"
)

_NO_INTRO = "# The Book\n\n## 1. On Knowledge\n\nSeek knowledge.\n\n## 2. On Patience\n\nPatience is light.\n"


# ─── record_chapter_attempt / open_chapters ─────────────────────────────────
def test_record_chapter_attempt_persists_gate_findings(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    R.record_chapter_attempt(bd, "On Patience", "reverted", ["abridged re-voice (10<20 words)"], attempt_kind="pass")

    data = json.loads(R.reconcile_path(bd).read_text())
    entry = data["chapters"]["On Patience"]
    assert entry["resolved"] is False
    assert entry["log"][0]["gate_findings"] == ["abridged re-voice (10<20 words)"]
    assert entry["log"][0]["attempt_kind"] == "pass"
    assert R.open_chapters(bd) == ["On Patience"]


def test_needs_human_only_set_after_a_second_attempt_still_fails(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    R.record_chapter_attempt(bd, "On Patience", "reverted", ["reason A"], attempt_kind="pass")
    assert R.reconcile_path(bd).read_text()
    data = json.loads(R.reconcile_path(bd).read_text())
    assert data["chapters"]["On Patience"]["needs_human"] is False  # first pass alone isn't "needs a human"

    R.record_chapter_attempt(bd, "On Patience", "reverted", ["reason A", "reason B"], attempt_kind="second-attempt")
    data = json.loads(R.reconcile_path(bd).read_text())
    entry = data["chapters"]["On Patience"]
    assert entry["needs_human"] is True
    assert entry["resolved"] is False
    assert len(entry["log"]) == 2  # append-only — first attempt's findings are not lost


def test_resolved_when_a_later_attempt_passes(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    R.record_chapter_attempt(bd, "On Patience", "reverted", ["reason A"], attempt_kind="pass")
    R.record_chapter_attempt(bd, "On Patience", "adapted", [], attempt_kind="second-attempt")
    data = json.loads(R.reconcile_path(bd).read_text())
    entry = data["chapters"]["On Patience"]
    assert entry["resolved"] is True
    assert entry["needs_human"] is False
    assert R.open_chapters(bd) == []


# ─── _chapter_numbers_by_title — the introduction off-by-one regression ────
def test_chapter_numbers_account_for_leading_introduction(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    numbers = R._chapter_numbers_by_title(bd / "book" / "book.md")
    # Introduction is section 1; "On Knowledge" is section 2, NOT 1.
    assert numbers == {"On Knowledge": 2, "On Patience": 3}


def test_chapter_numbers_without_an_introduction(tmp_path: Path) -> None:
    bd = _book(tmp_path, _NO_INTRO)
    numbers = R._chapter_numbers_by_title(bd / "book" / "book.md")
    assert numbers == {"On Knowledge": 1, "On Patience": 2}


# ─── gate_articulation_complete (B9) ────────────────────────────────────────
def test_gate_passes_when_no_fluency_report(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    ok, why = R.gate_articulation_complete(bd)
    assert ok is True
    assert "does not apply" in why


def test_gate_passes_when_every_chapter_adapted(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    report = {
        "chapters": [{"title": "On Knowledge", "status": "adapted"}, {"title": "On Patience", "status": "adapted"}]
    }
    (bd / "_system" / "book-fluency-report.json").write_text(json.dumps(report))
    ok, why = R.gate_articulation_complete(bd)
    assert ok is True


def test_gate_fails_on_open_reconcile_debt(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    report = {
        "chapters": [{"title": "On Knowledge", "status": "adapted"}, {"title": "On Patience", "status": "partial"}]
    }
    (bd / "_system" / "book-fluency-report.json").write_text(json.dumps(report))
    ok, why = R.gate_articulation_complete(bd)
    assert ok is False
    assert "On Patience" in why


def test_gate_passes_when_stuck_chapter_already_resolved_in_ledger(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    report = {"chapters": [{"title": "On Patience", "status": "partial"}]}
    (bd / "_system" / "book-fluency-report.json").write_text(json.dumps(report))
    R.record_chapter_attempt(bd, "On Patience", "adapted", [], attempt_kind="second-attempt")
    ok, why = R.gate_articulation_complete(bd)
    assert ok is True
    assert "resolved" in why


# ─── reconcile_records — the retry itself, using a fake fn/repair_fn ───────
def test_reconcile_records_retries_only_the_stuck_chapter_by_correct_number(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    book_md = bd / "book" / "book.md"
    seen_numbers = []

    def fake_fn(title, base_text, book_dir, label, log, **kw):
        return base_text + " (revised)"

    # Fake the underlying _run_pass via monkeypatch-free indirection: call the
    # real thing through _book_voice, but assert on `only` by wrapping fn to
    # record which title it was invoked for during the retry.
    def spying_fn(title, base_text, book_dir, label, log, **kw):
        seen_numbers.append(title)
        return base_text + " (revised)"

    records = [
        {"title": "On Knowledge", "status": "adapted", "gates": []},
        {"title": "On Patience", "status": "reverted", "gates": ["teaching loss"]},
    ]
    new_text, merged = R.reconcile_records(
        bd,
        book_md,
        records,
        fn=spying_fn,
        repair_fn=None,
        frame=None,
        narrator_subject="",
        window_words=300,
        log=lambda *a: None,
    )
    # Only "On Patience" (the stuck one) was retried — "On Knowledge" untouched.
    assert seen_numbers == ["On Patience"]
    assert merged[0]["title"] == "On Knowledge"
    assert merged[0]["status"] == "adapted"
    assert merged[1]["title"] == "On Patience"

    data = json.loads(R.reconcile_path(bd).read_text())
    assert "On Patience" in data["chapters"]
    assert "On Knowledge" not in data["chapters"]  # never-stuck chapters get no entry


def test_reconcile_records_noop_when_nothing_stuck(tmp_path: Path) -> None:
    bd = _book(tmp_path, _WITH_INTRO)
    book_md = bd / "book" / "book.md"
    records = [{"title": "On Knowledge", "status": "adapted", "gates": []}]
    calls = []

    def fn_should_not_be_called(*a, **k):
        calls.append(1)
        return "x"

    new_text, merged = R.reconcile_records(
        bd,
        book_md,
        records,
        fn=fn_should_not_be_called,
        repair_fn=None,
        frame=None,
        narrator_subject="",
        window_words=300,
        log=lambda *a: None,
    )
    assert calls == []
    assert merged == records
    assert not R.reconcile_path(bd).exists()
