#!/usr/bin/env python3
"""Tests for resume_dispatcher._clear_downstream_phases.

--retry-phase on an earlier phase must clear EVERY downstream phase block
(canonical PHASES order), including the per-chapter completion ledgers —
otherwise re-running 0d on a completed book leaves per-chapter/finalize/
0book-* marked completed and the re-run silently no-ops.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from phases.resume_dispatcher import _clear_downstream_phases  # noqa: E402


def _completed_book_state() -> dict:
    """State shaped like a book that ran to 0book-render (e.g. M&D)."""
    phases = {
        "pre-flight": {"status": "completed"},
        "branch": {"status": "completed"},
        "scaffold": {"status": "completed"},
        "0a": {"status": "completed"},
        "0b": {"status": "completed"},
        "0c": {"status": "completed"},
        "0d": {"status": "completed", "ts_completed": "x"},
        "0e": {"status": "completed"},
        "06a": {"status": "completed"},
        "0f": {"status": "completed"},
        "0g": {"status": "completed"},
        "per-chapter": {
            "status": "completed",
            "completed_slugs": ["a", "b", "c", "d", "e"],
            "failed_slugs": ["f"],
            "chapter_timings": {"a": 1.0},
        },
        "finalize": {"status": "halted"},
        "0book-design": {"status": "completed"},
        "0book-compose": {"status": "completed"},
        "0book-illustrate": {"status": "completed"},
        "0book-render": {"status": "completed"},
        "publish": {"status": "skipped"},
    }
    return {
        "phase": "0book-render",
        "phase_status": "completed",
        "last_completed_phase": "0book-render",
        "phases": phases,
    }


class RetryPhaseClearingTests(unittest.TestCase):
    def test_retry_0d_clears_all_downstream(self):
        state = _completed_book_state()
        _clear_downstream_phases(state, "0d", log=lambda *_: None)

        self.assertEqual(state["phase"], "0d")
        self.assertEqual(state["phase_status"], "pending")
        self.assertEqual(state["phases"]["0d"]["status"], "pending")
        self.assertNotIn("ts_completed", state["phases"]["0d"])

        for later in ("0e", "0f", "0g", "per-chapter", "finalize",
                      "0book-design", "0book-compose", "0book-illustrate",
                      "0book-render", "publish"):
            self.assertEqual(
                state["phases"][later]["status"], "pending",
                f"{later} should be cleared to pending",
            )

        pc = state["phases"]["per-chapter"]
        self.assertEqual(pc["completed_slugs"], [])
        self.assertEqual(pc["failed_slugs"], [])
        self.assertEqual(pc["chapter_timings"], {})

    def test_retry_0d_leaves_earlier_phases_completed(self):
        state = _completed_book_state()
        _clear_downstream_phases(state, "0d", log=lambda *_: None)
        for earlier in ("pre-flight", "branch", "scaffold", "0a", "0b", "0c"):
            self.assertEqual(
                state["phases"][earlier]["status"], "completed",
                f"{earlier} must not be touched",
            )

    def test_mid_pipeline_retry_per_chapter(self):
        state = _completed_book_state()
        _clear_downstream_phases(state, "per-chapter", log=lambda *_: None)
        # earlier phases untouched
        self.assertEqual(state["phases"]["0d"]["status"], "completed")
        self.assertEqual(state["phases"]["0e"]["status"], "completed")
        # retried + downstream cleared — but retrying per-chapter ITSELF is
        # the resume/recovery path (watchdog uses it): completed chapters
        # must be PRESERVED so the loop continues where it left off. Ledgers
        # are wiped only when per-chapter is downstream of the retried phase.
        pc = state["phases"]["per-chapter"]
        self.assertEqual(pc["status"], "pending")
        self.assertEqual(pc["completed_slugs"], ["a", "b", "c", "d", "e"])
        self.assertEqual(state["phases"]["finalize"]["status"], "pending")
        self.assertEqual(state["phases"]["0book-render"]["status"], "pending")

    def test_last_completed_phase_rewound(self):
        state = _completed_book_state()
        _clear_downstream_phases(state, "0d", log=lambda *_: None)
        # canonical phase before 0d is 0ci; M&D state may lack that block,
        # but the pointer must rewind to the canonical predecessor regardless.
        self.assertEqual(state["last_completed_phase"], "0ci")


if __name__ == "__main__":
    unittest.main()
