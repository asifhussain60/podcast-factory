#!/usr/bin/env python3
"""Two loops must stay serial. This test is the tripwire.

Both look like obvious parallelisation targets — they are the two longest phases by
wall clock and their units look independent — and both would break in ways no other
gate in this repo can see. The investigation is recorded in the comments above each
loop; this pins the conclusion so a future well-meaning change fails loudly.

  THE BOOK COMPOSE LOOP (`_translation_edition.author_translation_edition_compose`)
    Each iteration consumes `previous_tail` and `prev_emitted_prose` from the one
    before — an eighty-word continuity tail handed to the next chapter's compose, and
    the previous chapter's prose that `_trim_seam_overlap` compares against to delete
    a passage the source narrates twice. Parallelised, every chapter gets an empty
    tail: the book still renders, every chapter is present, the counts are right, and
    every gate passes, because nothing inspects the join BETWEEN two chapters. Wrong
    to a reader, clean to the pipeline.

  THE PER-CHAPTER PODCAST LOOP (`phases/chapter_driver._drive_per_chapter_and_after`)
    Three blockers. `phase_git_commit` runs a repo-wide `git add`/`status`/`commit`
    per chapter, so concurrent chapters contend on `.git/index.lock` and commit each
    other's files under the wrong message. The C3 circuit breaker is an ECONOMIC
    early exit whose value is halting before the remaining chapters are paid for —
    concurrency puts them all in flight before the signal appears. And the per-book
    cost ceiling is checked at chapter boundaries, so concurrent chapters overshoot
    it. The last two are the decisive ones: weakening two cost controls to buy
    wall-clock time trades the problem this pass exists to fix for a lesser one.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

COMPOSE = SCRIPTS_PODCAST / "_translation_edition.py"
CHAPTER_DRIVER = SCRIPTS_PODCAST / "phases" / "chapter_driver.py"

#: Anything that would run the loop bodies concurrently.
CONCURRENCY_MARKERS = (
    "ThreadPoolExecutor",
    "ProcessPoolExecutor",
    "concurrent.futures",
    "multiprocessing",
    "asyncio.gather",
    "asyncio.TaskGroup",
)


class NoConcurrencyIntroducedTests(unittest.TestCase):
    def _assert_serial(self, path: Path, what: str) -> None:
        source = path.read_text(encoding="utf-8")
        found = [m for m in CONCURRENCY_MARKERS if m in source]
        self.assertEqual(
            found,
            [],
            f"{what} introduced concurrency ({', '.join(found)}). Read the comment "
            f"above the loop in {path.name} before removing this test — the failure "
            f"mode is invisible to every other gate here.",
        )

    def test_the_book_compose_module_runs_no_workers(self):
        self._assert_serial(COMPOSE, "the book compose module")

    def test_the_per_chapter_driver_runs_no_workers(self):
        self._assert_serial(CHAPTER_DRIVER, "the per-chapter driver")


class SerialDependencyStillExistsTests(unittest.TestCase):
    """The REASON must still hold. If the dependency is gone, revisit the decision.

    Guards against the opposite mistake: someone removes the continuity tail, the
    tests above keep passing, and the comments now describe a constraint that no
    longer exists — so the loop stays serial for a reason that has expired.
    """

    def test_compose_still_threads_a_continuity_tail_between_chapters(self):
        source = COMPOSE.read_text(encoding="utf-8")
        for name in ("previous_tail", "prev_emitted_prose"):
            self.assertIn(
                name,
                source,
                f"{name} is gone from the compose loop. If the chapter-to-chapter "
                f"dependency has really been removed, the serial constraint may no "
                f"longer be needed — re-open the decision rather than deleting this test.",
            )

    def test_the_per_chapter_loop_still_commits_per_chapter(self):
        source = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertIn(
            "phase_git_commit",
            source,
            "the per-chapter git commit is gone — one of the three blockers to "
            "parallelising this loop may have been removed; re-read the comment.",
        )

    def test_the_per_chapter_loop_still_has_its_circuit_breaker(self):
        source = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertIn("CIRCUIT-BREAKER", source)
        self.assertIn("failure_signatures", source)


class DecisionIsDocumentedTests(unittest.TestCase):
    """A tripwire with no explanation gets deleted by whoever trips it."""

    def test_both_loops_carry_their_reasoning_in_the_source(self):
        for path, marker in ((COMPOSE, "SERIAL BY NECESSITY"), (CHAPTER_DRIVER, "MUST STAY SERIAL")):
            self.assertIn(
                marker,
                path.read_text(encoding="utf-8"),
                f"{path.name} lost the comment explaining why its loop is serial",
            )


class BothModulesStillParseTests(unittest.TestCase):
    """Cheap guard: the comments above were inserted into live files."""

    def test_modules_parse(self):
        for path in (COMPOSE, CHAPTER_DRIVER):
            ast.parse(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
