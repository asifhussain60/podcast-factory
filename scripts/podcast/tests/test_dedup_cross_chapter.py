#!/usr/bin/env python3
"""Tests for dedup_cross_chapter.py — retroactive cross-chapter de-dup planner.

Guards the two safety properties that matter most:
  * a repeat WOVEN into a larger unique paragraph is flagged for an authoring
    rewrite, never blunt-cut (a cut would leave dangling lead-ins/restatements);
  * a STANDALONE duplicated paragraph is safely auto-collapsed to a callback;
  * a shared bibliographic CITATION never registers as repeated teaching.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import dedup_cross_chapter as dd

DOCTRINE = (
    "The Imam's substance dissolves at each succession and the ranks return that "
    "substance so the line itself is structurally never broken across the generations"
)


def _book(tmp: Path, chapters: dict[str, str]) -> Path:
    book = tmp / "Islamic" / "fixture"
    (book / "chapters").mkdir(parents=True)
    for i, (slug, body) in enumerate(chapters.items(), 1):
        (book / "chapters" / f"ch{i:02d}-{slug}.txt").write_text(f"# {slug.title()}\n\n{body}\n", encoding="utf-8")
    return book


class DedupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_standalone_repeat_is_auto_collapsible(self):
        book = _book(
            self.tmp,
            {
                "home": f"## Concept A\n\n{DOCTRINE}.",
                "later": f"## Concept B\n\n{DOCTRINE}.",
            },
        )
        collapses = dd.plan(book)
        self.assertEqual(len(collapses), 1)
        c = collapses[0]
        self.assertEqual(c.home_slug, "home")
        self.assertFalse(c.embedded, "a paragraph that IS the repeat must be auto-collapsible")

    def test_embedded_repeat_is_flagged_not_cut(self):
        unique_pre = (
            "The lecture opened on the believer's own place and the discipline of "
            "being from a place, returning always to one ground and no other ground. "
        )
        unique_post = (
            " The teacher then turned to geography and the soil of one's own life, "
            "a teaching distinct to this movement and found in no earlier chapter here."
        )
        book = _book(
            self.tmp,
            {
                "home": f"## Concept A\n\n{DOCTRINE}.",
                "later": f"## Concept B\n\n{unique_pre}{DOCTRINE}.{unique_post}",
            },
        )
        collapses = dd.plan(book)
        self.assertEqual(len(collapses), 1)
        self.assertTrue(collapses[0].embedded, "a repeat woven into unique prose must be flagged for rewrite")
        # apply must refuse to touch it
        counts = dd.apply_collapses(book, collapses)
        self.assertEqual(counts, {}, "embedded repeats must never be auto-edited")

    def test_shared_citation_is_not_a_repeat(self):
        cite = "(Farhad Daftary, The Ismailis: Their History and Doctrines, Cambridge University Press, 2007, p. 4)"
        book = _book(
            self.tmp,
            {
                "home": f"## A\n\nThe line preserves itself across the eras {cite}.",
                "later": f"## B\n\nA wholly unrelated teaching about the soul and its ascent {cite}.",
            },
        )
        self.assertEqual(dd.plan(book), [], "a shared citation must not register as a repeat")


if __name__ == "__main__":
    unittest.main()
