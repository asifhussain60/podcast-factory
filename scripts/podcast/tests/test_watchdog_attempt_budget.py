#!/usr/bin/env python3
"""The relaunch budget must survive a watchdog respawn, and reset on progress.

`watch_orchestrator.sh` counted attempts in a shell variable while
`orchestrate_book.py` spawns a FRESH watchdog on every bare `--resume`. Each new
watchdog counted from 1, so the documented `--max-retries 20` ceiling never bound
across respawns: `orchestrator-the-master-and-the-disciple.log` reached 201
attempts with every line reporting "attempt N/20".

The count now lives in `orchestrator-state.json` under `phase_attempts`, keyed by
phase. Two properties matter and both are pinned here:

  * it PERSISTS, so a respawned watchdog continues the count rather than
    restarting it — the whole point;
  * it RESETS when the phase reaches `completed`, so the ceiling bounds
    failure-to-progress and never total work. Without this a long book would
    exhaust its budget simply by having many phases succeed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _progress import (
    ATTEMPTS_KEY,
    attempts_for,
    clear_attempts,
    initial_state,
    read_state,
    record_attempt,
    update_phase,
    write_state,
)

_ORIG_GATES: str | None = None


def setUpModule() -> None:
    """This file is about the attempt BUDGET, not about the phase-review gates.

    Its fixtures complete phases like 0b and 0d in a bare temp dir to move the budget
    along. Since 2026-08-09 a completed phase is reviewed, and completing a gated phase
    with none of its deliverables on disk correctly fails it — which would make every
    assertion here about `completed` fail for a reason that has nothing to do with the
    budget. Blocking is turned off through its own documented control surface rather
    than by fabricating artifacts these tests never read.
    """
    global _ORIG_GATES
    _ORIG_GATES = os.environ.get("PODCAST_PHASE_GATES")
    os.environ["PODCAST_PHASE_GATES"] = "off"


def tearDownModule() -> None:
    if _ORIG_GATES is None:
        os.environ.pop("PODCAST_PHASE_GATES", None)
    else:
        os.environ["PODCAST_PHASE_GATES"] = _ORIG_GATES


class AttemptBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)
        write_state(self.book, initial_state("test-book", "books"))

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_count_persists_across_processes(self):
        # Each call stands in for one watchdog relaunch — a separate process in
        # production, which is exactly why a shell variable could not hold this.
        self.assertEqual(record_attempt(self.book, "0b"), 1)
        self.assertEqual(record_attempt(self.book, "0b"), 2)
        self.assertEqual(record_attempt(self.book, "0b"), 3)
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 3)

    def test_counts_are_per_phase(self):
        record_attempt(self.book, "0b")
        record_attempt(self.book, "0b")
        record_attempt(self.book, "0d")
        state = read_state(self.book)
        self.assertEqual(attempts_for(state, "0b"), 2)
        self.assertEqual(attempts_for(state, "0d"), 1)

    def test_completing_a_phase_clears_its_budget(self):
        record_attempt(self.book, "0b")
        record_attempt(self.book, "0b")
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 2)
        update_phase(self.book, phase="0b", status="completed")
        self.assertEqual(
            attempts_for(read_state(self.book), "0b"),
            0,
            "a phase that completed must start fresh — the ceiling bounds failure-to-progress, not total work",
        )

    def test_failing_a_phase_does_not_clear_its_budget(self):
        record_attempt(self.book, "0b")
        update_phase(self.book, phase="0b", status="failed", error="boom")
        self.assertEqual(
            attempts_for(read_state(self.book), "0b"),
            1,
            "a failure must not refund the attempt, or the ceiling never binds",
        )

    def test_completing_one_phase_leaves_another_phases_budget_alone(self):
        record_attempt(self.book, "0b")
        record_attempt(self.book, "0d")
        update_phase(self.book, phase="0d", status="completed")
        state = read_state(self.book)
        self.assertEqual(attempts_for(state, "0b"), 1)
        self.assertEqual(attempts_for(state, "0d"), 0)

    def test_clear_attempts_is_safe_when_nothing_recorded(self):
        clear_attempts(self.book, "0b")  # must not raise
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 0)

    def test_attempts_survive_an_unrelated_state_write(self):
        record_attempt(self.book, "0b")
        update_phase(self.book, phase="0b", status="running")
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 1)

    def test_reader_tolerates_a_state_file_written_before_the_field_existed(self):
        state = read_state(self.book)
        state.pop(ATTEMPTS_KEY, None)
        write_state(self.book, state)
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 0)
        self.assertEqual(record_attempt(self.book, "0b"), 1)


class BudgetCliTests(unittest.TestCase):
    """The CLI the watchdog shells out to must use exit codes, not text parsing."""

    CLI = SCRIPTS_PODCAST / "watchdog_budget.py"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.CLI), *args],
            capture_output=True,
            text=True,
            cwd=SCRIPTS_PODCAST.parents[1],
        )

    def test_unresolvable_book_degrades_rather_than_blocking(self):
        # Exit 2, NOT 3: an unresolvable book must never stop a relaunch the old
        # code would have made. Silently blocking here would strand a run.
        proc = self._run("a-slug-that-does-not-exist-anywhere", "--max", "5")
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_help_works(self):
        proc = self._run("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--max", proc.stdout)


class BudgetExhaustionTests(unittest.TestCase):
    """Exit 3 is the code that actually stops a 201-attempt runaway.

    Driven against a temp book by pointing the CLI's own resolver at it, because
    the behaviour under test is the ceiling, not path resolution (covered above).
    """

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)
        state = initial_state("temp-book", "books")
        state["phase"] = "0b"
        write_state(self.book, state)

    def tearDown(self) -> None:
        self._td.cleanup()

    def _invoke(self, max_attempts: int) -> int:
        import unittest.mock as m

        import watchdog_budget as wb

        with m.patch.object(wb, "find_content", return_value=("Islamic", "temp-book", self.book)):
            with m.patch.object(sys, "argv", ["watchdog_budget", "temp-book", "--max", str(max_attempts)]):
                return wb.main()

    def test_within_budget_returns_zero(self):
        self.assertEqual(self._invoke(3), 0)  # 1st
        self.assertEqual(self._invoke(3), 0)  # 2nd
        self.assertEqual(self._invoke(3), 0)  # 3rd, at the ceiling

    def test_exceeding_the_ceiling_returns_three(self):
        for _ in range(3):
            self._invoke(3)
        self.assertEqual(self._invoke(3), 3, "the 4th attempt against a ceiling of 3 must refuse")

    def test_a_ceiling_of_zero_means_unlimited(self):
        for _ in range(25):
            self.assertEqual(self._invoke(0), 0)
        self.assertEqual(attempts_for(read_state(self.book), "0b"), 25)

    def test_completing_the_phase_restores_the_budget(self):
        for _ in range(3):
            self._invoke(3)
        self.assertEqual(self._invoke(3), 3)
        update_phase(self.book, phase="0b", status="completed")
        state = read_state(self.book)
        state["phase"] = "0b"  # a --retry-phase puts us back on 0b
        write_state(self.book, state)
        self.assertEqual(self._invoke(3), 0, "after real progress the phase gets a fresh budget")


if __name__ == "__main__":
    unittest.main()
