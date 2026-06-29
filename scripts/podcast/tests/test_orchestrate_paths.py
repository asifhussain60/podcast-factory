#!/usr/bin/env python3
"""Tests for orchestrate_book.py path resolution.

The 2026-05-24 commit fixed an infinite-recursion bug in `_resolve_book_path`
that crashed on every non-'books' category in ALLOWED_CATEGORIES. This test
pins the fix so re-introducing the recursion regresses immediately.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import orchestrate_book as ob   # noqa: E402
from _rules import ALLOWED_CATEGORIES, BUCKETS   # noqa: E402


class ResolveBookPathTests(unittest.TestCase):

    def test_books_resolves_to_islamic_bucket(self):
        # 2026-06-04 type-first layout: content/<Bucket>/<slug>. A 'books'
        # category maps to the Islamic bucket (no drafts/ or category folder).
        p = ob._resolve_book_path("books", "the-master-and-the-disciple")
        self.assertEqual(p.name, "the-master-and-the-disciple")
        self.assertEqual(p.parent.name, "Islamic")
        self.assertEqual(p.parent.parent.name, "content")

    def test_sites_resolves_to_guides_bucket(self):
        p = ob._resolve_book_path("sites", "healthequity")
        self.assertEqual(p.name, "healthequity")
        self.assertEqual(p.parent.name, "Guides")

    def test_every_allowed_category_resolves_to_a_known_bucket(self):
        """The bug was infinite recursion on any non-'books' category.
        This iterates the full ALLOWED_CATEGORIES tuple to catch any future
        category added without updating the resolver."""
        for cat in ALLOWED_CATEGORIES:
            p = ob._resolve_book_path(cat, "test-slug")
            self.assertEqual(p.name, "test-slug")
            self.assertIn(p.parent.name, BUCKETS)
            # Must NOT recurse — if it did, this loop would never get here.


if __name__ == "__main__":
    unittest.main()
