#!/usr/bin/env python3
"""Tests for resume_dispatcher.run_resume's book-lane re-entry.

RCA (2026-08-07): retrying an in-progress book-lane phase (0book-design,
0book-compose, 0book-illustrate, 0book-slide-import, 0book-render) used to
route through `_drive_publish_through_done` — the same driver that (a) gates
on `audio-ingest`, a phase the common early-build path
(`_book_preview.maybe_build_reading_edition_early`) never runs, and (b) falls
straight through to publish + merge-to-develop with no re-check that a human
ever actually approved the finalize gate. A book-lane retry must re-enter the
BOUNDED `_drive_book_branch` driver instead — book-writing only, no publish,
no merge — exactly like the early-build path that got it there in the first
place.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from phases import resume_dispatcher


def _book_lane_state(phase: str, status: str = "failed") -> dict:
    return {
        "phase": phase,
        "phase_status": status,
        "last_completed_phase": "0book-design",
        "phases": {
            "finalize": {"status": "halted"},
            "0book-design": {"status": "completed"},
            "0book-compose": {"status": status if phase == "0book-compose" else "completed"},
            "0book-illustrate": {"status": status if phase == "0book-illustrate" else "pending"},
            "0book-slide-import": {"status": status if phase == "0book-slide-import" else "pending"},
            "0book-render": {"status": status if phase == "0book-render" else "pending"},
        },
    }


class ResumeDispatcherBookLaneTests(unittest.TestCase):
    def _run(self, phase: str, status: str = "failed"):
        args = argparse.Namespace(resume="spiritual-ethos", stop_after=None, retry_phase=None, unattended=False)
        state = _book_lane_state(phase, status)
        with (
            mock.patch.object(resume_dispatcher, "preflight_resume", return_value=(Path("/tmp/book"), [])),
            mock.patch.object(resume_dispatcher, "read_state", return_value=state),
            mock.patch.object(resume_dispatcher, "write_state"),
            mock.patch.object(resume_dispatcher, "cost_ceiling_check", return_value={"action": "ok"}),
            mock.patch("phases.book_driver._drive_book_branch", return_value=0) as book_branch,
            mock.patch("phases.publish_driver._drive_publish_through_done", return_value=0) as publish_through,
        ):
            resume_dispatcher.run_resume(args)
        return book_branch, publish_through

    def test_0book_compose_retry_uses_the_bounded_book_branch_driver(self):
        book_branch, publish_through = self._run("0book-compose")
        book_branch.assert_called_once()
        publish_through.assert_not_called()

    def test_0book_design_retry_uses_the_bounded_book_branch_driver(self):
        book_branch, publish_through = self._run("0book-design", status="completed")
        book_branch.assert_called_once()
        publish_through.assert_not_called()

    def test_0book_render_retry_uses_the_bounded_book_branch_driver(self):
        book_branch, publish_through = self._run("0book-render", status="failed")
        book_branch.assert_called_once()
        publish_through.assert_not_called()

    def test_0book_slide_import_halted_uses_the_bounded_book_branch_driver(self):
        book_branch, publish_through = self._run("0book-slide-import", status="halted")
        book_branch.assert_called_once()
        publish_through.assert_not_called()

    def _run_with_audio_ingest(self, phase: str, audio_ingest_status: str, status: str = "failed"):
        args = argparse.Namespace(resume="spiritual-ethos", stop_after=None, retry_phase=None, unattended=False)
        state = _book_lane_state(phase, status)
        state["phases"]["audio-ingest"] = {"status": audio_ingest_status}
        with (
            mock.patch.object(resume_dispatcher, "preflight_resume", return_value=(Path("/tmp/book"), [])),
            mock.patch.object(resume_dispatcher, "read_state", return_value=state),
            mock.patch.object(resume_dispatcher, "write_state"),
            mock.patch.object(resume_dispatcher, "cost_ceiling_check", return_value={"action": "ok"}),
            mock.patch("phases.book_driver._drive_book_branch", return_value=0) as book_branch,
            mock.patch.object(resume_dispatcher, "_drive_publish_through_done", return_value=0) as publish_through,
        ):
            resume_dispatcher.run_resume(args)
        return book_branch, publish_through

    def test_0book_render_after_audio_ingest_completed_uses_the_full_publish_driver(self):
        # Regression for the sharh-al-masail-ghulam-hussain incident (2026-08-18):
        # once finalize has genuinely been approved (proven by audio-ingest having
        # run), a book-lane phase must route FORWARD through the publish chain,
        # not loop forever in the bounded book-only lane.
        book_branch, publish_through = self._run_with_audio_ingest("0book-render", "completed")
        publish_through.assert_called_once()
        book_branch.assert_not_called()

    def test_0book_render_after_audio_ingest_skipped_uses_the_full_publish_driver(self):
        book_branch, publish_through = self._run_with_audio_ingest("0book-render", "skipped")
        publish_through.assert_called_once()
        book_branch.assert_not_called()

    def test_0book_render_after_audio_ingest_halted_uses_the_full_publish_driver(self):
        # audio-ingest itself can be sitting HALTED (waiting on a NotebookLM drop)
        # from an earlier pass through the SAME publish-through-done call that also
        # touched the book lane — still proof finalize was approved.
        book_branch, publish_through = self._run_with_audio_ingest("0book-render", "halted")
        publish_through.assert_called_once()
        book_branch.assert_not_called()

    def test_0book_design_after_audio_ingest_completed_uses_the_full_publish_driver(self):
        book_branch, publish_through = self._run_with_audio_ingest("0book-design", "completed", status="completed")
        publish_through.assert_called_once()
        book_branch.assert_not_called()

    def test_0book_slide_import_after_audio_ingest_completed_uses_the_full_publish_driver(self):
        book_branch, publish_through = self._run_with_audio_ingest("0book-slide-import", "completed", status="halted")
        publish_through.assert_called_once()
        book_branch.assert_not_called()

    def test_0book_render_with_audio_ingest_still_pending_stays_bounded(self):
        # audio-ingest absent/pending == the early-build path, pre-approval —
        # unchanged behaviour, still the bounded lane.
        book_branch, publish_through = self._run_with_audio_ingest("0book-render", "pending")
        book_branch.assert_called_once()
        publish_through.assert_not_called()

    def test_finalize_halted_still_uses_the_full_publish_driver(self):
        # The one legitimate path to publish: a genuine --resume while
        # current_phase == "finalize" — unchanged by this fix.
        args = argparse.Namespace(resume="spiritual-ethos", stop_after=None, retry_phase=None, unattended=False)
        state = {
            "phase": "finalize",
            "phase_status": "halted",
            "last_completed_phase": "0g",
            "phases": {"finalize": {"status": "halted"}},
        }
        with (
            mock.patch.object(resume_dispatcher, "preflight_resume", return_value=(Path("/tmp/book"), [])),
            mock.patch.object(resume_dispatcher, "read_state", return_value=state),
            mock.patch.object(resume_dispatcher, "write_state"),
            mock.patch.object(resume_dispatcher, "cost_ceiling_check", return_value={"action": "ok"}),
            mock.patch.object(resume_dispatcher, "_drive_publish_through_done", return_value=0) as publish_through,
        ):
            resume_dispatcher.run_resume(args)
        publish_through.assert_called_once()


if __name__ == "__main__":
    unittest.main()
