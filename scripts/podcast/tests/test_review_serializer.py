#!/usr/bin/env python3
"""Tests for scripts/podcast/_review_serializer.py (P25.1 deliverable).

Covers:
  - Round-trip: struct → markdown → struct preserves all fields
  - Empty sections produce empty lists (tolerant parse)
  - Approval mark recognized in both checked/unchecked forms
  - Content range omitted when neither bound set
  - AI suggestions persisted via HTML comments
  - summary_one_line builds expected string
  - atomic_write performs tmp + rename
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _review_serializer as srz  # noqa: E402


def _populated_struct() -> srz.ReviewStruct:
    rs = srz.ReviewStruct(book_slug="tahdhib-al-akhlaq")
    rs.translation_issues = [
        srz.FlagRow(page=47, quote="structured the daʿwa hierarchy in the Fatimid period",
                    note="should be 'preacher-positions' not 'preacher positions' — hyphenation matters",
                    recurring_pattern=False),
        srz.FlagRow(page=23, quote="the angles fell at the wrong moment",
                    note="OCR scrambled 'angels' → 'angles' — fix",
                    recurring_pattern=True),
    ]
    rs.missing_passages = []
    rs.glossary = [srz.GlossaryRow(term="ibdāʿ", definition="origination (vs khalq = creation) — Ismāʿīlī Neoplatonic term")]
    rs.pronunciation = []
    rs.free_form_comments = "Note: voice shifts noticeably on page 48 — second author?"
    rs.content_range = srz.ContentRange(body_starts_at_page=14, body_ends_at_page=178)
    rs.approved = True
    rs.ai_suggestions = [
        srz.AISuggestion(
            id="sf-001",
            page=48,
            quote="Three implications follow",
            reason="voice-shift to enumerated argument style",
            feature="voice-shift",
            status="pending",
        )
    ]
    return rs


class RoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_everything(self):
        rs = _populated_struct()
        md = srz.serialize_to_markdown(rs)
        rs2 = srz.parse_from_markdown(md, book_slug="tahdhib-al-akhlaq")
        self.assertEqual(len(rs.translation_issues), len(rs2.translation_issues))
        for a, b in zip(rs.translation_issues, rs2.translation_issues):
            self.assertEqual(a.page, b.page)
            self.assertEqual(a.quote, b.quote)
            self.assertIn(a.note.split("—")[0].strip(), b.note)  # normalize whitespace
            self.assertEqual(a.recurring_pattern, b.recurring_pattern)
        self.assertEqual(rs.glossary[0].term, rs2.glossary[0].term)
        self.assertEqual(rs.glossary[0].definition, rs2.glossary[0].definition)
        self.assertEqual(rs.free_form_comments, rs2.free_form_comments)
        self.assertEqual(rs.content_range.body_starts_at_page, rs2.content_range.body_starts_at_page)
        self.assertEqual(rs.content_range.body_ends_at_page, rs2.content_range.body_ends_at_page)
        self.assertTrue(rs2.approved)
        self.assertEqual(len(rs.ai_suggestions), len(rs2.ai_suggestions))
        self.assertEqual(rs.ai_suggestions[0].id, rs2.ai_suggestions[0].id)


class EmptyStructTests(unittest.TestCase):
    def test_empty_struct_serializes(self):
        rs = srz.ReviewStruct(book_slug="empty-book")
        md = srz.serialize_to_markdown(rs)
        # All section headers present even when empty
        self.assertIn("## §1 Translation issues", md)
        self.assertIn("## §2 Missing or scrambled passages", md)
        self.assertIn("## §3 Glossary additions", md)
        self.assertIn("## §4 Pronunciation corrections", md)
        self.assertIn("## §5 Free-form comments", md)
        self.assertIn("## §7 Content range", md)
        self.assertIn("## §8 Approval", md)
        self.assertIn(srz.APPROVE_MARKER_UNCHECKED, md)

    def test_empty_struct_parses_cleanly(self):
        md = "# Operator review — x\n\n## §1 Translation issues\n_(none)_\n\n## §8 Approval\n\n[ ] I approve this transcript\n"
        rs = srz.parse_from_markdown(md, book_slug="x")
        self.assertEqual(len(rs.translation_issues), 0)
        self.assertFalse(rs.approved)


class ApprovalTests(unittest.TestCase):
    def test_approval_checked_recognized(self):
        md = f"## §8 Approval\n\n{srz.APPROVE_MARKER_CHECKED}\n"
        rs = srz.parse_from_markdown(md)
        self.assertTrue(rs.approved)

    def test_approval_unchecked_recognized(self):
        md = f"## §8 Approval\n\n{srz.APPROVE_MARKER_UNCHECKED}\n"
        rs = srz.parse_from_markdown(md)
        self.assertFalse(rs.approved)


class ContentRangeTests(unittest.TestCase):
    def test_range_both_set(self):
        md = "## §7 Content range\n\n- body_starts_at_page: 14\n- body_ends_at_page: 178\n"
        rs = srz.parse_from_markdown(md)
        self.assertEqual(rs.content_range.body_starts_at_page, 14)
        self.assertEqual(rs.content_range.body_ends_at_page, 178)

    def test_range_only_start(self):
        md = "## §7 Content range\n\n- body_starts_at_page: 5\n"
        rs = srz.parse_from_markdown(md)
        self.assertEqual(rs.content_range.body_starts_at_page, 5)
        self.assertIsNone(rs.content_range.body_ends_at_page)


class AISuggestionsTests(unittest.TestCase):
    def test_ai_suggestions_persist_in_html_comments(self):
        rs = srz.ReviewStruct(book_slug="x")
        rs.ai_suggestions.append(srz.AISuggestion(
            id="abc", page=10, quote="q", reason="r", feature="suggest-flags",
        ))
        md = srz.serialize_to_markdown(rs)
        self.assertIn(srz.AI_BLOCK_START, md)
        self.assertIn(srz.AI_BLOCK_END, md)
        # Parse back
        rs2 = srz.parse_from_markdown(md, book_slug="x")
        self.assertEqual(len(rs2.ai_suggestions), 1)
        self.assertEqual(rs2.ai_suggestions[0].id, "abc")

    def test_ai_block_skipped_when_empty(self):
        rs = srz.ReviewStruct(book_slug="x")
        md = srz.serialize_to_markdown(rs)
        self.assertNotIn(srz.AI_BLOCK_START, md)


class SummaryTests(unittest.TestCase):
    def test_summary_one_line(self):
        rs = _populated_struct()
        summary = srz.summary_one_line(rs)
        self.assertIn("2 flags", summary)
        self.assertIn("1 glossary", summary)
        self.assertIn("range 14–178", summary)

    def test_summary_empty(self):
        rs = srz.ReviewStruct(book_slug="x")
        self.assertEqual(srz.summary_one_line(rs), "no changes")


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_creates_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "subdir" / "out.md"
            srz.atomic_write(p, "hello\n")
            self.assertTrue(p.exists())
            self.assertEqual(p.read_text(), "hello\n")
            # No leftover tmp
            self.assertFalse((p.with_suffix(p.suffix + ".tmp")).exists())

    def test_atomic_write_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.md"
            srz.atomic_write(p, "first\n")
            srz.atomic_write(p, "second\n")
            self.assertEqual(p.read_text(), "second\n")


class FromDictTests(unittest.TestCase):
    def test_from_dict_full(self):
        rs = _populated_struct()
        d = rs.to_dict()
        rs2 = srz.ReviewStruct.from_dict(d)
        self.assertEqual(len(rs2.translation_issues), 2)
        self.assertEqual(rs2.translation_issues[0].page, 47)
        self.assertEqual(rs2.content_range.body_starts_at_page, 14)

    def test_from_dict_minimal(self):
        rs = srz.ReviewStruct.from_dict({"book_slug": "x"})
        self.assertEqual(rs.book_slug, "x")
        self.assertEqual(rs.translation_issues, [])
        self.assertFalse(rs.approved)


if __name__ == "__main__":
    unittest.main()
