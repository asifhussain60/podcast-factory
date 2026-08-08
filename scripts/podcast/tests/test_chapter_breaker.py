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
