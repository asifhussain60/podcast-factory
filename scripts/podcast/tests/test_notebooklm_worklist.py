#!/usr/bin/env python3
"""Unit tests for the durable NotebookLM worklist + the shared row builder.

Guards:
  - build_upload_rows produces one UploadRow per (filtered) episode, carrying the
    canonical chapter_stem the worklist checklist needs.
  - build_worklist_lines composes the locked upload table + slide-deck card +
    a per-episode drop-target checklist, and the checkbox flips on m4a presence.
  - the filter argument scopes rows (mixed-engine books).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import assemble_bundle  # noqa: E402
import _notebooklm_table as nlt  # noqa: E402

STEMS = ["ch01-the-call", "ch02-the-covenant"]
EPS = ["EP01-the-call", "EP02-the-covenant"]


def _make_book(tmp: str) -> Path:
    book = Path(tmp)
    (book / "_system").mkdir(parents=True, exist_ok=True)
    (book / "chapters").mkdir(exist_ok=True)
    (book / "episodes").mkdir(exist_ok=True)
    for stem, ep in zip(STEMS, EPS):
        (book / "chapters" / f"{stem}.txt").write_text("chapter body\n", encoding="utf-8")
        (book / "episodes" / f"{ep}.txt").write_text("framing body\n", encoding="utf-8")
    return book


def _mapping(book):
    # Same discovery the finalize halt + audio-ingest use.
    return assemble_bundle._load_episode_map(book)


class UploadRowBuilderTests(unittest.TestCase):
    def test_build_upload_rows_one_per_episode_with_stem(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            rows = assemble_bundle.build_upload_rows(book, _mapping(book))
        self.assertEqual([r.n for r in rows], [1, 2])
        self.assertEqual(sorted(r.chapter_stem for r in rows), STEMS)

    def test_filter_scopes_rows(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            rows = assemble_bundle.build_upload_rows(
                book, _mapping(book), filter_episode_ids={"EP02-the-covenant"})
        self.assertEqual([r.n for r in rows], [2])
        self.assertEqual(rows[0].chapter_stem, "ch02-the-covenant")

    def test_table_keeps_locked_header(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            rows = assemble_bundle.build_upload_rows(book, _mapping(book))
        table = nlt.render_upload_table(rows)
        self.assertIn("| Chapters | Episodes | Deep dive or debate | Length |", table)


class WorklistCompositionTests(unittest.TestCase):
    def test_worklist_composes_table_card_and_checklist(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            rows = assemble_bundle.build_upload_rows(book, _mapping(book))
            lines = nlt.build_worklist_lines(
                book, upload_rows=rows, resume_cmd="RESUME-CMD")
        text = "\n".join(lines)
        self.assertIn("# NotebookLM worklist", text)
        self.assertIn("Deep dive or debate", text)          # the upload table
        self.assertIn("Drop-target checklist", text)         # the checklist section
        self.assertIn("RESUME-CMD", text)                    # the resume command
        # One checklist row per episode, all unchecked (no audio dropped yet).
        self.assertEqual(text.count("- [ ] EP"), 2)
        self.assertEqual(text.count("- [x] EP"), 0)

    def test_checkbox_flips_on_audio_presence(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            (book / "m4a").mkdir()
            (book / "m4a" / "ch01-the-call.m4a").write_bytes(b"AUDIO")
            rows = assemble_bundle.build_upload_rows(book, _mapping(book))
            text = "\n".join(nlt.build_worklist_lines(
                book, upload_rows=rows, resume_cmd="x"))
        self.assertEqual(text.count("- [x] EP"), 1)          # ch01 present
        self.assertEqual(text.count("- [ ] EP"), 1)          # ch02 still missing


if __name__ == "__main__":
    unittest.main()
