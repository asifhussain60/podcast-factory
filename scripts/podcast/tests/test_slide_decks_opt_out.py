#!/usr/bin/env python3
"""Opting a book out of slide decks.

isaf-al-talib's series-config.yaml said `enable_slide_decks: false` (and a comment
claimed the driver honoured it), but `post_chapter_driver` only read the flag from
series-plan.md — so the pipeline authored slide decks anyway, against Asif's
explicit "I don't want the slide deck generated for this book" (2026-09-18). Either
file may now turn the phase off; the default stays ON so every existing book is
unaffected.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import pytest  # noqa: E402
from phases import post_chapter_driver as pcd  # noqa: E402


@pytest.fixture
def book(tmp_path: Path, monkeypatch):
    system = tmp_path / "_system"
    system.mkdir()
    (system / "orchestrator-state.json").write_text(
        json.dumps({"phase": "0g", "phase_status": "completed", "phases": {"0g": {"status": "completed"}}}),
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(pcd, "run_slide_cohort", lambda *_a, **_k: calls.append("cohort"))
    monkeypatch.setattr(pcd, "phase_git_commit", lambda *_a, **_k: None)
    import phases.audio_driver as audio_driver

    # ("halted", 0) makes drive_post_chapter return right after the slide step.
    monkeypatch.setattr(audio_driver, "drive_audio_phases", lambda *_a, **_k: ("halted", 0))
    return tmp_path, calls


def _drive(book_dir: Path) -> None:
    pcd.drive_post_chapter(
        book_dir, book_slug="t", completed_chapter_slugs=set(), outcomes=[], approve_audio_render=False
    )


def _slides_status(book_dir: Path) -> str | None:
    state = json.loads((book_dir / "_system" / "orchestrator-state.json").read_text(encoding="utf-8"))
    return state["phases"].get("per-chapter-slides", {}).get("status")


def test_slide_decks_run_by_default(book) -> None:
    book_dir, calls = book
    _drive(book_dir)
    assert calls == ["cohort"]


def test_series_config_can_opt_out(book) -> None:
    book_dir, calls = book
    (book_dir / "_system" / "series-config.yaml").write_text("enable_slide_decks: false\n", encoding="utf-8")
    _drive(book_dir)
    assert calls == []
    assert _slides_status(book_dir) == "skipped"


def test_series_plan_can_still_opt_out(book) -> None:
    book_dir, calls = book
    (book_dir / "_system" / "series-plan.md").write_text("**Enable Slide Decks:** false\n", encoding="utf-8")
    _drive(book_dir)
    assert calls == []


def test_config_true_does_not_override_a_plan_opt_out(book) -> None:
    book_dir, calls = book
    (book_dir / "_system" / "series-config.yaml").write_text("enable_slide_decks: true\n", encoding="utf-8")
    (book_dir / "_system" / "series-plan.md").write_text("**Enable Slide Decks:** false\n", encoding="utf-8")
    _drive(book_dir)
    assert calls == []
