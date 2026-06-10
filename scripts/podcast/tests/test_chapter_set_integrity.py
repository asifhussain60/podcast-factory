#!/usr/bin/env python3
"""Tests for check_chapter_set.py P7-P10 (chapter-set integrity wave, 2026-06-10).

P7 source coverage, P8 overlap + n-gram duplication, P9 sermon integrity,
P10 set density. Fixtures are synthetic book dirs under a tempdir.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import check_chapter_set as ccs  # noqa: E402


def _mk_book(tmp: Path) -> Path:
    book = tmp / "Islamic" / "fixture-book"
    (book / "chapters").mkdir(parents=True)
    (book / "chapter-contracts").mkdir(parents=True)
    (book / "_system" / "source" / "text" / "_chunks" / "0d").mkdir(parents=True)
    return book


def _write_toc(book: Path, ranges: list[tuple[int, int]]) -> None:
    toc = {
        "source_chapters": [
            {"sc_index": i + 1, "source_title": f"sc{i+1}",
             "start_line": a, "end_line": b}
            for i, (a, b) in enumerate(ranges)
        ]
    }
    (book / "_system" / "source" / "text" / "_chunks" / "0d" / "source-toc.json").write_text(
        json.dumps(toc), encoding="utf-8")


def _write_refined(book: Path, n_lines: int) -> None:
    (book / "_system" / "source" / "text" / "refined-english.md").write_text(
        "\n".join(f"line {i}" for i in range(1, n_lines + 1)), encoding="utf-8")


class SourceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book = _mk_book(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gap_flagged(self):
        _write_refined(self.book, 1000)
        _write_toc(self.book, [(1, 300), (500, 1000)])  # 199-line gap
        f = ccs.check_source_coverage(self.book)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["check"], "P7")
        self.assertIn("301-499", f[0]["msg"])

    def test_full_coverage_clean(self):
        _write_refined(self.book, 1000)
        _write_toc(self.book, [(1, 500), (501, 1000)])
        self.assertEqual(ccs.check_source_coverage(self.book), [])

    def test_legacy_book_without_toc_vacuous(self):
        self.assertEqual(ccs.check_source_coverage(self.book), [])

    def test_overlap_flagged_p0(self):
        _write_refined(self.book, 1000)
        _write_toc(self.book, [(1, 500), (450, 1000)])
        f = ccs.check_source_overlap(self.book)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["check"], "P8")
        self.assertEqual(f[0]["severity"], "P0")


class DuplicationTests(unittest.TestCase):
    def test_shared_block_flagged(self):
        dup = ("the master explained that the seven heavens emerged from the smoke "
               "and the seven earths from the thickness of mud below them all ")
        a = "## Concept one\n\n" + dup * 2 + "\n\nunique alpha text here."
        b = "## Concept two\n\n" + dup * 2 + "\n\nunique beta text there."
        f = ccs.check_cross_chapter_duplication({"ch-a": a, "ch-b": b})
        self.assertTrue(f, "shared 12-gram block must be flagged")
        self.assertEqual(f[0]["check"], "P8")

    def test_distinct_chapters_clean(self):
        a = "## One\n\n" + "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima " * 5
        b = "## Two\n\n" + "mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray " * 5
        self.assertEqual(ccs.check_cross_chapter_duplication({"a": a, "b": b}), [])

    def test_frame_sections_excluded(self):
        frame = "where this episode opens the same words repeat " * 6
        a = "## Where this episode opens\n\n" + frame + "\n## Real\n\nunique one."
        b = "## Where this episode opens\n\n" + frame + "\n## Real2\n\nunique two."
        self.assertEqual(ccs.check_cross_chapter_duplication({"a": a, "b": b}), [])


class SermonIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book = _mk_book(self.tmp)
        (self.book / "chapter-contracts" / "ep-one.yml").write_text(
            'slug: ep-one\nsermon:\n  present: true\n  section_title: "The opening sermon"\n',
            encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_sermon_section_p0(self):
        chapters = {"ep-one": "## Some other section\n\nbody text."}
        f = ccs.check_sermon_integrity(self.book, chapters)
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["check"], f[0]["severity"]), ("P9", "P0"))

    def test_sermon_in_two_chapters_p0(self):
        body = "## The opening sermon\n\n" + "word " * 200
        f = ccs.check_sermon_integrity(self.book, {"ep-one": body, "ep-two": body})
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["severity"], "P0")
        self.assertIn("2 chapters", f[0]["msg"])

    def test_sermon_stub_p1(self):
        body = "## The opening sermon\n\nonly a few words here.\n\n## Next\n\nmore."
        f = ccs.check_sermon_integrity(self.book, {"ep-one": body})
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["severity"], "P1")
        self.assertIn("stub", f[0]["msg"])

    def test_whole_sermon_clean(self):
        body = "## The opening sermon\n\n" + "word " * 200 + "\n\n## Next\n\nrest."
        self.assertEqual(ccs.check_sermon_integrity(self.book, {"ep-one": body}), [])


class SetDensityTests(unittest.TestCase):
    def test_over_dense_chapter_flagged(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            cf = tmp / "ch01-over.txt"
            cf.write_text(
                "\n\n".join(f"## Concept {i}\n\n" + "word " * 50 for i in range(1, 7)),
                encoding="utf-8")
            f = ccs.check_set_density([cf], "fixture-book")
            self.assertEqual(len(f), 1)
            self.assertEqual(f[0]["check"], "P10")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
