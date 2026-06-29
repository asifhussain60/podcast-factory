#!/usr/bin/env python3
"""Phase 3 regression — converge_chapter mid-loop safety rails (F35, fixer-halt,
episode-rebuild surfacing, heartbeat). Drives converge_chapter with monkeypatched
challenger/fixer so no LLM is invoked; asserts the rails fire at the right time.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _convergence as cv  # noqa: E402
from _authoring import AuthoringError  # noqa: E402


@pytest.fixture
def book(tmp_path):
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    return bd


def _write_report(book_dir: Path, verdict: str) -> None:
    """Write a minimal challenger-report.md with a parseable verdict + no findings."""
    (book_dir / "_system" / "challenger-report.md").write_text(
        f"**Verdict:** {verdict}\n\n## Findings\n\n### P0\nNone.\n### P1\nNone.\n### P2\nNone.\n",
        encoding="utf-8",
    )


class TestCostCeilings:
    def test_per_book_ceiling_systemic_halt(self, book, monkeypatch):
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "BLOCKED"))
        out = cv.converge_chapter(
            book, "ch01",
            book_cost_cap=10.0, book_cost_fn=lambda: 99.0,
        )
        assert out.final_verdict == "FAILED"
        assert out.systemic_halt and "COST-CEILING" in out.systemic_halt
        # challenger never ran (ceiling checked BEFORE the expensive call) → iter 1
        assert out.outer_iterations == 1

    def test_per_chapter_ceiling_fails_chapter_only(self, book, monkeypatch):
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "BLOCKED"))
        out = cv.converge_chapter(
            book, "ch01",
            per_chapter_cost_cap=5.0, chapter_cost_fn=lambda: 7.5,
        )
        assert out.final_verdict == "FAILED"
        assert out.systemic_halt is None  # per-chapter breach is NOT systemic
        assert any("COST-CAPPED (mid-loop)" in n for n in out.notes)

    def test_ceilings_dormant_when_unset(self, book, monkeypatch):
        # No cost fns → behaves exactly as before (ships on SHIP-READY).
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "SHIP-READY"))
        out = cv.converge_chapter(book, "ch01")
        assert out.final_verdict == "SHIP-READY"


class TestHeartbeat:
    def test_heartbeat_called_each_iteration(self, book, monkeypatch):
        beats = []
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "SHIP-READY"))
        cv.converge_chapter(book, "ch01", heartbeat=lambda outer, note: beats.append(outer))
        assert beats == [1]  # one iteration, SHIP-READY → one beat

    def test_heartbeat_failure_never_breaks_loop(self, book, monkeypatch):
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "SHIP-READY"))
        def _boom(outer, note):
            raise RuntimeError("beat exploded")
        out = cv.converge_chapter(book, "ch01", heartbeat=_boom)
        assert out.final_verdict == "SHIP-READY"


class TestFixerHalt:
    def test_two_consecutive_fixer_failures_early_halt(self, book, monkeypatch):
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "BLOCKED"))
        def _always_fail(*a, **k):
            raise AuthoringError("fixer", "fixer down")
        monkeypatch.setattr(cv, "invoke_fixer", _always_fail)
        out = cv.converge_chapter(book, "ch01")
        assert out.final_verdict == "FAILED"
        # halts at iter 2 (2 consecutive failures), not grinding to MAX_OUTER (3)
        assert out.outer_iterations == 2
        assert any("2 consecutive structural fixer failures" in n for n in out.notes)


class TestEpisodeRebuildSurfacing:
    def test_failed_rebuild_surfaced(self, book, monkeypatch):
        # First pass BLOCKED → fixer succeeds → rebuild fails → flagged.
        monkeypatch.setattr(cv, "invoke_challenger", lambda *a, **k: _write_report(book, "BLOCKED"))
        monkeypatch.setattr(cv, "invoke_fixer", lambda *a, **k: None)
        monkeypatch.setattr(cv, "_find_episode_id", lambda *a, **k: "EP01-ch01")
        monkeypatch.setattr(cv, "_rebuild_episode_txt", lambda *a, **k: False)
        out = cv.converge_chapter(book, "ch01")
        assert out.episode_rebuild_failed is True
        assert any("episode.txt rebuild FAILED" in n for n in out.notes)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
