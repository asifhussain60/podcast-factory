#!/usr/bin/env python3
"""The orchestrator log must have exactly ONE writer per line.

`watch_orchestrator.sh` writes everything it and the orchestrator produce into
the run log itself, through `tee -a "$LOG"` — its `_log` helper and the pipe
around the orchestrator invocation. Until 2026-08-08,
`_maybe_relaunch_under_watchdog` ALSO handed that same log file to the spawned
watchdog as its stdout, so tee's append and tee's stdout both landed in the same
file and every line was written twice. Measured on a real run:
`orchestrator-spiritual-ethos.log` carried 128 watchdog lines for 64 distinct
ones — an exact 2x.

That doubling was most of the reason a run APPEARED to re-run its steps, and it
made a genuine repeat impossible to distinguish from an echo of the last one.

Two things are pinned here, because fixing the first by dropping BOTH streams
would silently lose the second:

  1. stdout is discarded — tee already owns the log, so a second handle on it
     can only duplicate.
  2. stderr is still captured — it is the one stream tee does NOT carry, so a
     bash syntax error or an early crash inside the watchdog itself must still
     reach the log rather than vanishing.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import orchestrate_book as ob


class SpawnRedirectionTests(unittest.TestCase):
    """The spawn must not hand the log file to the child as stdout."""

    #: `_maybe_relaunch_under_watchdog` opens the run log before spawning, so
    #: exercising it creates a real (empty) file under _workspace/logs. Named
    #: here and removed in tearDown so the suite leaves no debris in the repo.
    SLUG = "test-slug-does-not-exist"

    def tearDown(self) -> None:
        stray = SCRIPTS_PODCAST.parents[1] / "_workspace" / "logs" / f"orchestrator-{self.SLUG}.log"
        if stray.exists() and stray.stat().st_size == 0:
            stray.unlink()

    def _capture_popen_kwargs(self) -> dict:
        with mock.patch.object(ob.subprocess, "Popen") as popen, mock.patch.object(ob.sys, "exit") as _exit:
            _exit.side_effect = SystemExit(0)
            with self.assertRaises(SystemExit):
                ob._maybe_relaunch_under_watchdog(self.SLUG)
            self.assertTrue(popen.called, "the watchdog was never spawned")
            return popen.call_args.kwargs

    def test_stdout_is_discarded_not_pointed_at_the_log(self):
        kwargs = self._capture_popen_kwargs()
        self.assertIs(
            kwargs.get("stdout"),
            subprocess.DEVNULL,
            "stdout must be DEVNULL — the watchdog tees to the log itself, so a "
            "second handle on that file writes every line twice",
        )

    def test_stderr_is_still_captured_to_a_file(self):
        kwargs = self._capture_popen_kwargs()
        stderr = kwargs.get("stderr")
        self.assertIsNot(
            stderr,
            subprocess.DEVNULL,
            "stderr must NOT be discarded — it is the only stream tee does not carry, so a watchdog crash would vanish",
        )
        self.assertTrue(
            hasattr(stderr, "write"),
            f"stderr should be an open file handle on the run log, got {stderr!r}",
        )

    def test_stderr_is_not_merged_into_stdout(self):
        # stderr=STDOUT while stdout=DEVNULL would throw the crash away too.
        kwargs = self._capture_popen_kwargs()
        self.assertIsNot(kwargs.get("stderr"), subprocess.STDOUT)


class DoublingBehaviourTests(unittest.TestCase):
    """End-to-end: reproduce the writer collision and prove the fix removes it.

    Uses the same shape as the real thing — a shell script that tees to a log,
    spawned by Python with that log as a redirection target — rather than
    asserting on the source text, so it fails on the BEHAVIOUR rather than on
    how the behaviour happens to be written.
    """

    SCRIPT = 'LOG="$1"\n_log() { echo "[watchdog] $*" | tee -a "$LOG"; }\n_log "attempt 1/20"\n'

    def _run(self, *, stdout, stderr) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "wd.sh"
            script.write_text(self.SCRIPT, encoding="utf-8")
            log = Path(td) / "run.log"
            log.touch()
            with open(log, "a") as fh:
                subprocess.run(
                    ["/bin/bash", str(script), str(log)],
                    stdout=(fh if stdout == "log" else subprocess.DEVNULL),
                    stderr=(fh if stderr == "log" else subprocess.DEVNULL),
                )
            return [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.startswith("[watchdog")]

    def test_the_old_wiring_doubled_every_line(self):
        # Guards the test itself: if this stops doubling, the reproduction has
        # drifted and the passing test below would prove nothing.
        lines = self._run(stdout="log", stderr="log")
        self.assertEqual(len(lines), 2, f"expected the old wiring to double, got {lines!r}")
        self.assertEqual(len(set(lines)), 1)

    def test_the_new_wiring_writes_each_line_once(self):
        lines = self._run(stdout="devnull", stderr="log")
        self.assertEqual(len(lines), 1, f"expected exactly one copy per line, got {lines!r}")


if __name__ == "__main__":
    unittest.main()
