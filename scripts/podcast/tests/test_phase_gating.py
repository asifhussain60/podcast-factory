#!/usr/bin/env python3
"""A failing gate must FAIL the phase, not leave a note beside a completed one.

Until 2026-08-09 the phase review ran, wrote its verdict into the book's state, and let
the run carry on to the next phase regardless. A phase could finish carrying
`PHASE-BROKEN` and the pipeline would advance over it — which made the review a report
nobody was obliged to read rather than a gate.

What is pinned here:

  * a blocking gate rewrites the phase as `failed`, with the gate's own reason as the
    error a human reads;
  * an advisory gate never can, however loudly it fails;
  * the run's pointers walk BACK, so a resume returns to the phase that needs fixing
    instead of stepping past it;
  * the escape hatch withdraws the ability to fail a phase without withdrawing the
    review — a false positive must never be a reason to wait for a code change;
  * a phase with no gates pays nothing at all;
  * gates see the extras written by the very call that is completing the phase, which
    is where the first implementation of this was wrong: it reviewed before the write,
    so `completed_slugs` was always one call stale and the per-chapter lane reported
    itself short of chapters it had just recorded;
  * the review can never itself break a phase — a crashing reviewer leaves the run
    exactly as it was before this layer existed.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _phase_review as pr  # noqa: E402
import _progress as prog  # noqa: E402
from _progress import initial_state, read_state, update_phase, write_state  # noqa: E402


class _Book(unittest.TestCase):
    def setUp(self) -> None:
        self._td = TemporaryDirectory()
        self.book = Path(self._td.name) / "bk"
        (self.book / "_system").mkdir(parents=True)
        for d in ("chapter-contracts", "chapters", "episodes", "book", "audits"):
            (self.book / d).mkdir()
        write_state(self.book, initial_state("bk", "books"))

    def tearDown(self) -> None:
        self._td.cleanup()

    def _contract(self, slug: str = "c1") -> None:
        (self.book / "chapter-contracts" / f"{slug}.yml").write_text("title: t\n", encoding="utf-8")

    def _episode(self, slug: str = "c1") -> None:
        (self.book / "episodes" / f"EP01-{slug}.txt").write_text("framing\n", encoding="utf-8")


class BlockingTests(_Book):
    def test_a_blocking_gate_fails_the_phase(self):
        self._contract()  # a chapter with no episode -> PPC1 fails
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "failed")
        self.assertEqual(state["phases"]["per-chapter"]["status"], "failed")

    def test_the_gates_own_reason_is_what_a_human_reads(self):
        self._contract()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        message = str((state.get("last_error") or {}).get("message", ""))
        self.assertIn("PPC1", message, "the failing gate must be named")
        self.assertIn("episode", message, "the reason must say what was actually wrong")

    def test_the_run_points_back_at_the_phase_that_needs_fixing(self):
        self._contract()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["next_phase"], "per-chapter", "a resume must return to the failed phase")
        self.assertNotEqual(
            state["last_completed_phase"], "per-chapter", "a phase its own review failed was not completed"
        )

    def test_last_completed_walks_back_to_the_previous_real_completion(self):
        # 'branch' has no gates, so it completes for real; per-chapter then fails.
        update_phase(self.book, phase="branch", status="completed")
        self._contract()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["last_completed_phase"], "branch")

    def test_a_passing_gate_completes_normally(self):
        self._contract()
        self._episode()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "completed")
        self.assertEqual(state["last_completed_phase"], "per-chapter")
        self.assertEqual(state["phases"]["per-chapter"]["review"]["verdict"], pr.VERDICT_SOUND)

    def test_an_advisory_gate_cannot_fail_a_phase(self):
        self._contract()
        self._episode()
        advisory = [("PZ9", "advisory", lambda _bd: (False, "advisory complaint"))]
        with mock.patch.dict(pr.OWN_GATES, {"per-chapter": advisory}):
            state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "completed")
        self.assertEqual(state["phases"]["per-chapter"]["review"]["verdict"], pr.VERDICT_CONCERNS)


class GatesSeeThisCallsExtrasTests(_Book):
    """The ordering bug that the first implementation had.

    Gates read the book's state from disk, and a phase reports what it did through the
    `extras` of the call that completes it. Reviewing BEFORE that write asked the gates
    about the previous call's state, so the per-chapter lane reported itself short of
    chapters it had just recorded, and every completion of it failed.
    """

    def test_completed_slugs_from_this_call_are_visible_to_the_gate(self):
        self._contract("c1")
        self._episode("c1")
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "completed", "the gate did not see this call's completed_slugs")

    def test_a_chapter_missing_from_this_calls_extras_still_fails(self):
        # The same path must still catch the real defect: a chapter never attempted.
        self._contract("c1")
        self._contract("c2")
        self._episode("c1")
        self._episode("c2")
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "failed")
        self.assertIn("c2", str((state.get("last_error") or {}).get("message", "")))


class EscapeHatchTests(_Book):
    def setUp(self) -> None:
        super().setUp()
        self._orig = os.environ.get(pr.BLOCKING_ENV)

    def tearDown(self) -> None:
        if self._orig is None:
            os.environ.pop(pr.BLOCKING_ENV, None)
        else:
            os.environ[pr.BLOCKING_ENV] = self._orig
        super().tearDown()

    def test_the_hatch_withdraws_blocking_but_not_the_review(self):
        self._contract()
        os.environ[pr.BLOCKING_ENV] = "off"
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "completed", "blocking should be off")
        review = state["phases"]["per-chapter"]["review"]
        self.assertEqual(review["verdict"], pr.VERDICT_BROKEN, "the finding must still be recorded")
        self.assertIsNone(review["blocking_fail"], "a suppressed block must not read as a live one")

    def test_every_documented_off_value_works(self):
        for value in ("0", "off", "false", "no", "OFF", " Off "):
            os.environ[pr.BLOCKING_ENV] = value
            self.assertFalse(pr.blocking_enabled(), f"{value!r} should disable blocking")

    def test_blocking_is_on_by_default_and_for_any_other_value(self):
        os.environ.pop(pr.BLOCKING_ENV, None)
        self.assertTrue(pr.blocking_enabled())
        for value in ("on", "1", "yes", "banana"):
            os.environ[pr.BLOCKING_ENV] = value
            self.assertTrue(pr.blocking_enabled(), f"{value!r} should leave blocking on")


class CostAndSafetyTests(_Book):
    def test_a_phase_with_no_gates_is_not_reviewed_at_all(self):
        state = update_phase(self.book, phase="branch", status="completed")
        self.assertEqual(state["phase_status"], "completed")
        self.assertNotIn("review", state["phases"]["branch"])

    def test_a_non_completed_status_is_never_reviewed(self):
        self._contract()  # would fail PPC1 if it were reviewed
        for status in ("running", "failed", "halted", "skipped"):
            state = update_phase(self.book, phase="per-chapter", status=status)
            self.assertEqual(state["phase_status"], status)
            self.assertNotIn("review", state["phases"]["per-chapter"])

    def test_a_crashing_review_leaves_the_phase_exactly_as_it_was(self):
        """A review is an observer. A fault in the observing must not decide the
        fate of the phase it was watching."""
        self._contract()
        with mock.patch.object(prog, "_phase_review_for", side_effect=RuntimeError("reviewer exploded")):
            with self.assertRaises(RuntimeError):
                update_phase(self.book, phase="per-chapter", status="completed")

        # And the guarded helper itself swallows a broken reviewer rather than raising.
        with mock.patch.object(pr, "review_phase", side_effect=RuntimeError("boom")):
            self.assertIsNone(prog._phase_review_for(self.book, "per-chapter", "completed"))

    def test_a_broken_reviewer_lets_the_phase_complete(self):
        self._contract()
        with mock.patch.object(pr, "review_phase", side_effect=RuntimeError("boom")):
            state = update_phase(self.book, phase="per-chapter", status="completed")
        self.assertEqual(state["phase_status"], "completed", "a broken reviewer must not fail the phase")

    def test_a_failed_phase_is_recoverable_by_retry(self):
        """A gate may delay a book; it must never strand one.

        `--retry-phase` resets any phase in PHASES to pending and clears everything
        downstream, so the recovery path for a gate failure is the same one every other
        phase failure already uses.
        """
        from _progress import PHASES

        self.assertIn("per-chapter", PHASES)
        self._contract()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertEqual(state["phase_status"], "failed")
        # The dispatcher's reset is what a retry performs; assert the block it targets
        # is present and ordinary, not some special gate-failure shape it cannot handle.
        block = read_state(self.book)["phases"]["per-chapter"]
        self.assertEqual(block["status"], "failed")
        self.assertIn("review", block)


class ReportTests(_Book):
    def test_the_full_report_is_written_to_disk_for_a_blocked_phase(self):
        self._contract()
        update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        report = self.book / "_system" / "phase-reviews" / "per-chapter.json"
        self.assertTrue(report.is_file(), "the phase review report must survive a blocking failure")

    def test_the_state_summary_names_the_blocking_gate(self):
        self._contract()
        state = update_phase(self.book, phase="per-chapter", status="completed", extras={"completed_slugs": ["c1"]})
        self.assertIn("PPC1", str(state["phases"]["per-chapter"]["review"]["blocking_fail"]))


if __name__ == "__main__":
    unittest.main()
