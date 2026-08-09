#!/usr/bin/env python3
"""The C3 circuit breaker must make the SAME decisions, and survive workers.

The breaker halts the book on a systemic failure rather than grinding through twenty
chapters reproducing one root cause. Two signals: the first chapter attempted died in
under five seconds (a deterministic bug, not content), or the same normalized failure
has hit a second chapter (paying for the same lesson twice is waste).

Its value is ECONOMIC and entirely about TIMING — it exists to stop before the remaining
chapters are paid for. That is why the verdict is now asked at `begin()`, before a
chapter starts, and not only after one fails: a worker that has not begun can still
decline, which is the only way the saving survives concurrency.

Two things are pinned here:

  * EQUIVALENCE — the decisions match the inline version this replaced, so extracting it
    while the loop is still serial changed no behaviour;
  * CONCURRENCY SAFETY — the counter and the signature map are correct under threads,
    and the pre-start gate actually stops work rather than merely reporting.
"""

from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _chapter_breaker import (
    FAST_FAILURE_SEC,
    SHARED_FAILURE_CHAPTERS,
    BreakerTripped,
    ChapterBreaker,
    failure_signature,
)
from _chapter_cost_caps import BookCeiling

#: Admission never touches the filesystem — spend is supplied by the injected function —
#: so a placeholder path is enough and keeps these tests free of temp dirs.
BOOK = Path("/nonexistent-book")


class SignatureTests(unittest.TestCase):
    def test_numbers_collapse_so_one_root_cause_matches_across_chapters(self):
        a = failure_signature("word count 2 outside band")
        b = failure_signature("word count 5000 outside band")
        self.assertEqual(a, b)

    def test_genuinely_different_failures_stay_distinct(self):
        a = failure_signature("word count outside band")
        b = failure_signature("contract missing required key")
        self.assertNotEqual(a, b)

    def test_signature_is_bounded(self):
        self.assertLessEqual(len(failure_signature("x " * 500)), 80)


class FirstChapterFastFailureTests(unittest.TestCase):
    """Signal (a): the first chapter ATTEMPTED died fast — a deterministic bug."""

    def setUp(self) -> None:
        self.b = ChapterBreaker()

    def test_first_chapter_failing_fast_trips_the_breaker(self):
        o = self.b.begin("ch01")
        systemic = self.b.record_failure("ch01", "boom", 1.2, o)
        self.assertIsNotNone(systemic)
        self.assertIn("first attempted chapter", systemic)
        self.assertIn("ch01", systemic)

    def test_first_chapter_failing_slowly_does_not_trip(self):
        # A slow failure is content, not a deterministic bug — degrade, do not halt.
        o = self.b.begin("ch01")
        self.assertIsNone(self.b.record_failure("ch01", "boom", FAST_FAILURE_SEC + 1, o))
        self.assertIsNone(self.b.tripped())

    def test_a_later_chapter_failing_fast_does_not_trip_on_that_signal(self):
        # Only the FIRST attempt carries the deterministic-bug reading; a fast failure
        # on chapter 5 with a unique signature is just one bad chapter.
        self.b.begin("ch01")
        o2 = self.b.begin("ch02")
        self.assertIsNone(self.b.record_failure("ch02", "unique failure here", 0.5, o2))

    def test_the_boundary_is_exclusive(self):
        o = self.b.begin("ch01")
        self.assertIsNone(
            self.b.record_failure("ch01", "boom", FAST_FAILURE_SEC, o),
            "a failure exactly at the threshold must not count as fast",
        )


