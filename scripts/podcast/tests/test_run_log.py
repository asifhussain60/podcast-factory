#!/usr/bin/env python3
"""Tests for the run-correlated structured event log.

Covers _progress.log_event / init_run_log / write_failure_dump and the
claude_p.* capture wired into _authoring/_core._run_claude_p.

The load-bearing guarantees under test:
  1. Observability NEVER raises into the pipeline (a broken log must not turn a
     working phase into a failed one).
  2. A FAILED `claude -p` call persists evidence. Before this wiring, only a
     SUCCESSFUL call wrote artifacts; failures and timeouts wrote nothing.

Uses stdlib unittest only — no pytest dependency.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _progress
import _runlog
from _progress import (
    RUN_LOG_RETENTION,
    init_run_log,
    initial_state,
    log_event,
    read_run_events,
    reset_run_log,
    update_phase,
    write_state,
)


class _RunLogCase(unittest.TestCase):
    """Isolates the process-wide run context and redirects _workspace/runs/."""

    def setUp(self) -> None:
        reset_run_log()
        # Book dirs here are temp dirs, outside the repo content root, so the
        # log is off by default (that guard is what keeps the rest of the test
        # suite from writing into a real _workspace/). Force it on for these.
        self._orig_flag = os.environ.get("PODCAST_RUN_LOG")
        os.environ["PODCAST_RUN_LOG"] = "1"
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.runs_root = self.tmp / "runs"
        # Patch where the name is USED (_runlog), not where it is re-exported
        # (_progress) — init_run_log resolves runs_dir in its own module globals.
        self._orig_runs_dir = _runlog.runs_dir
        _runlog.runs_dir = lambda slug: self.runs_root / (slug or "_unknown")  # type: ignore[assignment]

        self.book_dir = self.tmp / "content" / "Islamic" / "demo-book"
        (self.book_dir / "_system").mkdir(parents=True)
        write_state(self.book_dir, initial_state("demo-book", "books"))

    def tearDown(self) -> None:
        _runlog.runs_dir = self._orig_runs_dir  # type: ignore[assignment]
        if self._orig_flag is None:
            os.environ.pop("PODCAST_RUN_LOG", None)
        else:
            os.environ["PODCAST_RUN_LOG"] = self._orig_flag
        reset_run_log()
        self._tmp.cleanup()

    def _lines(self) -> list[dict]:
        path = _progress.run_log_path()
        assert path is not None
        return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


class TestNoOpFallback(_RunLogCase):
    def test_log_event_before_init_is_silent_noop(self):
        """Importing phase modules in isolation must never crash or create files."""
        log_event("orphan.event")  # no book_dir, no init
        self.assertIsNone(_progress.current_run_id())
        self.assertFalse(self.runs_root.exists())

    def test_log_event_never_raises_on_io_error(self):
        """A broken log degrades to a stderr warning — it does not propagate."""
        init_run_log(self.book_dir)
        path = Path(_progress.run_log_path())
        # Make the run log unwritable.
        path.touch()
        path.chmod(stat.S_IRUSR)
        try:
            log_event("should.not.raise", book_dir=self.book_dir)  # must not throw
        finally:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_update_phase_survives_a_broken_run_log(self):
        """The state machine keeps working even when the timeline cannot be written."""
        init_run_log(self.book_dir)
        d = Path(_progress.run_log_path()).parent
        # Replace the runs directory with a file so every write fails.
        for p in d.glob("*"):
            p.unlink()
        d.rmdir()
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text("not a directory")

        state = update_phase(self.book_dir, phase="0a", status="completed")
        self.assertEqual(state["phase_status"], "completed")


class TestModuleSplit(unittest.TestCase):
    """DR-005 split: the run log lives in _runlog, re-exported from _progress."""

    def test_progress_reexports_are_the_same_objects(self):
        for name in (
            "RUN_LOG_RETENTION",
            "RUN_LOG_TAIL_CHARS",
            "current_run_id",
            "init_run_log",
            "log_event",
            "mint_run_id",
            "read_run_events",
            "reset_run_log",
            "run_log_enabled",
            "run_log_path",
            "runs_dir",
            "tail",
            "write_failure_dump",
        ):
            self.assertIs(
                getattr(_progress, name),
                getattr(_runlog, name),
                f"{name} drifted between _progress and _runlog",
            )

    def test_both_modules_stay_under_the_dr005_limit(self):
        for mod in ("_progress.py", "_runlog.py"):
            path = Path(__file__).resolve().parents[1] / mod
            n = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(n, 600, f"{mod} is {n} lines — DR-005 limit is 600")


class TestEnablementGuard(_RunLogCase):
    """The guard that stops the rest of the test suite writing to _workspace/."""

    def test_temp_book_dir_is_off_by_default(self):
        os.environ.pop("PODCAST_RUN_LOG", None)
        self.assertFalse(_progress.run_log_enabled(self.book_dir))
        update_phase(self.book_dir, phase="0a", status="running")
        self.assertIsNone(_progress.current_run_id())
        self.assertFalse(self.runs_root.exists())

    def test_explicit_off_beats_a_real_book_dir(self):
        os.environ["PODCAST_RUN_LOG"] = "0"
        self.assertFalse(_progress.run_log_enabled(self.book_dir))

    def test_real_content_dir_is_on_by_default(self):
        os.environ.pop("PODCAST_RUN_LOG", None)
        from _paths import CONTENT_ROOT

        self.assertTrue(_progress.run_log_enabled(Path(CONTENT_ROOT) / "Islamic" / "some-book"))


class TestPhaseEvents(_RunLogCase):
    def test_transition_emits_wellformed_line_and_stamps_run_id(self):
        state = update_phase(self.book_dir, phase="0a", status="running")

        self.assertTrue(state["run_id"])
        self.assertEqual(state["run_id"], _progress.current_run_id())

        rows = self._lines()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for key in ("ts", "run_id", "book_slug", "phase", "event", "level", "msg"):
            self.assertIn(key, row)
        self.assertEqual(row["event"], "phase.running")
        self.assertEqual(row["phase"], "0a")
        self.assertEqual(row["book_slug"], "demo-book")
        self.assertEqual(row["level"], "info")
        self.assertEqual(row["run_id"], state["run_id"])

    def test_failed_transition_is_error_level(self):
        update_phase(self.book_dir, phase="0b", status="failed", error="boom")
        row = self._lines()[-1]
        self.assertEqual(row["event"], "phase.failed")
        self.assertEqual(row["level"], "error")
        self.assertEqual(row["msg"], "boom")

    def test_events_accumulate_in_order_under_one_run_id(self):
        update_phase(self.book_dir, phase="0a", status="running")
        update_phase(self.book_dir, phase="0a", status="completed")
        update_phase(self.book_dir, phase="0b", status="running")

        rows = self._lines()
        self.assertEqual(
            [r["event"] for r in rows],
            ["phase.running", "phase.completed", "phase.running"],
        )
        self.assertEqual(len({r["run_id"] for r in rows}), 1)


class TestFailureDump(_RunLogCase):
    def test_failed_phase_writes_last_failure_with_resume_command(self):
        update_phase(self.book_dir, phase="0a", status="running")
        update_phase(self.book_dir, phase="0d", status="failed", error="chapter design blew up")

        dump = self.book_dir / "_system" / "last-failure.md"
        self.assertTrue(dump.exists())
        text = dump.read_text()

        self.assertIn("chapter design blew up", text)
        self.assertIn("`0d`", text)
        self.assertIn(
            "orchestrate_book.py --resume demo-book --retry-phase 0d",
            text,
        )
        self.assertIn(_progress.current_run_id(), text)
        # The timeline tail is cross-referenced, not just the checkpoint.
        self.assertIn("phase.running", text)

    def test_halted_phase_also_writes_a_dump(self):
        update_phase(self.book_dir, phase="0f", status="halted")
        self.assertTrue((self.book_dir / "_system" / "last-failure.md").exists())

    def test_completed_phase_writes_no_dump(self):
        update_phase(self.book_dir, phase="0a", status="completed")
        self.assertFalse((self.book_dir / "_system" / "last-failure.md").exists())


class TestRetention(_RunLogCase):
    def test_prunes_to_retention_but_keeps_newest_failed_run(self):
        d = self.runs_root / "demo-book"
        d.mkdir(parents=True)

        # One old FAILED run, then enough clean runs to push it past the cap.
        failed = d / "20200101T000000Z-failed.jsonl"
        failed.write_text(json.dumps({"level": "error", "event": "phase.failed"}) + "\n")
        for i in range(RUN_LOG_RETENTION + 5):
            (d / f"20260101T0000{i:02d}Z-clean.jsonl").write_text(
                json.dumps({"level": "info", "event": "phase.completed"}) + "\n"
            )

        init_run_log(self.book_dir)  # minting a new run triggers the prune

        survivors = sorted(p.name for p in d.glob("*.jsonl"))
        self.assertIn(failed.name, survivors, "the failed run must outrank newer clean runs")
        self.assertLessEqual(len(survivors), RUN_LOG_RETENTION + 2)


class TestClaudePCapture(_RunLogCase):
    """The core guarantee: a FAILED llm call persists evidence."""

    def _fake_claude(self, body: str) -> Path:
        p = self.tmp / "fake-claude"
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        return p

    def _run(self, fake: Path, **kw):
        from _authoring import _core

        orig = _core.CLAUDE_CMD
        _core.CLAUDE_CMD = str(fake)
        try:
            return _core._run_claude_p(
                "PROMPT-SENTINEL-12345",
                book_dir=self.book_dir,
                phase="0d",
                step="ch01-design",
                **kw,
            )
        finally:
            _core.CLAUDE_CMD = orig

    def test_successful_call_logs_info_and_no_sidecar(self):
        fake = self._fake_claude('echo \'{"result":"ok"}\'\nexit 0\n')
        rc, _, _ = self._run(fake)
        self.assertEqual(rc, 0)

        row = [r for r in self._lines() if r["event"] == "claude_p.call"][-1]
        self.assertEqual(row["level"], "info")
        self.assertEqual(row["rc"], 0)
        self.assertEqual(row["phase"], "0d")
        self.assertEqual(row["step"], "ch01-design")
        self.assertIn("prompt_sha256", row)
        self.assertIsInstance(row["duration_ms"], int)
        self.assertIsNone(row["prompt_dump"])
        self.assertEqual(list(Path(_progress.run_log_path()).parent.glob("*.failure.txt")), [])

    def test_nonzero_rc_logs_error_and_dumps_full_prompt(self):
        fake = self._fake_claude('echo "partial output"\necho "the real error" >&2\nexit 3\n')
        rc, _, _ = self._run(fake)
        self.assertEqual(rc, 3)

        row = [r for r in self._lines() if r["event"] == "claude_p.call"][-1]
        self.assertEqual(row["level"], "error")
        self.assertEqual(row["rc"], 3)
        self.assertIn("partial output", row["stdout_tail"])
        self.assertIn("the real error", row["stderr_tail"])

        # Full evidence sidecar — the prompt is recoverable, not just its hash.
        self.assertTrue(row["prompt_dump"])
        dump = Path(row["prompt_dump"]).read_text()
        self.assertIn("PROMPT-SENTINEL-12345", dump)
        self.assertIn("partial output", dump)
        self.assertIn("the real error", dump)

    def test_timeout_captures_partial_output_that_used_to_be_discarded(self):
        from _authoring._core import AuthoringError

        fake = self._fake_claude('echo "work done before the hang"\nsleep 30\n')
        with self.assertRaises(AuthoringError):
            self._run(fake, timeout=2)

        row = [r for r in self._lines() if r["event"] == "claude_p.timeout"][-1]
        self.assertEqual(row["level"], "error")
        self.assertIn("timed out", row["msg"])
        self.assertTrue(row["prompt_dump"])

        dump = Path(row["prompt_dump"]).read_text()
        self.assertIn("PROMPT-SENTINEL-12345", dump)
        self.assertIn("work done before the hang", dump)

    def test_missing_binary_is_logged(self):
        from _authoring._core import AuthoringError

        with self.assertRaises(AuthoringError):
            self._run(self.tmp / "definitely-not-a-real-binary")

        row = [r for r in self._lines() if r["event"] == "claude_p.missing_binary"][-1]
        self.assertEqual(row["level"], "error")

    def test_llm_failure_surfaces_in_last_failure_dump(self):
        """End to end: the LLM call and the phase failure land in ONE file."""
        fake = self._fake_claude('echo "boom detail" >&2\nexit 9\n')
        self._run(fake)
        update_phase(self.book_dir, phase="0d", status="failed", error="authoring failed")

        text = (self.book_dir / "_system" / "last-failure.md").read_text()
        self.assertIn("authoring failed", text)
        self.assertIn("claude_p.call", text)
        self.assertIn("boom detail", text)
        self.assertIn("ch01-design", text)


class TestReadEvents(_RunLogCase):
    def test_read_run_events_respects_limit(self):
        init_run_log(self.book_dir)
        for i in range(5):
            log_event(f"e{i}", book_dir=self.book_dir)
        self.assertEqual(len(read_run_events()), 5)
        self.assertEqual([e["event"] for e in read_run_events(limit=2)], ["e3", "e4"])

    def test_read_run_events_skips_corrupt_lines(self):
        init_run_log(self.book_dir)
        log_event("good", book_dir=self.book_dir)
        with Path(_progress.run_log_path()).open("a") as fh:
            fh.write("{not json\n")
        log_event("also-good", book_dir=self.book_dir)
        self.assertEqual([e["event"] for e in read_run_events()], ["good", "also-good"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
