#!/usr/bin/env python3
"""The per-chapter loop under WORKERS — the path the default never takes.

`PER_CHAPTER_MAX_WORKERS` defaults to 1, so every other test in this suite exercises the
serial path. That makes the concurrent path the one place a defect could sit unnoticed
until a book was opted in and had already spent hours, so it is driven directly here.

The prize is measured, not assumed: 732 minutes of serial chapters on
`the-master-and-the-disciple` (20 chapters, median 37 min each). Four workers takes that
to roughly 185.

What is pinned:
  * every pending chapter runs, exactly once, under workers;
  * the state file ends up consistent — no chapter marked complete that the batched
    commit does not name, and no timing half-written;
  * ONE commit for the whole run, never one per worker;
  * a systemic halt stops chapters that have NOT started, which is the property the
    breaker's pre-start gate exists for;
  * a worker that raises is reported as this phase's failure rather than vanishing.
"""

from __future__ import annotations

import io
import sys
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import phases.chapter_driver as cd
from _convergence import ChapterOutcome
from _progress import initial_state, read_state, write_state

CHAPTERS = [f"ch{i:02d}" for i in range(1, 9)]


def _outcome(verdict="SHIP-READY", *, systemic=None) -> ChapterOutcome:
    return ChapterOutcome(
        chapter_slug="x",
        final_verdict=verdict,
        outer_iterations=1,
        fixer_attempts=0,
        p0_remaining=0,
        p1_remaining=0,
        p2_remaining=0,
        notes=["a reason"] if verdict == "FAILED" else [],
        systemic_halt=systemic,
    )


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._td = TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)
        (self.book / "chapter-contracts").mkdir(parents=True)
        for slug in CHAPTERS:
            (self.book / "chapter-contracts" / f"{slug}.yml").write_text("title: t\n", encoding="utf-8")
        state = initial_state("test-book", "books")
        write_state(self.book, state)
        self.commits: list[str] = []
        self.ran: list[str] = []
        self._lock = threading.Lock()

    def tearDown(self) -> None:
        self._td.cleanup()

    def _drive(self, *, workers: int, pass_fn=None) -> int:
        def _pass(book_dir, slug, **kw):
            with self._lock:
                self.ran.append(slug)
            result = (pass_fn or (lambda s: _outcome()))(slug)
            # The real pass leaves an episode text behind, and the per-chapter review
            # gate checks for exactly that. A mock that skips it makes the phase fail
            # for a reason that has nothing to do with what these tests are about.
            if result.final_verdict != "FAILED":
                (Path(book_dir) / "episodes").mkdir(parents=True, exist_ok=True)
                (Path(book_dir) / "episodes" / f"EP-{slug}.txt").write_text("framing\n", encoding="utf-8")
            return result

        def _commit(book_dir, subject):
            with self._lock:
                self.commits.append(subject)

        env = {"PER_CHAPTER_MAX_WORKERS": str(workers)}
        with (
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
            mock.patch.dict("os.environ", env),
            mock.patch.object(cd, "smoke_check_book", return_value=[]),
            mock.patch.object(cd, "per_chapter_pass", _pass),
            mock.patch.object(cd, "phase_git_commit", _commit),
            mock.patch.object(cd, "_sweep_orphan_episode_drafts", return_value=0),
            mock.patch.object(cd, "_chapter_cost_so_far", return_value=0.0),
            mock.patch.object(cd, "_book_cost_so_far", return_value=0.0),
            mock.patch.object(cd, "read_caps", return_value=(0.0, 0.0)),
            # Stop at the end of the chapter phase — the post-chapter chain is its own
            # module with its own tests, and driving it here would test something else.
            mock.patch("phases.post_chapter_driver.drive_post_chapter", return_value=0),
        ):
            return cd._drive_per_chapter_and_after(self.book)


