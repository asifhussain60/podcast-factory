#!/usr/bin/env python3
"""The optional vowelling pass must never wedge the book behind it.

Degrees of Excellence sat at phase 0a for 43 minutes on 2026-07-31 at 0% CPU with
eight ESTABLISHED sockets to the model and nothing written. `vowel_arabic_source`
was wrapped in `except Exception`, which catches a failure but not a hang — the
call simply never returned, so the driver never advanced and never logged. These
tests pin the deadline that bounds it.
"""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from phases import scaffold


class VowelDeadlineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._real_deadline = scaffold.VOWEL_SOURCE_DEADLINE_S
        self._logged: list[str] = []
        self._real_info = scaffold._info
        scaffold._info = self._logged.append

    def tearDown(self) -> None:
        scaffold.VOWEL_SOURCE_DEADLINE_S = self._real_deadline
        scaffold._info = self._real_info
        sys.modules.pop("vowel_source", None)

    def _install_vowel_source(self, fn) -> None:
        import types

        mod = types.ModuleType("vowel_source")
        mod.vowel_source = fn
        sys.modules["vowel_source"] = mod

    def test_a_hang_returns_instead_of_blocking_forever(self) -> None:
        released = threading.Event()
        self._install_vowel_source(lambda *a, **k: released.wait(30))
        scaffold.VOWEL_SOURCE_DEADLINE_S = 0.2

        started = time.monotonic()
        try:
            scaffold.vowel_arabic_source(Path("/nonexistent"))
            elapsed = time.monotonic() - started
        finally:
            released.set()

        self.assertLess(elapsed, 5, "a wedged vowelling pass still blocked the driver")
        self.assertTrue(
            any("did not finish" in m for m in self._logged),
            f"the timeout was not reported to the log: {self._logged}",
        )

    def test_an_exception_is_still_caught_and_reported(self) -> None:
        def boom(*a, **k):
            raise RuntimeError("model refused")

        self._install_vowel_source(boom)
        scaffold.vowel_arabic_source(Path("/nonexistent"))
        self.assertTrue(
            any("model refused" in m for m in self._logged),
            f"the exception path regressed: {self._logged}",
        )

    def test_the_happy_path_stays_silent(self) -> None:
        self._install_vowel_source(lambda *a, **k: {"vowelled": 3})
        scaffold.vowel_arabic_source(Path("/nonexistent"))
        self.assertEqual(self._logged, [], "a clean pass should add no noise")

    def test_the_shipped_deadline_is_bounded_and_generous(self) -> None:
        self.assertGreaterEqual(self._real_deadline, 5 * 60)
        self.assertLessEqual(self._real_deadline, 60 * 60)


if __name__ == "__main__":
    unittest.main()