class SharedFailureTests(unittest.TestCase):
    """Signal (b): the same failure across chapters — the archetype-over-rerun rule."""

    def setUp(self) -> None:
        self.b = ChapterBreaker()

    def test_the_same_failure_on_a_second_chapter_trips(self):
        o1 = self.b.begin("ch01")
        self.b.record_failure("ch01", "word count 100 outside band", 60.0, o1)
        o2 = self.b.begin("ch02")
        systemic = self.b.record_failure("ch02", "word count 900 outside band", 60.0, o2)
        self.assertIsNotNone(systemic)
        self.assertIn("same failure across 2 chapters", systemic)
        self.assertIn("ch01", systemic)
        self.assertIn("ch02", systemic)

    def test_different_failures_on_two_chapters_do_not_trip(self):
        o1 = self.b.begin("ch01")
        self.b.record_failure("ch01", "word count outside band", 60.0, o1)
        o2 = self.b.begin("ch02")
        self.assertIsNone(self.b.record_failure("ch02", "contract missing key", 60.0, o2))

    def test_the_same_chapter_failing_twice_does_not_count_as_two(self):
        # A retry of one chapter is not two chapters sharing a root cause.
        o = self.b.begin("ch01")
        self.b.record_failure("ch01", "word count outside band", 60.0, o)
        self.assertIsNone(self.b.record_failure("ch01", "word count outside band", 60.0, o))

    def test_the_threshold_is_the_declared_constant(self):
        self.assertEqual(SHARED_FAILURE_CHAPTERS, 2)


class PreStartGateTests(unittest.TestCase):
    """The property the extraction exists for: an unstarted chapter can decline."""

    def setUp(self) -> None:
        self.b = ChapterBreaker()

    def test_begin_refuses_once_tripped(self):
        o = self.b.begin("ch01")
        self.b.record_failure("ch01", "boom", 0.5, o)
        with self.assertRaises(BreakerTripped) as ctx:
            self.b.begin("ch02")
        self.assertIn("first attempted chapter", ctx.exception.reason)

    def test_begin_refusing_does_not_consume_an_ordinal(self):
        o = self.b.begin("ch01")
        self.b.record_failure("ch01", "boom", 0.5, o)
        for slug in ("ch02", "ch03"):
            with self.assertRaises(BreakerTripped):
                self.b.begin(slug)
        self.assertEqual(self.b.attempted(), 1, "a refused start must not count as an attempt")

    def test_the_refusal_reason_is_the_first_one(self):
        # The operator reads this to diagnose; a later failure must not overwrite it.
        o1 = self.b.begin("ch01")
        first = self.b.record_failure("ch01", "the original cause", 0.5, o1)
        self.b.record_failure("ch01", "a different later cause", 0.5, o1)
        self.assertEqual(self.b.tripped(), first)