class EveryChapterRunsTests(_Fixture):
    def test_serial_runs_every_chapter_once(self):
        rc = self._drive(workers=1)
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(self.ran), sorted(CHAPTERS))

    def test_workers_run_every_chapter_exactly_once(self):
        rc = self._drive(workers=4)
        self.assertEqual(rc, 0)
        self.assertEqual(
            sorted(self.ran),
            sorted(CHAPTERS),
            "a chapter was skipped or run twice under workers",
        )

    def test_workers_and_serial_agree_on_the_recorded_state(self):
        self._drive(workers=4)
        parallel_state = read_state(self.book)["phases"]["per-chapter"]

        # Same book, fresh, run serially.
        self.setUp()
        self._drive(workers=1)
        serial_state = read_state(self.book)["phases"]["per-chapter"]

        self.assertEqual(parallel_state["status"], serial_state["status"])
        self.assertEqual(
            sorted(parallel_state["completed_slugs"]),
            sorted(serial_state["completed_slugs"]),
            "workers and the serial path disagree about which chapters shipped",
        )


class OneCommitTests(_Fixture):
    """Exactly one commit for the CHAPTERS, however many workers ran them.

    Scoped to the per-chapter commit on purpose: the phase after the loop
    (`per-chapter-optimize`) makes its own commit, which is correct and unrelated. An
    unscoped count would pass or fail for reasons that have nothing to do with workers.
    """

    def _chapter_commits(self) -> list[str]:
        return [c for c in self.commits if "per-chapter —" in c]

    def test_workers_produce_exactly_one_chapter_commit(self):
        self._drive(workers=4)
        got = self._chapter_commits()
        self.assertEqual(
            len(got),
            1,
            f"expected ONE batched chapter commit, got {len(got)} — per-worker commits "
            f"would contend on .git/index.lock and land under each other's messages",
        )

    def test_the_commit_names_every_chapter(self):
        self._drive(workers=4)
        body = self._chapter_commits()[0]
        for slug in CHAPTERS:
            self.assertIn(slug, body, f"{slug} shipped but is missing from the batched commit")

    def test_serial_produces_the_same_single_chapter_commit(self):
        self._drive(workers=1)
        self.assertEqual(len(self._chapter_commits()), 1)


class ConsistentStateTests(_Fixture):
    def test_every_completed_chapter_has_a_finished_timing(self):
        self._drive(workers=4)
        timings = read_state(self.book)["phases"]["per-chapter"]["chapter_timings"]
        for slug in CHAPTERS:
            self.assertIn(slug, timings)
            self.assertIsNotNone(timings[slug]["completed_ts"], f"{slug} timing left half-written")
            self.assertIsNotNone(timings[slug]["duration_sec"])
            self.assertEqual(timings[slug]["verdict"], "SHIP-READY")

    def test_no_chapter_is_both_completed_and_failed(self):
        self._drive(workers=4)
        block = read_state(self.book)["phases"]["per-chapter"]
        overlap = set(block.get("completed_slugs", [])) & set(block.get("failed_slugs", []))
        self.assertEqual(overlap, set(), f"chapters recorded as both shipped and failed: {overlap}")

    def test_the_shared_collections_are_only_ever_serialised_through_the_snapshot(self):
        """No state write may build the chapter extras from the raw collections.

        `_snapshot()` takes the lock and copies; an inline
        `{"completed_slugs": sorted(...), "chapter_timings": chapter_timings}` does
        neither. Three of the phase's writes were built that way until 2026-08-08.
        They ran after the workers had joined, so nothing raced — but they were a
        second way to build the same extras, sitting one edit away from being moved
        somewhere a worker is still running, and `chapter_timings` was handed over
        without even a copy.
        """
        src = Path(cd.__file__).read_text(encoding="utf-8")
        # Counted rather than excluded by text: `_snapshot` itself contains the one
        # legitimate occurrence, so "not present" would fail on the fix and "present"
        # would pass on the defect.
        self.assertEqual(
            src.count('"completed_slugs": sorted('),
            1,
            "only _snapshot() may build completed_slugs — another site is serialising the "
            "shared collections its own way",
        )
        self.assertEqual(
            src.count('"chapter_timings": chapter_timings'),
            0,
            "a state write hands chapter_timings over uncopied and unlocked; use _snapshot()",
        )


