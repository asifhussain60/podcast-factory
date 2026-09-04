#!/usr/bin/env python3
"""A phase that HALTS is a clean stop for the watchdog, not a crash to relaunch.

`watch_orchestrator.sh` recognised only two halts as terminal — `finalize/halted`
and `done` — so any other phase that halted cleanly for a human artifact
(`audio-ingest` waiting on a NotebookLM drop, `0book-slide-import` waiting on deck
PDFs) came back as "rc=0 but phase not terminal" and was relaunched until the
persistent attempt budget went FATAL. Those attempts stayed recorded, so the very
next `--resume` after the human dropped the audio exited BUDGET EXHAUSTED before
running anything, and the printed remedy (`--retry-phase <phase>`) did not clear
the count either.

Two things are pinned here, both against the REAL script driven in a throwaway
repo with a stub orchestrator:

  1. a halting phase produces exactly ONE launch, exit 0, and the phase's
     attempt count is not left behind;
  2. `--retry-phase` clears the retried phase's attempt count, so the remedy the
     watchdog prints on exhaustion actually restores the budget.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _progress import ATTEMPTS_KEY, attempts_for, initial_state, read_state, record_attempt, write_state

SLUG = "halting-book"
PHASE = "audio-ingest"

# Stub orchestrator: counts its launches, then halts the phase the way
# audio_ingest_driver does (rc 0, status=halted, a `reason` extra).
STUB_ORCHESTRATOR = textwrap.dedent(
    """\
    import json, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    counter = root / "launches.txt"
    counter.write_text(str(int(counter.read_text() or "0") + 1) if counter.exists() else "1")
    state_path = root / "content" / "Islamic" / "%s" / "_system" / "orchestrator-state.json"
    state = json.loads(state_path.read_text())
    state["phase"] = "%s"
    state["phase_status"] = "halted"
    state["phases"]["%s"] = {"status": "halted", "reason": "awaiting NotebookLM audio drop"}
    state_path.write_text(json.dumps(state))
    sys.exit(0)
    """
    % (SLUG, PHASE, PHASE)
)


class HaltingPhaseStopsTheWatchdog(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.repo = Path(self._td.name) / "repo"
        scripts = self.repo / "scripts" / "podcast"
        scripts.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        # The script under test and the real budget CLI; everything they import
        # (`_paths`, `_progress`) resolves through PYTHONPATH to the real modules,
        # rooted at the temp repo via PODCAST_FACTORY_ROOT.
        shutil.copy(SCRIPTS_PODCAST / "watch_orchestrator.sh", scripts / "watch_orchestrator.sh")
        shutil.copy(SCRIPTS_PODCAST / "watchdog_budget.py", scripts / "watchdog_budget.py")
        (scripts / "orchestrate_book.py").write_text(STUB_ORCHESTRATOR, encoding="utf-8")
        (scripts / "book_status_card.py").write_text("print('card')\n", encoding="utf-8")
        self.book = self.repo / "content" / "Islamic" / SLUG
        (self.book / "_system").mkdir(parents=True)
        state = initial_state(SLUG, "books")
        state["phase"] = PHASE
        state["phase_status"] = "pending"
        write_state(self.book, state)

    def tearDown(self) -> None:
        self._td.cleanup()

    def _run_watchdog(self, max_retries: int = 2) -> tuple[int, str]:
        """Returns (exit code, everything the watchdog logged).

        Output goes to a FILE, as the real spawn does (see
        test_watchdog_log_single_write.py) — never a pipe: the heartbeat subshell's
        `sleep` inherits stdout and would hold a pipe open long after the watchdog
        itself has exited.
        """
        env = {
            **os.environ,
            "PODCAST_FACTORY_ROOT": str(self.repo),
            "PYTHONPATH": str(SCRIPTS_PODCAST),
            "HEARTBEAT_S": "3600",
            "RETRY_DELAY_S": "0",
        }
        out = self.repo / "watchdog-stdout.txt"
        with open(out, "w", encoding="utf-8") as fh:
            proc = subprocess.run(
                [
                    "/bin/bash",
                    str(self.repo / "scripts" / "podcast" / "watch_orchestrator.sh"),
                    SLUG,
                    "--max-retries",
                    str(max_retries),
                ],
                stdout=fh,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=self.repo,
                timeout=120,
            )
        return proc.returncode, out.read_text(encoding="utf-8")

    def _launches(self) -> int:
        counter = self.repo / "launches.txt"
        return int(counter.read_text()) if counter.exists() else 0

    def test_a_halting_phase_is_launched_once_and_exits_clean(self):
        rc, log = self._run_watchdog(max_retries=2)
        self.assertEqual(self._launches(), 1, f"a halt must not be relaunched:\n{log}")
        self.assertEqual(rc, 0, f"a halt is a clean stop:\n{log}")
        self.assertIn(PHASE, log)
        self.assertIn("awaiting NotebookLM audio drop", log, "the halt reason must be printed")
        self.assertEqual(
            attempts_for(read_state(self.book), PHASE),
            0,
            "a halt is progress to a human gate, not a failed attempt — the budget must not carry it forward",
        )
        self.assertFalse((self.book / "_system" / "watchdog.json").exists(), "sentinel must be removed on a clean stop")


class RetryPhaseRestoresTheBudget(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)
        write_state(self.book, initial_state("test-book", "books"))

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_clear_downstream_phases_forgets_the_retried_phases_attempts(self):
        from phases.resume_dispatcher import _clear_downstream_phases

        for _ in range(3):
            record_attempt(self.book, "0b")
        record_attempt(self.book, "0a")
        state = read_state(self.book)
        state["phase"], state["phase_status"] = "0b", "failed"
        _clear_downstream_phases(state, "0b", log=lambda *_: None)
        write_state(self.book, state)
        state = read_state(self.book)
        self.assertEqual(attempts_for(state, "0b"), 0, "the remedy the watchdog prints must restore the budget")
        self.assertEqual(attempts_for(state, "0a"), 1, "an unrelated phase's count is untouched")
        self.assertIn(ATTEMPTS_KEY, json.dumps(state))


if __name__ == "__main__":
    unittest.main()
