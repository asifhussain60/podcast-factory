#!/usr/bin/env python3
"""Tests for scripts/podcast/_proposal_writer.py (P1.2 deliverable)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _proposal_writer as pw  # noqa: E402


class RenderTests(unittest.TestCase):
    def test_minimal_bundle_renders_with_frontmatter(self):
        b = pw.ProposalBundle(book_slug="ayyuhal-walad", episode_id="EP02-hatim")
        out = pw.render_proposal(b, generated_at="2026-05-19T12:00:00Z")
        self.assertIn("schema_version: 1", out)
        self.assertIn("book_slug: ayyuhal-walad", out)
        self.assertIn("episode_id: EP02-hatim", out)
        self.assertIn("generated_by: scripts/podcast/_proposal_writer.py", out)
        self.assertIn("generated_at: 2026-05-19T12:00:00Z", out)
        self.assertIn("(none in this episode)", out)  # empty quotes + clinical

    def test_quote_entry_renders_correctly(self):
        b = pw.ProposalBundle(
            book_slug="ayyuhal-walad",
            episode_id="EP02-hatim",
            quotes=[pw.QuoteProposal(
                text="Knowledge that you do not act on will not save you.",
                attribution="al-Ghazali",
                source_ref="Ayyuhal Walad, ch. 1",
                episode_context="Anchor for the chapter's central tension",
                confidence="high",
            )],
        )
        out = pw.render_proposal(b, generated_at="2026-05-19T12:00:00Z")
        self.assertIn("Knowledge that you do not act on will not save you.", out)
        self.assertIn("attribution: 'al-Ghazali'", out)
        self.assertIn("confidence: high", out)

    def test_clinical_entry_renders_correctly(self):
        b = pw.ProposalBundle(
            book_slug="ayyuhal-walad",
            episode_id="EP02-hatim",
            clinical=[pw.ClinicalProposal(
                title="Hatim's eight benefits",
                summary="Pattern of inventorying lifelong work into eight distilled benefits.",
                source_ref="Ayyuhal Walad, ch. 2",
                episode_context="Craft observation for memoir benefit-structuring",
            )],
        )
        out = pw.render_proposal(b)
        self.assertIn("title: 'Hatim''s eight benefits'", out)  # escaped apostrophe
        self.assertIn("Pattern of inventorying", out)

    def test_yaml_escape_handles_apostrophes(self):
        self.assertEqual(pw._yaml_escape("don't"), "don''t")
        self.assertEqual(pw._yaml_escape("'all'"), "''all''")

    def test_empty_sections_marked_explicitly(self):
        b = pw.ProposalBundle(book_slug="x", episode_id="EP01-y")
        out = pw.render_proposal(b)
        # Both sections should explicitly say "(none in this episode)" rather than blank
        self.assertEqual(out.count("(none in this episode)"), 2)


class WriteProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_to_canonical_path(self):
        b = pw.ProposalBundle(book_slug="x", episode_id="EP02-test")
        out_path = pw.write_proposal(self.book, b)
        expected = self.book / "_system" / "episode-drafts" / "EP02-test" / "proposed-library-entries.md"
        self.assertEqual(out_path, expected)
        self.assertTrue(out_path.exists())

    def test_creates_directories(self):
        b = pw.ProposalBundle(book_slug="x", episode_id="EP02-test")
        pw.write_proposal(self.book, b)
        self.assertTrue((self.book / "_system" / "episode-drafts" / "EP02-test").is_dir())

    def test_refuses_overwrite_by_default(self):
        b = pw.ProposalBundle(book_slug="x", episode_id="EP02-test")
        pw.write_proposal(self.book, b)
        with self.assertRaises(FileExistsError) as cm:
            pw.write_proposal(self.book, b)
        self.assertIn("Promotion is journal-side", str(cm.exception))

    def test_overwrite_when_explicit(self):
        b1 = pw.ProposalBundle(book_slug="x", episode_id="EP02-test",
                               quotes=[pw.QuoteProposal("first", "x", "x", "x")])
        b2 = pw.ProposalBundle(book_slug="x", episode_id="EP02-test",
                               quotes=[pw.QuoteProposal("second", "x", "x", "x")])
        path = pw.write_proposal(self.book, b1)
        first = path.read_text()
        pw.write_proposal(self.book, b2, overwrite=True)
        second = path.read_text()
        self.assertNotEqual(first, second)
        self.assertIn("second", second)

    def test_emit_is_schema_valid(self):
        """Every emitted file MUST carry the required frontmatter keys."""
        b = pw.ProposalBundle(book_slug="kitab-foo", episode_id="EP03-bar")
        path = pw.write_proposal(self.book, b)
        text = path.read_text()
        for key in ("schema_version:", "book_slug:", "episode_id:",
                    "generated_by:", "generated_at:"):
            self.assertIn(key, text, f"missing frontmatter key: {key}")

    def test_promotion_ledger_section_present_empty(self):
        b = pw.ProposalBundle(book_slug="x", episode_id="EP01-y")
        path = pw.write_proposal(self.book, b)
        self.assertIn("## Promotion ledger", path.read_text())


class SchemaVersionTests(unittest.TestCase):
    def test_schema_version_is_one(self):
        self.assertEqual(pw.SCHEMA_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