class HaltStopsUnstartedChaptersTests(_Fixture):
    def test_a_systemic_halt_prevents_further_chapters_starting(self):
        # The property the pre-start gate exists for. The FIRST chapter to run halts the
        # book; with four workers at most four can be in flight, so the rest must never
        # start — and that is the saving, since each would have cost ~37 minutes.
        halted = threading.Event()

        def _pass(slug):
            if not halted.is_set():
                halted.set()
                return _outcome("FAILED", systemic="COST-CEILING: out of budget")
            return _outcome()

        rc = self._drive(workers=4, pass_fn=_pass)
        self.assertEqual(rc, 2, "a systemic halt must fail the phase")
        self.assertLess(
            len(self.ran),
            len(CHAPTERS),
            f"every chapter ran despite a halt on the first — the pre-start gate did not "
            f"fire (ran {len(self.ran)} of {len(CHAPTERS)})",
        )

    def test_the_halt_reason_reaches_the_state_file(self):
        def _pass(slug):
            return _outcome("FAILED", systemic="COST-CEILING: out of budget")

        self._drive(workers=4, pass_fn=_pass)
        err = read_state(self.book).get("last_error") or {}
        self.assertIn("COST-CEILING", str(err.get("message", "")))

    def test_chapters_that_shipped_before_the_halt_are_still_committed(self):
        seen: list[str] = []
        lock = threading.Lock()

        def _pass(slug):
            with lock:
                seen.append(slug)
                n = len(seen)
            if n > 2:
                return _outcome("FAILED", systemic="COST-CEILING: out of budget")
            return _outcome()

        self._drive(workers=1, pass_fn=_pass)
        self.assertEqual(len(self.commits), 1, "finished chapters were not committed before the halt")
        self.assertIn("ch01", self.commits[0])


class WorkerCrashTests(_Fixture):
    def test_a_raising_worker_is_reported_not_swallowed(self):
        def _pass(slug):
            if slug == "ch03":
                raise RuntimeError("worker exploded")
            return _outcome()

        rc = self._drive(workers=4, pass_fn=_pass)
        self.assertEqual(rc, 2, "a worker crash must fail the phase rather than pass quietly")
        block = read_state(self.book)["phases"]["per-chapter"]
        self.assertIn("ch03", block.get("failed_slugs", []))

    def test_the_crash_message_survives(self):
        def _pass(slug):
            if slug == "ch03":
                raise RuntimeError("worker exploded")
            return _outcome()

        self._drive(workers=4, pass_fn=_pass)
        err = str((read_state(self.book).get("last_error") or {}).get("message", ""))
        self.assertIn("worker exploded", err)


