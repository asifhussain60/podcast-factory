#!/usr/bin/env python3
"""A cached window is reused only when it was written against the SAME source.

Two opposite defects meet here, and the fix has to avoid both.

  UNDER-invalidation (what 0b actually did): the resume check was a bare
  `out_path.exists()` with nothing compared against the input, so a window refined
  from one source was silently reused after the source changed and every later phase
  worked from prose answering a different text.

  OVER-invalidation (what an mtime rule would do): `_translation_cache` compares
  mtimes against a set of governing files. That is correct about staleness and
  expensive about everything else — a `git checkout`, a `git pull` or a whitespace
  edit to a shared module rewrites an mtime and discards work that is still valid.
  Re-refining a 28-window book costs about $8 of metered API, measured on
  `spiritual-ethos` on 2026-08-05, where 81% of the book's entire real spend was
  four repeats of a pass it already had.

So the comparison is a CONTENT fingerprint, and a pre-existing cache is adopted
rather than discarded — otherwise the check would charge for its own introduction
across every book in the repo.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _chunking import cache_fingerprint, run_windowed
from _step_ledger import last_by_step, read_steps

# `iter_windows` is PARAGRAPH-aligned (it splits on blank lines), so a fixture
# without blank lines yields a single window no matter how long it is — which would
# make every reuse assertion below trivially true.
SOURCE = "\n\n".join(" ".join(f"word{i}-{j}" for j in range(200)) for i in range(20))
CHANGED = SOURCE + "\n\nAnd one more paragraph entirely."


class FingerprintTests(unittest.TestCase):
    def test_same_input_same_fingerprint(self):
        a = cache_fingerprint(SOURCE, target_words=3000, overlap_words=120)
        b = cache_fingerprint(SOURCE, target_words=3000, overlap_words=120)
        self.assertEqual(a, b)

    def test_changed_content_changes_the_fingerprint(self):
        a = cache_fingerprint(SOURCE, target_words=3000, overlap_words=120)
        b = cache_fingerprint(CHANGED, target_words=3000, overlap_words=120)
        self.assertNotEqual(a, b)

    def test_window_parameters_are_part_of_the_identity(self):
        # Different boundaries mean `win-003` is not the same window, so reusing it
        # across segmentations would splice unrelated prose.
        a = cache_fingerprint(SOURCE, target_words=3000, overlap_words=120)
        b = cache_fingerprint(SOURCE, target_words=1500, overlap_words=120)
        c = cache_fingerprint(SOURCE, target_words=3000, overlap_words=200)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)


class _RunFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)
        self.chunks = self.book / "_system" / "source" / "text" / "_chunks" / "0b"
        self.calls: list[int] = []

    def tearDown(self) -> None:
        self._td.cleanup()

    def _invoke(self, prompt: str, body: str, timeout: int) -> str:
        # Stands in for the SDK. Counting calls IS the money measurement.
        self.calls.append(1)
        return f"refined: {body[:40]}"

    def _run(self, text: str, *, target_words: int = 1000) -> list[Path]:
        return run_windowed(
            text=text,
            chunks_dir=self.chunks,
            prompt_builder=lambda body, idx, total, out: f"do window {idx}",
            target_words=target_words,
            overlap_words=50,
            timeout_per_window=5,
            log=lambda m: None,
            book_dir=self.book,
            phase="0b",
            # A REAL model name: an unknown one makes the cost ledger print a
            # pricing warning to stderr on every run of this test, which is noise
            # in a suite people read.
            model="claude-sonnet-4-6",
            max_workers=1,
            _invoke_fn=self._invoke,
        )


class ReuseTests(_RunFixture):
    def test_first_run_computes_every_window(self):
        self._run(SOURCE)
        self.assertGreater(len(self.calls), 1, "expected several windows")
        self.assertTrue((self.chunks / ".source-fingerprint").exists())

    def test_second_run_on_the_same_source_spends_nothing(self):
        self._run(SOURCE)
        first = len(self.calls)
        self.calls.clear()
        self._run(SOURCE)
        self.assertEqual(
            self.calls,
            [],
            f"an unchanged source re-paid for windows it already had ({first} the first time)",
        )

    def test_a_changed_source_recomputes_every_window(self):
        self._run(SOURCE)
        n = len(self.calls)
        self.calls.clear()
        self._run(CHANGED)
        self.assertGreaterEqual(
            len(self.calls),
            n,
            "a changed source reused cached windows — later phases would work from prose that answers a different text",
        )

    def test_changing_the_window_size_recomputes(self):
        self._run(SOURCE, target_words=1000)
        self.calls.clear()
        self._run(SOURCE, target_words=500)
        self.assertTrue(self.calls, "a different segmentation must not reuse the old windows")

    def test_a_pre_existing_cache_is_adopted_not_re_paid(self):
        # The grandfathering case: every book in the repo has a cache with no
        # fingerprint. Treating unknown as stale would re-spend on all of them the
        # first time this code runs.
        self._run(SOURCE)
        (self.chunks / ".source-fingerprint").unlink()
        self.calls.clear()
        self._run(SOURCE)
        self.assertEqual(
            self.calls,
            [],
            "a cache that predates the fingerprint was discarded — the check charged for its own introduction",
        )
        self.assertTrue((self.chunks / ".source-fingerprint").exists(), "the fingerprint should now be recorded")

    def test_adoption_happens_only_once(self):
        self._run(SOURCE)
        (self.chunks / ".source-fingerprint").unlink()
        self._run(SOURCE)  # adopts
        self.calls.clear()
        self._run(CHANGED)  # now protected: a real change must invalidate
        self.assertTrue(self.calls, "after adoption the fingerprint must protect against a real change")


class LedgerTests(_RunFixture):
    def test_a_cache_hit_records_noop_and_a_computed_window_records_ok(self):
        self._run(SOURCE)
        first = last_by_step(read_steps(self.book, phase="0b"))
        computed = [k for k, v in first.items() if k.startswith("win-") and v["outcome"] == "ok"]
        self.assertTrue(computed, "the first run should record computed windows")

        self._run(SOURCE)
        second = last_by_step(read_steps(self.book, phase="0b"))
        cached = [k for k, v in second.items() if k.startswith("win-") and v["outcome"] == "noop"]
        self.assertTrue(cached, "the second run should record cache hits")

    def test_an_absent_cache_is_recorded(self):
        # The condition that cost $8.38 five times: no cached windows present.
        self._run(SOURCE)
        rec = last_by_step(read_steps(self.book, phase="0b")).get("window-cache")
        self.assertIsNotNone(rec)
        self.assertIn("no cached windows", rec["evidence"]["why"])

    def test_an_invalidation_is_recorded_with_its_reason(self):
        self._run(SOURCE)
        self._run(CHANGED)
        rec = last_by_step(read_steps(self.book, phase="0b")).get("window-cache")
        self.assertIn("source changed", rec["evidence"]["why"])

    def test_the_review_gate_sees_the_reuse_shape(self):
        import _phase_review as pr

        self._run(SOURCE)
        self._run(SOURCE)
        ok, note = pr.gate_windows_not_repaid(self.book)
        self.assertTrue(ok)
        self.assertIn("cache", note)


if __name__ == "__main__":
    unittest.main()
