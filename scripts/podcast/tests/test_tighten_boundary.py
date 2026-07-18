#!/usr/bin/env python3
"""Tests for _tighten_helpers.boundary_check.

The check must accept book dirs under any content bucket (the post-2026-06-04
type-first layout) and the legacy drafts/published trees, and refuse anything
outside content/.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _tighten_helpers
from _rules import BUCKETS

REPO_ROOT = _tighten_helpers.REPO_ROOT


class BoundaryCheckTests(unittest.TestCase):
    def test_every_bucket_accepted(self):
        for bucket in BUCKETS:
            with self.subTest(bucket=bucket):
                _tighten_helpers.boundary_check(REPO_ROOT / "content" / bucket / "some-book")

    def test_nested_series_volume_accepted(self):
        _tighten_helpers.boundary_check(REPO_ROOT / "content" / "Islamic" / "asaas-al-taveel" / "vol-01")

    def test_legacy_drafts_accepted(self):
        _tighten_helpers.boundary_check(REPO_ROOT / "content" / "drafts" / "some-book")

    def test_legacy_published_accepted(self):
        _tighten_helpers.boundary_check(REPO_ROOT / "content" / "published" / "books" / "some-book")

    def test_outside_content_refused(self):
        with self.assertRaises(SystemExit):
            _tighten_helpers.boundary_check(REPO_ROOT / "scripts" / "podcast")

    def test_content_root_itself_refused(self):
        with self.assertRaises(SystemExit):
            _tighten_helpers.boundary_check(REPO_ROOT / "content")


if __name__ == "__main__":
    unittest.main()