class ExternalTripTests(unittest.TestCase):
    """`trip()` is how the per-book cost ceiling halts the book.

    A ceiling breach is already a systemic halt in this pipeline — same `systemic_halt`
    field, same COST-CEILING marker that tells the supervisor not to relaunch — so it
    shares this gate rather than getting a parallel mechanism. There should be exactly
    one answer to "may a new chapter start", however many reasons it can say no.
    """

    def setUp(self) -> None:
        self.b = ChapterBreaker()

    def test_tripping_stops_new_chapters_starting(self):
        self.b.begin("ch01")
        self.b.trip("COST-CEILING: book has spent $60.00 against a cap of $50.00")
        with self.assertRaises(BreakerTripped) as ctx:
            self.b.begin("ch02")
        self.assertIn("COST-CEILING", ctx.exception.reason)

    def test_the_first_reason_wins(self):
        self.b.trip("first reason")
        self.b.trip("second reason")
        self.assertEqual(self.b.tripped(), "first reason")

    def test_trip_returns_the_reason_in_force(self):
        self.assertEqual(self.b.trip("mine"), "mine")
        self.assertEqual(self.b.trip("later"), "mine", "trip must report what is actually in force")

    def test_a_chapter_already_running_can_still_record_its_failure(self):
        # The ceiling stops chapters STARTING; it must not stop one already in flight
        # from reporting how it ended, or that chapter's outcome is lost.
        ordinal = self.b.begin("ch01")
        self.b.trip("COST-CEILING: out of budget")
        self.b.record_failure("ch01", "some content failure", 90.0, ordinal)
        self.assertIn(
            "COST-CEILING",
            self.b.tripped(),
            "a later failure overwrote the ceiling diagnosis the operator needs to read",
        )

    def test_tripping_is_visible_to_every_thread(self):
        b = ChapterBreaker()
        refused: list[str] = []
        lock = threading.Lock()
        b.trip("COST-CEILING: out of budget")

        def worker(i: int) -> None:
            try:
                b.begin(f"ch{i:02d}")
            except BreakerTripped:
                with lock:
                    refused.append(f"ch{i:02d}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(refused), 20, "a tripped breaker must refuse every worker")
        self.assertEqual(b.attempted(), 0, "no refused start may consume an attempt")


class CostCeilingAdmissionTests(unittest.TestCase):
    """The driver must ASK before starting a chapter, not only mid-convergence.

    The live check inside the convergence loop reads actual spend and self-corrects, so
    the gap was never the accounting — it was that a NEW chapter could start after the
    ceiling was already gone. Serially that is the next loop iteration; concurrently it
    is every worker that has not begun.
    """

    def setUp(self) -> None:
        self.source = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        self.caps = (SCRIPTS_PODCAST / "_chapter_cost_caps.py").read_text(encoding="utf-8")

    def test_the_ceiling_is_checked_before_the_pre_start_gate(self):
        admit_at = self.source.index("ceiling.admit(book_dir)")
        begin_at = self.source.index("breaker.begin(slug)")
        self.assertLess(admit_at, begin_at, "the ceiling must be consulted BEFORE a chapter is admitted")

    def test_the_ceiling_breach_trips_the_shared_breaker(self):
        # A breach must trip the SAME breaker the systemic-failure path uses, so there is
        # one answer to "may a new chapter start". The trip now happens at the CALL SITE
        # from the returned refusal (see the returns-its-refusal test below), so this
        # asserts against the driver rather than the caps module.
        self.assertIn("breaker.trip(_refusal)", self.source)
        self.assertIn("COST-CEILING", self.caps)

    def test_the_admission_check_reads_live_spend_rather_than_estimating(self):
        # The whole reason this is admission rather than a reservation: no estimate of
        # what a chapter WILL cost. Counting an in-flight chapter at the per-chapter cap
        # is a different thing — that cap is a limit the loop already enforces, so it is
        # a bound, not a forecast.
        self.assertIn("_spend_fn", self.caps)
        for guessy in ("estimate", "projected_cost", "reserve("):
            self.assertNotIn(f"{guessy} =", self.caps, f"{guessy} suggests a reservation crept back in")

    def test_admission_returns_its_refusal_rather_than_only_tripping(self):
        """The refusal must reach the caller as a VALUE.

        It used to be communicated only by tripping the breaker, with the returned reason
        discarded — so the chapter was actually stopped by `breaker.begin()` re-reading
        the flag a few lines later. Enforcement by side effect at a distance is one
        reordering away from silently doing nothing.
        """
        ceiling = BookCeiling(10.0, 5.0, lambda _bd: 99.0)
        refusal = ceiling.admit(Path("/nonexistent"))
        self.assertIsInstance(refusal, str)
        self.assertIn("COST-CEILING", refusal)

    def test_a_halt_before_starting_is_recorded_rather_than_falling_through(self):
        # Without this the phase would exit the loop looking like a book whose chapters
        # were simply all done, and the supervisor would relaunch into the same wall.
        self.assertIn("_pre_start_halt", self.source)
        self.assertIn("per-chapter halted before starting further chapters", self.source)

    def test_the_mid_convergence_check_is_still_there(self):
        # Admission control does not replace it: it is what stops work ALREADY running.
        conv = (SCRIPTS_PODCAST / "_convergence.py").read_text(encoding="utf-8")
        self.assertIn("COST-CEILING", conv)
        self.assertIn("book_cost_fn", conv)


class BookCeilingAdmissionTests(unittest.TestCase):
    """`BookCeiling` — the admission decision itself, exercised rather than grepped."""

    def _ceiling(self, *, cap=50.0, per_chapter=5.0, spent=0.0) -> BookCeiling:
        return BookCeiling(cap, per_chapter, lambda _bd: spent)

    def test_a_disabled_ceiling_admits_everything(self):
        c = BookCeiling(0.0, 5.0, lambda _bd: 10_000.0)
        for _ in range(10):
            self.assertIsNone(c.admit(BOOK))

    def test_a_chapter_is_admitted_while_the_book_has_headroom(self):
        self.assertIsNone(self._ceiling(spent=10.0).admit(BOOK))

    def test_a_chapter_is_refused_once_spend_reaches_the_ceiling(self):
        refusal = self._ceiling(spent=50.0).admit(BOOK)
        self.assertIsNotNone(refusal)
        self.assertIn("COST-CEILING", refusal)

    def test_in_flight_chapters_are_counted_against_the_ceiling(self):
        """The overshoot fix, stated as one assertion.

        $46 spent against a $50 ceiling with a $5 per-chapter cap: ONE chapter fits,
        because a second could take the book to $56. Before 2026-08-09 every worker read
        the same $46, saw headroom, and started.
        """
        c = self._ceiling(cap=50.0, per_chapter=5.0, spent=46.0)
        self.assertIsNone(c.admit(BOOK), "the first chapter fits and must be admitted")
        self.assertIsNotNone(c.admit(BOOK), "a second in-flight chapter could breach the ceiling")

    def test_concurrent_admissions_cannot_overshoot_the_ceiling(self):
        """Twenty threads racing on the same ceiling admit only what the cap allows.

        The defect this pins was a genuine race: the read of live spend and the decision
        to start were not under one lock, so N workers each read the same figure and all
        admitted. Worst case measured at the time: 4 workers, $50 ceiling, $49 spent,
        book reached ~$69.
        """
        # $50 ceiling, $5 per chapter, nothing spent yet -> at most 10 may be in flight.
        c = self._ceiling(cap=50.0, per_chapter=5.0, spent=0.0)
        admitted: list[bool] = []
        lock = threading.Lock()
        barrier = threading.Barrier(20)

        def worker() -> None:
            barrier.wait()  # maximise the overlap on the decision
            ok = c.admit(BOOK) is None
            with lock:
                admitted.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(
            sum(admitted),
            10,
            f"expected exactly 10 admissions under a $50 ceiling at $5/chapter, got {sum(admitted)} "
            f"— concurrent admissions are overshooting the ceiling",
        )
        self.assertEqual(c.in_flight(), 10)

    def test_releasing_frees_the_slot(self):
        c = self._ceiling(cap=10.0, per_chapter=5.0, spent=0.0)
        self.assertIsNone(c.admit(BOOK))
        self.assertIsNone(c.admit(BOOK))
        self.assertIsNotNone(c.admit(BOOK), "two in flight already commits the whole ceiling")
        c.release()
        self.assertIsNone(c.admit(BOOK), "a finished chapter must free its slot")

    def test_release_never_goes_negative(self):
        c = self._ceiling()
        for _ in range(5):
            c.release()
        self.assertEqual(c.in_flight(), 0)

    def test_a_ceiling_without_a_per_chapter_cap_forces_serial_execution(self):
        """No bound on in-flight spend means concurrency cannot be made safe.

        Refusing to widen is the correct direction to be wrong: the alternative is
        overshooting a spend limit by an amount nothing in the system bounds.
        """
        c = BookCeiling(50.0, 0.0, lambda _bd: 0.0)
        self.assertEqual(c.concurrency_limit(4), 1)

    def test_a_book_with_both_caps_may_use_the_requested_workers(self):
        self.assertEqual(BookCeiling(50.0, 5.0, lambda _bd: 0.0).concurrency_limit(4), 4)

    def test_a_book_with_no_ceiling_may_use_the_requested_workers(self):
        self.assertEqual(BookCeiling(0.0, 0.0, lambda _bd: 0.0).concurrency_limit(4), 4)

    def test_a_nonsense_worker_count_is_floored_at_one(self):
        c = BookCeiling(0.0, 0.0, lambda _bd: 0.0)
        for value in (0, -4):
            self.assertEqual(c.concurrency_limit(value), 1)

    def test_an_admitted_chapter_is_always_released_however_it_ends(self):
        """The driver must pair every admission with a release.

        Releasing only on the success path leaks the in-flight count, and since that
        count is charged against the ceiling the book would refuse every chapter after
        the first failure — a spend limit that tightens itself as the run goes on.
        """
        source = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        self.assertIn("finally:", source)
        self.assertIn("ceiling.release()", source)
        release_at = source.index("ceiling.release()")
        finally_at = source.rindex("finally:", 0, release_at)
        between = source[finally_at:release_at]
        self.assertNotIn("def ", between, "the release must sit directly under a `finally:`")


class ConcurrencySafetyTests(unittest.TestCase):
    """The state must be correct under threads — the reason this class exists at all."""

    def test_ordinals_are_unique_under_concurrent_begins(self):
        b = ChapterBreaker()
        seen: list[int] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                o = b.begin(f"ch{i:02d}")
            except BreakerTripped:
                return
            with lock:
                seen.append(o)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(seen), 50)
        self.assertEqual(sorted(seen), list(range(1, 51)), "ordinals raced or duplicated")

    def test_exactly_one_ordinal_is_first(self):
        b = ChapterBreaker()
        firsts: list[str] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            o = b.begin(f"ch{i:02d}")
            if o == 1:
                with lock:
                    firsts.append(f"ch{i:02d}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(firsts), 1, "'the first chapter attempted' must be exactly one chapter")

    def test_concurrent_failures_of_one_signature_trip_once(self):
        b = ChapterBreaker()
        results: list[str | None] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                o = b.begin(f"ch{i:02d}")
            except BreakerTripped:
                return
            r = b.record_failure(f"ch{i:02d}", "word count 5 outside band", 60.0, o)
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertIsNotNone(b.tripped())
        # Every reported reason must be the SAME one — the first diagnosis, not a
        # different message per worker.
        reported = {r for r in results if r is not None}
        self.assertEqual(len(reported), 1, f"workers reported conflicting diagnoses: {reported}")

    def test_signature_groups_are_a_copy(self):
        b = ChapterBreaker()
        o = b.begin("ch01")
        b.record_failure("ch01", "boom boom", 60.0, o)
        groups = b.signature_groups()
        groups.clear()
        self.assertTrue(b.signature_groups(), "the caller mutated the breaker's own state")


class EquivalenceWithTheInlineVersionTests(unittest.TestCase):
    """The driver still exposes the signature helper, and the constants are unchanged.

    The extraction had to preserve behaviour exactly, because it landed while the loop
    was still serial — the point was to make parallelism POSSIBLE later, not to change
    any decision now.
    """

    def test_the_driver_re_exports_the_signature_helper(self):
        import phases.chapter_driver as cd

        self.assertIs(cd._failure_signature, failure_signature)

    def test_the_thresholds_match_the_original_inline_values(self):
        self.assertEqual(FAST_FAILURE_SEC, 5.0)
        self.assertEqual(SHARED_FAILURE_CHAPTERS, 2)

    def test_the_driver_no_longer_keeps_its_own_breaker_state(self):
        source = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        for gone in ("attempted += 1", "failure_signatures.setdefault"):
            self.assertNotIn(
                gone,
                source,
                f"{gone!r} is back in the driver — the breaker's state must have ONE home, "
                f"or workers will race the copy that is not locked",
            )

    def test_the_driver_asks_the_breaker_before_starting_a_chapter(self):
        source = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        self.assertIn("breaker.begin(", source, "the pre-start gate is not wired into the loop")
        self.assertIn("BreakerTripped", source, "the driver does not handle a refused start")


if __name__ == "__main__":
    unittest.main()
