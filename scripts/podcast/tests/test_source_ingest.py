#!/usr/bin/env python3
"""Phase 0a for books whose source was written, not scanned.

`phase_0a_ingest_source_md` is the Azure-OCR replacement for the categories whose
material already exists as English markdown. It had no test naming it, which matters
more than the line count suggests: it is the only writer of `raw-extract.md` on that
route, and every phase downstream — refinement, chapter design, enrichment — reads
that one file. A silent change to the concatenation order or the section markers would
surface as a content defect many phases later.

The four refusals below are the reason it can be trusted to run unattended: each one
would otherwise destroy or fabricate the book's source of truth.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _authoring._core import SKIP_OCR_CATEGORIES  # noqa: E402
from phases.source_ingest import phase_0a_ingest_source_md  # noqa: E402

CATEGORY = sorted(SKIP_OCR_CATEGORIES)[0]


class SourceIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.book_dir = self.root / "a-book"
        (self.book_dir / "source").mkdir(parents=True)
        # REPO_ROOT is only used for the relative paths in messages and provenance.
        self._patch = mock.patch("phases.source_ingest.REPO_ROOT", self.root)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self.tmp.cleanup()

    def _write(self, name: str, text: str) -> None:
        (self.book_dir / "source" / name).write_text(text, encoding="utf-8")

    def _ingest(self, **kw) -> None:
        with mock.patch("builtins.print"):
            phase_0a_ingest_source_md(self.book_dir, CATEGORY, "a-book", **kw)

    def _raw(self) -> str:
        return (self.book_dir / "_system" / "source" / "text" / "raw-extract.md").read_text(encoding="utf-8")

    def _provenance(self) -> dict:
        return json.loads(
            (self.book_dir / "_system" / "source" / "text" / "_provenance.json").read_text(encoding="utf-8")
        )

    # ── what it produces ─────────────────────────────────────────────────────

    def test_the_three_phase_0a_artifacts_are_written(self) -> None:
        self._write("01-first.md", "First words.\n")
        self._ingest()
        text_dir = self.book_dir / "_system" / "source" / "text"
        for name in ("raw-extract.md", "_provenance.json", "_extraction-notes.md"):
            self.assertTrue((text_dir / name).exists(), f"{name} was not written")

    def test_files_are_concatenated_in_alphabetical_order(self) -> None:
        # The order IS the book's order — the files are named to sort into it, and
        # every later phase reads the result as one continuous source.
        self._write("02-second.md", "Second chapter body.\n")
        self._write("01-first.md", "First chapter body.\n")
        self._write("03-third.md", "Third chapter body.\n")
        self._ingest()
        raw = self._raw()
        self.assertLess(raw.index("First chapter"), raw.index("Second chapter"))
        self.assertLess(raw.index("Second chapter"), raw.index("Third chapter"))

    def test_each_section_is_marked_with_the_file_it_came_from(self) -> None:
        # The provenance a scanned book gets from OCR metadata; here it is this marker.
        self._write("01-first.md", "Body one.\n")
        self._write("02-second.md", "Body two.\n")
        self._ingest()
        raw = self._raw()
        self.assertIn("<!-- source: 01-first.md -->", raw)
        self.assertIn("<!-- source: 02-second.md -->", raw)

    def test_the_provenance_records_a_word_count_per_file_and_a_total(self) -> None:
        self._write("01-first.md", "one two three\n")
        self._write("02-second.md", "four five\n")
        self._ingest()
        prov = self._provenance()
        self.assertEqual([m["word_count"] for m in prov["source_files"]], [3, 2])
        self.assertEqual(prov["total_word_count"], 5)

    def test_the_provenance_says_no_azure_ran(self) -> None:
        # This route deliberately spends nothing on OCR or translation. A non-null
        # value here would mean a book was billed for a scan it never needed.
        self._write("01-first.md", "Body.\n")
        self._ingest()
        prov = self._provenance()
        self.assertIsNone(prov["azure_ocr"])
        self.assertIsNone(prov["translator"])
        self.assertEqual(prov["category"], CATEGORY)

    # ── the four refusals ────────────────────────────────────────────────────

    def test_it_refuses_a_category_that_belongs_on_the_ocr_route(self) -> None:
        self._write("01-first.md", "Body.\n")
        with self.assertRaises(RuntimeError) as ctx:
            with mock.patch("builtins.print"):
                phase_0a_ingest_source_md(self.book_dir, "books", "a-book")
        self.assertIn("SKIP_OCR_CATEGORIES", str(ctx.exception))

    def test_it_refuses_when_there_is_no_source_directory(self) -> None:
        (self.book_dir / "source").rmdir()
        with self.assertRaises(RuntimeError) as ctx:
            self._ingest()
        self.assertIn("source directory not found", str(ctx.exception))

    def test_it_refuses_an_empty_source_directory_rather_than_writing_nothing(self) -> None:
        # An empty raw-extract.md would send every downstream phase to work on a book
        # with no text, and each would report its own confusing failure instead.
        with self.assertRaises(RuntimeError) as ctx:
            self._ingest()
        self.assertIn("no .md files found", str(ctx.exception))

    def test_it_refuses_to_overwrite_an_existing_extract_without_force(self) -> None:
        self._write("01-first.md", "Original body.\n")
        self._ingest()
        self._write("01-first.md", "Replacement body.\n")
        with self.assertRaises(RuntimeError) as ctx:
            self._ingest()
        self.assertIn("already exists", str(ctx.exception))
        self.assertIn("Original body", self._raw(), "the refusal must leave the extract untouched")

    def test_force_overwrites_deliberately(self) -> None:
        self._write("01-first.md", "Original body.\n")
        self._ingest()
        self._write("01-first.md", "Replacement body.\n")
        self._ingest(force=True)
        self.assertIn("Replacement body", self._raw())

    def test_force_does_not_clobber_extraction_notes_already_written(self) -> None:
        # 0b and 0c append to that file. A re-ingest must not wipe their notes.
        self._write("01-first.md", "Body.\n")
        self._ingest()
        notes = self.book_dir / "_system" / "source" / "text" / "_extraction-notes.md"
        notes.write_text("# Notes\n\nA human observation from 0b.\n", encoding="utf-8")
        self._ingest(force=True)
        self.assertIn("A human observation from 0b", notes.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
