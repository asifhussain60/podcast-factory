#!/usr/bin/env python3
"""Tests for Wave J (J4): live session style fetch in rewrite_chapters.py.

Pure unit tests — no Sonnet calls, no live server.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent.parent
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))
sys.path.insert(0, str(_HERE.parent))

import rewrite_chapters as rc  # noqa: E402


def _make_book_dir(tmp: Path, *, live_style: bool = False) -> Path:
    book_dir = tmp / "test-book"
    book_dir.mkdir(parents=True)
    series: dict = {}
    if live_style:
        series["enable_live_style_fetch"] = True
    meta = {"series": series}
    import yaml  # type: ignore[import]
    (book_dir / "meta.yml").write_text(yaml.dump(meta), encoding="utf-8")
    return book_dir


def _make_chapter(book_dir: Path, content: str = "Chapter text about Imamah and tawhid.") -> Path:
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    ch = chapters_dir / "ch01-test.txt"
    ch.write_text(content, encoding="utf-8")
    return ch


class ExtractThemesTests(unittest.TestCase):
    def test_returns_top_phrases(self):
        text = "The Imam is the Guide. The Imam teaches the faithful. Tawhid is central."
        themes = rc.extract_chapter_themes(text, n=2)
        self.assertLessEqual(len(themes), 2)
        self.assertTrue(all(isinstance(t, str) for t in themes))

    def test_returns_empty_for_blank_text(self):
        self.assertEqual(rc.extract_chapter_themes(""), [])

    def test_deduplicates(self):
        text = "Imam Imam Imam guide guide guide"
        themes = rc.extract_chapter_themes(text, n=5)
        self.assertEqual(len(themes), len(set(themes)))


class LiveStyleGateTests(unittest.TestCase):
    def test_gate_off_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_style=False)
            ch = _make_chapter(book_dir)
            result = rc._build_live_style_supplement(ch, book_dir)
            self.assertEqual(result, "")

    def test_gate_on_server_unreachable_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_style=True)
            ch = _make_chapter(book_dir)
            with mock.patch("rewrite_chapters._live_sessions", return_value=[]):
                result = rc._build_live_style_supplement(ch, book_dir)
            self.assertEqual(result, "")

    def test_gate_on_passages_returned_included_in_supplement(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_style=True)
            ch = _make_chapter(book_dir, "The Imam teaches about tawhid and wilaya.")
            fake_passages = [{"session_id": 1, "content": "Wilaya is the inner bond."},
                             {"session_id": 2, "content": "Tawhid is divine unity."}]
            with mock.patch("rewrite_chapters._live_sessions", return_value=fake_passages):
                result = rc._build_live_style_supplement(ch, book_dir)
            self.assertIn("LIVE SESSION STYLE SAMPLES", result)
            self.assertIn("Wilaya", result)

    def test_deduplicates_by_session_id(self):
        """Same session_id returned for two theme queries → appears only once."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_style=True)
            ch = _make_chapter(book_dir, "Imam teaches Wilaya and tawhid and haqiqa.")
            same_passage = [{"session_id": 99, "content": "Duplicate passage."}]
            with mock.patch("rewrite_chapters._live_sessions", return_value=same_passage):
                result = rc._build_live_style_supplement(ch, book_dir)
            self.assertEqual(result.count("Duplicate passage."), 1)

    def test_no_crash_on_exception(self):
        """Even if the live fetch raises, the supplement returns '' (never crashes)."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), live_style=True)
            ch = _make_chapter(book_dir)
            with mock.patch("rewrite_chapters._live_sessions", side_effect=RuntimeError("boom")):
                result = rc._build_live_style_supplement(ch, book_dir)
            self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