class SerialCrashTests(_Fixture):
    """The DEFAULT path must survive a chapter that raises — it was the unguarded one.

    `WorkerCrashTests` above covers the executor, which has caught worker exceptions
    since it was written. The serial loop — the path every book actually takes, since
    `PER_CHAPTER_MAX_WORKERS` defaults to 1 — called the chapter with no guard at all, so
    an exception escaped the whole phase.

    That was harmless while each chapter committed itself. Batching the commit to after
    the loop (2026-08-08) made it lossy: the exception skipped the one commit call, and
    every chapter that had already shipped was left uncommitted on disk. Nineteen shipped
    chapters could be discarded by a crash on the twentieth.
    """

    def _crash_on_ch03(self):
        def _pass(slug):
            if slug == "ch03":
                raise RuntimeError("serial explosion")
            return _outcome()

        return _pass

    def test_a_crash_does_not_lose_the_commit_for_chapters_that_shipped(self):
        self._drive(workers=1, pass_fn=self._crash_on_ch03())
        commits = [c for c in self.commits if "per-chapter —" in c]
        self.assertEqual(
            len(commits),
            1,
            "chapters that shipped before the crash were never committed — the exception "
            "escaped the phase and took the batched commit with it",
        )
        for shipped in ("ch01", "ch02"):
            self.assertIn(shipped, commits[0], f"{shipped} shipped but is missing from the commit")

    def test_a_crash_fails_the_phase_rather_than_propagating(self):
        rc = self._drive(workers=1, pass_fn=self._crash_on_ch03())
        self.assertEqual(rc, 2, "a chapter crash must be reported as this phase's failure")

    def test_the_crash_reaches_the_state_file(self):
        self._drive(workers=1, pass_fn=self._crash_on_ch03())
        block = read_state(self.book)["phases"]["per-chapter"]
        self.assertIn("ch03", block.get("failed_slugs", []))
        err = str((read_state(self.book).get("last_error") or {}).get("message", ""))
        self.assertIn("serial explosion", err)

    def test_serial_and_workers_agree_about_a_crash(self):
        """One handler serves both paths, so the outcome must not depend on the path."""
        serial_rc = self._drive(workers=1, pass_fn=self._crash_on_ch03())
        serial = read_state(self.book)["phases"]["per-chapter"]

        self.setUp()
        worker_rc = self._drive(workers=4, pass_fn=self._crash_on_ch03())
        parallel = read_state(self.book)["phases"]["per-chapter"]

        self.assertEqual(serial_rc, worker_rc)
        self.assertEqual(sorted(serial.get("failed_slugs", [])), sorted(parallel.get("failed_slugs", [])))


class InFlightMarkersTests(_Fixture):
    """`current_chapter` must not outlive the phase.

    `update_phase` MERGES extras into the phase block, and every progress beat writes
    `current_chapter` (and `convergence_iter` during convergence). Nothing cleared them,
    so a FINISHED book still reported the last chapter as the one it was working on —
    and `current_chapter` is exactly what a supervisor or status card reads to answer
    that question.
    """

    def test_a_completed_phase_reports_no_chapter_in_flight(self):
        self._drive(workers=1)
        block = read_state(self.book)["phases"]["per-chapter"]
        self.assertEqual(block["status"], "completed")
        self.assertIsNone(block.get("current_chapter"), "a finished phase still names a chapter in flight")
        self.assertIsNone(block.get("convergence_iter"))

    def test_a_failed_phase_also_clears_the_markers(self):
        def _pass(slug):
            return _outcome("FAILED") if slug == "ch02" else _outcome()

        self._drive(workers=1, pass_fn=_pass)
        block = read_state(self.book)["phases"]["per-chapter"]
        self.assertEqual(block["status"], "failed")
        self.assertIsNone(block.get("current_chapter"))

    def test_the_marker_is_still_written_while_the_phase_runs(self):
        """Clearing it at the end must not stop it being set during the run.

        Without the beat a supervisor cannot tell "moved to a new chapter" from "stuck on
        the same one", which is the whole reason the field exists.
        """
        seen: list[object] = []

        def _pass(slug):
            seen.append((read_state(self.book)["phases"]["per-chapter"] or {}).get("current_chapter"))
            return _outcome()

        self._drive(workers=1, pass_fn=_pass)
        self.assertIn("ch01", seen, "no progress beat recorded a chapter in flight")


class WorkerCountTests(_Fixture):
    def test_the_default_is_one_worker(self):
        # The capability is OPT-IN: merging it must not change how any book runs until
        # someone sets the variable. Asserted against the source because the default is
        # the thing under test — reading it from a live os.environ would only prove what
        # this process happens to have set.
        source = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("PER_CHAPTER_MAX_WORKERS", "1")', source)

    def test_a_nonsense_worker_count_falls_back_to_one(self):
        # `max(1, ...)` — a 0 or a negative must not mean "no chapters run at all".
        for value in ("0", "-4"):
            self.setUp()
            rc = self._drive(workers=int(value))
            self.assertEqual(rc, 0)
            self.assertEqual(sorted(self.ran), sorted(CHAPTERS), f"workers={value} ran nothing")


if __name__ == "__main__":
    unittest.main()
