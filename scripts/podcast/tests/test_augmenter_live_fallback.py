#!/usr/bin/env python3
"""Tests for Wave J (J3): augmenter live verse fallback + J5 topic marker emission.

All tests are pure unit tests — no DB, no live server.
The local server client is monkey-patched in each test.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import intelligence.augmenter as aug  # noqa: E402


def _make_book_dir(tmp: Path, *, live_quran: bool = False,
                   topic_markers: bool = False, tags: list | None = None) -> Path:
    book_dir = tmp / "test-book"
    (book_dir / "_system").mkdir(parents=True)
    series: dict = {}
    if live_quran:
        series["enable_live_quran_lookup"] = True
    if topic_markers:
        series["enable_topic_markers"] = True
    meta = {"series": series, "knowledge_tags": tags or []}
    import yaml  # type: ignore[import]
    (book_dir / "meta.yml").write_text(yaml.dump(meta), encoding="utf-8")
    return book_dir


class LiveQuranGateTests(unittest.TestCase):
    """enable_live_quran_lookup gate behaviour."""

    def test_gate_off_returns_text_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=False)
            text = "Chapter mentions Q2:255 in passing."
            result = aug.augment_chapter_text(text, book_dir)
            self.assertEqual(result, text)

    def test_gate_on_no_citation_returns_text_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=True)
            text = "No Quran citation here."
            result = aug.augment_chapter_text(text, book_dir)
            self.assertEqual(result, text)

    def test_gate_on_citation_in_db_no_live_call(self):
        """If the verse is already in the knowledge DB, no live server call is made."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=True)
            text = "The throne verse Q2:255 is essential."
            with mock.patch.object(aug, "_verse_in_db", return_value=True) as m_db, \
                 mock.patch.object(aug, "_live_verse") as m_live:
                aug.augment_chapter_text(text, book_dir)
            m_live.assert_not_called()

    def test_gate_on_citation_not_in_db_calls_live(self):
        """Citation not in DB → live server call made."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=True)
            text = "Chapter references Q2:255 explicitly."
            fake_verse = {"surah": 2, "ayat": 255, "pickthall": "Allah! There is no god but He.",
                          "arabic": "", "asad": "", "urdu": "", "phonetic": ""}
            with mock.patch.object(aug, "_verse_in_db", return_value=False), \
                 mock.patch.object(aug, "_live_verse", return_value=fake_verse) as m_live:
                result = aug.augment_chapter_text(text, book_dir)
            m_live.assert_called_once_with(2, 255)
            self.assertIn("LIVE VERSE CONTEXT", result)
            self.assertIn("Allah! There is no god but He.", result)

    def test_server_unreachable_returns_text_unchanged(self):
        """If live server returns None (unreachable), text passes through unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=True)
            text = "Q2:255 mentioned here."
            with mock.patch.object(aug, "_verse_in_db", return_value=False), \
                 mock.patch.object(aug, "_live_verse", return_value=None):
                result = aug.augment_chapter_text(text, book_dir)
            self.assertNotIn("LIVE VERSE CONTEXT", result)

    def test_mcp_log_written_on_live_hit(self):
        """A live hit writes a JSON line to mcp-calls.jsonl."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_quran=True)
            log_path = book_dir / "_system" / "mcp-calls.jsonl"
            text = "See Q2:255 for the throne verse."
            fake_verse = {"surah": 2, "ayat": 255, "pickthall": "Allah! There is no god.",
                          "arabic": "", "asad": "", "urdu": "", "phonetic": ""}
            with mock.patch.object(aug, "_verse_in_db", return_value=False), \
                 mock.patch.object(aug, "_live_verse", return_value=fake_verse):
                aug.augment_chapter_text(text, book_dir, mcp_log=log_path)
            self.assertTrue(log_path.exists())
            entry = json.loads(log_path.read_text())
            self.assertEqual(entry["tool"], "quran_verse")
            self.assertEqual(entry["source"], "live")
            self.assertEqual(entry["args"]["surah"], 2)


class TopicMarkerGateTests(unittest.TestCase):
    """enable_topic_markers gate behaviour."""

    def test_gate_off_returns_text_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), topic_markers=False, tags=["tawhid"])
            text = "The concept of tawhid is fundamental."
            result = aug.emit_topic_markers(text, book_dir)
            self.assertEqual(result, text)

    def test_gate_on_no_match_returns_text_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), topic_markers=True, tags=["tawhid"])
            text = "Unrelated content with no matching terms."
            with mock.patch.object(aug, "_live_topic_search", return_value=[]):
                result = aug.emit_topic_markers(text, book_dir)
            self.assertEqual(result, text)

    def test_gate_on_match_wraps_term(self):
        """Matching topic wraps the term with a .ref-topic span."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), topic_markers=True, tags=["tawhid"])
            text = "The concept of tawhid is the foundation of everything."
            fake_topics = [{"topic_id": 42, "topic": "tawhid"}]
            with mock.patch.object(aug, "_live_topic_search", return_value=fake_topics):
                result = aug.emit_topic_markers(text, book_dir)
            self.assertIn('data-topic-id="42"', result)
            self.assertIn('class="ref-topic"', result)
            self.assertIn("tawhid", result)


if __name__ == "__main__":
    unittest.main()
