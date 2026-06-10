#!/usr/bin/env python3
"""Tests for the Phase 0d deterministic topic floor (chapter-density standard).

Pins the 2026-06-10 fix for the merge loophole: the TOC planner under-counted
59 source concepts on the-master-and-the-disciple and re-planned 5 marathon
episodes; the author then disguised the cramming by rolling ~4 teachings under
each H2. The floor is arithmetic on the plan's `topics` enumeration plus the
measured concept inventory from `chapters/_curator-archive/`.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _authoring._chapter_design import (  # noqa: E402
    _concept_inventory,
    _topic_floor_violations,
)


def _sc(idx, ep_count, topics=None, title="Part"):
    sc = {"sc_index": idx, "source_title": f"{title} {idx}",
          "episode_count": ep_count}
    if topics is not None:
        sc["topics"] = topics
    return sc


class TopicFloorTest(unittest.TestCase):
    def test_under_split_chapter_violates(self):
        plan = [_sc(1, 1, topics=[f"t{i}" for i in range(9)])]
        v = _topic_floor_violations(plan, None, max_concepts=3,
                                    enforce=True, consolidate=False)
        self.assertEqual(len(v), 1)
        self.assertIn("requires episode_count >= 3", v[0])

    def test_correctly_split_chapter_passes(self):
        plan = [_sc(1, 3, topics=[f"t{i}" for i in range(9)])]
        v = _topic_floor_violations(plan, None, max_concepts=3,
                                    enforce=True, consolidate=False)
        self.assertEqual(v, [])

    def test_missing_topics_violates_when_enforced(self):
        plan = [_sc(1, 1)]
        v = _topic_floor_violations(plan, None, max_concepts=3,
                                    enforce=True, consolidate=False)
        self.assertEqual(len(v), 1)
        self.assertIn("missing the `topics` enumeration", v[0])

    def test_missing_topics_tolerated_when_not_enforced(self):
        plan = [_sc(1, 1)]
        v = _topic_floor_violations(plan, None, max_concepts=3,
                                    enforce=False, consolidate=False)
        self.assertEqual(v, [])

    def test_missing_topics_tolerated_in_consolidation_mode(self):
        plan = [_sc(1, 1)]
        v = _topic_floor_violations(plan, None, max_concepts=3,
                                    enforce=True, consolidate=True)
        self.assertEqual(v, [])

    def test_global_inventory_floor_catches_marathon_plan(self):
        # The exact master-and-the-disciple failure: 5 source chapters, one
        # episode each, while the measured inventory carries 59 concepts.
        inventory = [
            {"file": f"ch0{i}.txt", "topics": [f"c{i}-{j}" for j in range(n)]}
            for i, n in enumerate((9, 12, 12, 14, 12), start=1)
        ]
        plan = [_sc(i, 1, topics=[f"t{i}a", f"t{i}b", f"t{i}c"])
                for i in range(1, 6)]
        v = _topic_floor_violations(plan, inventory, max_concepts=3,
                                    enforce=True, consolidate=False)
        self.assertTrue(any("requires >= 20 episodes total" in x for x in v))

    def test_global_inventory_floor_holds_in_consolidation_mode(self):
        inventory = [{"file": "ch01.txt", "topics": [f"c{j}" for j in range(12)]}]
        plan = [_sc(1, 1)]
        v = _topic_floor_violations(plan, inventory, max_concepts=3,
                                    enforce=True, consolidate=True)
        self.assertTrue(any("episodes total" in x for x in v))

    def test_inventory_satisfied_plan_passes(self):
        inventory = [{"file": "ch01.txt", "topics": [f"c{j}" for j in range(6)]}]
        plan = [_sc(1, 2, topics=[f"t{j}" for j in range(6)])]
        v = _topic_floor_violations(plan, inventory, max_concepts=3,
                                    enforce=True, consolidate=False)
        self.assertEqual(v, [])


class ConceptInventoryTest(unittest.TestCase):
    def test_reads_archive_and_excludes_frames(self):
        with tempfile.TemporaryDirectory() as td:
            book = Path(td) / "fixture-book"
            archive = book / "chapters" / "_curator-archive"
            archive.mkdir(parents=True)
            (archive / "ch01-old.txt").write_text(
                "# Title\n\n## Where this episode opens\nframe\n\n"
                "## First teaching\nbody\n\n## Second teaching\nbody\n",
                encoding="utf-8")
            inv = _concept_inventory(book)
            self.assertEqual(len(inv), 1)
            self.assertEqual(inv[0]["topics"],
                             ["First teaching", "Second teaching"])

    def test_no_archive_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(_concept_inventory(Path(td) / "nope"))


if __name__ == "__main__":
    unittest.main()
