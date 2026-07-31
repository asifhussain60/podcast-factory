#!/usr/bin/env python3
"""`--unattended` clears the gates that PACE a run, never one that waits on a file.

The distinction is the whole point. A human-approval gate (06a source review)
exists to make a person look before money is spent; authorizing the run in advance
is a legitimate way to satisfy it. A halt that waits for a dropped .m4a or a curated
visual layout is waiting for a FILE, and no amount of authorization makes a missing
file appear — auto-clearing those would just fail later and less clearly.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _progress import UNATTENDED_KEY, unattended_run


def _book(tmp: Path, state: dict | None) -> Path:
    bd = tmp / "a-book"
    (bd / "_system").mkdir(parents=True, exist_ok=True)
    if state is not None:
        (bd / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
    return bd


class UnattendedFlagTests(unittest.TestCase):
    def test_absent_means_attended(self) -> None:
        with TemporaryDirectory() as td:
            self.assertFalse(unattended_run(_book(Path(td), {"book_slug": "a-book"})))

    def test_set_means_unattended(self) -> None:
        with TemporaryDirectory() as td:
            self.assertTrue(unattended_run(_book(Path(td), {"book_slug": "a-book", UNATTENDED_KEY: True})))

    def test_no_state_file_is_attended_not_a_crash(self) -> None:
        # The safe direction: an unreadable run pauses for a human rather than
        # driving itself past every gate.
        with TemporaryDirectory() as td:
            self.assertFalse(unattended_run(_book(Path(td), None)))

    def test_explicit_false_means_attended(self) -> None:
        with TemporaryDirectory() as td:
            self.assertFalse(unattended_run(_book(Path(td), {UNATTENDED_KEY: False})))


class TheFlagIsWiredToTheCLIAndPersistedTests(unittest.TestCase):
    """It has to survive the process boundary or it does nothing.

    The watchdog re-invokes `--resume` in a fresh process that never saw argv, so
    a flag held only in memory would revert to attended on the first retry — and
    the book would sit at the same gate it was launched to run past.
    """

    def test_the_orchestrator_exposes_the_flag(self) -> None:
        text = (SCRIPTS_PODCAST / "orchestrate_book.py").read_text(encoding="utf-8")
        self.assertIn('"--unattended"', text)

    def test_the_initial_run_persists_it_into_state(self) -> None:
        text = (SCRIPTS_PODCAST / "phases" / "initial_driver.py").read_text(encoding="utf-8")
        self.assertIn("UNATTENDED_KEY", text)
        self.assertIn("unattended", text)

    def test_the_review_gate_consults_it(self) -> None:
        text = (SCRIPTS_PODCAST / "phases" / "resume_dispatcher.py").read_text(encoding="utf-8")
        self.assertIn("unattended_run(book_dir)", text)

    def test_resume_latches_it_BEFORE_the_watchdog_handoff(self) -> None:
        """Order matters, and getting it wrong makes the flag a no-op.

        `--resume` relaunches under the watchdog, replacing this process with one
        invoked WITHOUT --unattended. A flag latched inside run_resume is therefore
        never written at all: the first attempt observed exactly that, the book
        sitting at the same gate it had just been authorized past.
        """
        text = (SCRIPTS_PODCAST / "orchestrate_book.py").read_text(encoding="utf-8")
        latch = text.find("UNATTENDED_KEY")
        handoff = text.find("_maybe_relaunch_under_watchdog(slug_for_lock)")
        self.assertGreater(latch, 0, "the resume path never persists the flag")
        self.assertGreater(handoff, 0)
        self.assertLess(latch, handoff, "the flag is latched after the watchdog handoff — it can never be written")

    def test_artifact_halts_do_NOT_consult_it(self) -> None:
        # audio-ingest waits for dropped .m4a; the book lane waits for curated
        # visuals. Neither may be auto-cleared — authorization cannot supply a file.
        for module in ("audio_ingest_driver.py", "book_driver.py"):
            text = (SCRIPTS_PODCAST / "phases" / module).read_text(encoding="utf-8")
            self.assertNotIn(
                "unattended",
                text,
                f"{module} auto-clears a halt that waits on a human-supplied file",
            )


if __name__ == "__main__":
    unittest.main()
