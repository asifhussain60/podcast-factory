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

    def test_the_per_chapter_commits_are_batched_not_per_chapter(self):
        # Blocker 1 was CLEARED on 2026-08-08: the commits moved to one batched commit
        # after the loop. What must hold now is the opposite of what this test first
        # asserted — no `phase_git_commit` inside the loop body, or the index.lock
        # contention comes straight back the moment anyone adds workers.
        source = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertIn("_commit_chapter_batch", source, "the batched commit helper is gone")

        body = self._per_chapter_loop_body(source)
        self.assertNotIn(
            "phase_git_commit(",
            body,
            "a git commit was reintroduced INSIDE the per-chapter loop — two workers "
            "would contend on .git/index.lock and commit each other's staged files "
            "under the wrong message. Use the batched commit after the loop.",
        )

    @staticmethod
    def _per_chapter_loop_body(source: str) -> str:
        """The source of the `for slug in chapter_slugs:` loop, located by AST.

        Parsed rather than sliced between text markers. The first version of this keyed
        on the line that follows the loop, and broke the moment a block was inserted
        there — a brittle helper turns a real guard into noise, and the guard is the
        point.
        """
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.For)
                and isinstance(node.target, ast.Name)
                and node.target.id == "slug"
                and isinstance(node.iter, ast.Name)
                and node.iter.id == "chapter_slugs"
            ):
                return "".join(lines[node.lineno - 1 : node.end_lineno])
        raise AssertionError("could not find the `for slug in chapter_slugs:` loop")

    def test_the_batch_commits_on_every_halt_path_too(self):
        # A book where 18 of 20 chapters shipped before a halt must still commit those
        # 18 — finished work must not be lost because a later chapter broke.
        source = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertGreaterEqual(
            source.count("_commit_chapter_batch()"),
            4,  # definition + systemic halt + circuit breaker + after the loop
            "the batched commit is not called on every exit path from the loop",
        )

    def test_the_per_chapter_loop_still_has_its_circuit_breaker(self):
        # The breaker's STATE moved to `_chapter_breaker` on 2026-08-08 so it can be
        # shared safely once this loop gains workers, which is why this no longer looks
        # for the old `failure_signatures` local. What must still hold is that the loop
        # consults a breaker at all — both after a failure AND before a chapter starts,
        # since the pre-start gate is the half that makes the economics survive workers.
        source = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertIn("CIRCUIT-BREAKER", source)
        self.assertIn("breaker.record_failure(", source, "the loop no longer records failures with the breaker")
        self.assertIn("breaker.begin(", source, "the loop no longer asks the breaker BEFORE starting a chapter")


class DecisionIsDocumentedTests(unittest.TestCase):
    """A tripwire with no explanation gets deleted by whoever trips it."""

    def test_both_loops_carry_their_reasoning_in_the_source(self):
        # Matched on a short stable token rather than a whole sentence: the chapter
        # driver's comment was condensed on 2026-08-08 to fit the DR-005 ceiling and a
        # longer marker failed on the rewording alone, which is noise rather than a
        # finding. What must not vanish is the word SERIAL next to a reason.
        for path in (COMPOSE, CHAPTER_DRIVER):
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "SERIAL",
                text,
                f"{path.name} lost the comment explaining why its loop is serial",
            )

    def test_the_chapter_driver_says_it_is_now_safe_to_parallelise(self):
        # All three blockers were cleared on 2026-08-08, so this test's premise changed:
        # it used to demand the comment NAME what was still in the way. Now the comment's
        # job is to say the loop is ready and point at the three mechanisms that made it
        # ready, so the next person adding workers knows what they are relying on.
        text = CHAPTER_DRIVER.read_text(encoding="utf-8")
        self.assertIn("SAFE TO PARALLELISE", text, "the comment no longer records that the blockers are cleared")
        for mechanism in ("_commit_chapter_batch", "_chapter_breaker", "_chapter_cost_caps"):
            self.assertIn(
                mechanism,
                text,
                f"the comment no longer points at {mechanism}, which a future parallelisation depends on",
            )


class BothModulesStillParseTests(unittest.TestCase):
    """Cheap guard: the comments above were inserted into live files."""

    def test_modules_parse(self):
        for path in (COMPOSE, CHAPTER_DRIVER):
            ast.parse(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
