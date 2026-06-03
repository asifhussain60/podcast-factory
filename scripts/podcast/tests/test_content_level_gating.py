#!/usr/bin/env python3
"""Tests for Wave L content-level gating — foundation (L-1) + gate clause (L-2).

Covers:
  - _rules.allowed_content_levels (cumulative-downward ladder logic)
  - _rules.CONTENT_LEVELS / CONTENT_LEVEL_LADDER constants
  - augmenter._book_content_level (meta.yml reader, default None)
  - augmenter._content_level_clause (SQL fragment builder, L-2)

Pure unit tests — no Gemini/LLM calls, no live DB writes.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))

import _rules  # noqa: E402
import augmenter  # noqa: E402


class TestAllowedContentLevels(unittest.TestCase):
    def test_cumulative_downward(self):
        self.assertEqual(
            _rules.allowed_content_levels("esoteric"),
            ["history", "shariah", "esoteric", "universal"],
        )
        self.assertEqual(
            _rules.allowed_content_levels("realities"),
            ["history", "shariah", "esoteric", "realities", "universal"],
        )
        self.assertEqual(
            _rules.allowed_content_levels("shariah"),
            ["history", "shariah", "universal"],
        )
        self.assertEqual(
            _rules.allowed_content_levels("history"),
            ["history", "universal"],
        )

    def test_esoteric_excludes_realities(self):
        """The core safety property: an esoteric book never sees realities atoms."""
        self.assertNotIn("realities", _rules.allowed_content_levels("esoteric"))

    def test_none_and_unknown_return_empty(self):
        """Empty list => caller applies NO gate (non-Islamic / unclassified path)."""
        self.assertEqual(_rules.allowed_content_levels(None), [])
        self.assertEqual(_rules.allowed_content_levels(""), [])
        self.assertEqual(_rules.allowed_content_levels("bogus"), [])

    def test_constants(self):
        self.assertEqual(
            _rules.CONTENT_LEVEL_LADDER,
            ("history", "shariah", "esoteric", "realities"),
        )
        self.assertIn("universal", _rules.CONTENT_LEVELS)
        for lvl in _rules.CONTENT_LEVEL_LADDER:
            self.assertIn(lvl, _rules.CONTENT_LEVELS)


class TestBookContentLevelReader(unittest.TestCase):
    def _book_dir(self, meta_text: str | None) -> Path:
        d = Path(tempfile.mkdtemp())
        if meta_text is not None:
            (d / "meta.yml").write_text(meta_text, encoding="utf-8")
        return d

    def test_missing_meta_returns_none(self):
        self.assertIsNone(augmenter._book_content_level(self._book_dir(None)))

    def test_absent_field_returns_none(self):
        d = self._book_dir("slug: x\ntradition_affinity: fatimid-ismaili\n")
        self.assertIsNone(augmenter._book_content_level(d))

    def test_valid_level(self):
        d = self._book_dir("content_level: esoteric\n")
        self.assertEqual(augmenter._book_content_level(d), "esoteric")

    def test_typo_normalized_to_none(self):
        """A typo must never silently over-restrict — falls back to no-gate."""
        d = self._book_dir("content_level: esoterics\n")  # note trailing 's'
        self.assertIsNone(augmenter._book_content_level(d))


class TestContentLevelClause(unittest.TestCase):
    """L-2: the SQL fragment + params builder. None level => no clause (empty)."""

    def test_no_level_yields_empty_clause(self):
        clause, params = augmenter._content_level_clause(None)
        self.assertEqual(clause, "")
        self.assertEqual(params, [])

    def test_esoteric_clause_includes_universal_and_null(self):
        clause, params = augmenter._content_level_clause("esoteric")
        self.assertIn("content_level", clause)
        self.assertIn("IS NULL", clause)
        # params carry exactly the allowed ladder levels (incl. universal)
        self.assertEqual(set(params), {"history", "shariah", "esoteric", "universal"})
        self.assertNotIn("realities", params)

    def test_realities_clause_includes_all(self):
        clause, params = augmenter._content_level_clause("realities")
        self.assertEqual(
            set(params), {"history", "shariah", "esoteric", "realities", "universal"}
        )


if __name__ == "__main__":
    unittest.main()
