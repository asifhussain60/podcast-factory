#!/usr/bin/env python3
"""Tests for scripts/podcast/audit_page_markers.py (P22.markers.audit-tool).

Verifies the audit logic against synthesized mini-fixtures — no real book
required. The acceptance contract is: exit 0 on clean match, exit non-zero
with per-window breakdown on any mismatch (lost, hallucinated, repeated).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import audit_page_markers as apm  # noqa: E402


class ExtractPageMarkersTests(unittest.TestCase):
    def test_empty_string(self) -> None:
        self.assertEqual(apm.extract_page_markers(""), [])

    def test_no_markers(self) -> None:
        self.assertEqual(apm.extract_page_markers("just prose, no markers"), [])

    def test_single_marker(self) -> None:
        self.assertEqual(apm.extract_page_markers("<!-- page 1 -->"), [1])

    def test_multiple_markers_preserves_order(self) -> None:
        text = "<!-- page 3 -->\nbody\n<!-- page 1 -->\nmore\n<!-- page 2 -->"
        # Audit preserves emission order — the audit logic compares sets for
        # lost/hallucinated, so ordering doesn't change the verdict, but the
        # extractor must surface every occurrence to drive per-window analysis.
        self.assertEqual(apm.extract_page_markers(text), [3, 1, 2])

    def test_ignores_non_matching_html_comments(self) -> None:
        text = "<!-- context-overlap -->\n<!-- page 5 -->\n<!-- footnote 3 -->"
        self.assertEqual(apm.extract_page_markers(text), [5])

    def test_multi_digit_numbers(self) -> None:
        text = "<!-- page 99 -->\n<!-- page 100 -->\n<!-- page 416 -->"
        self.assertEqual(apm.extract_page_markers(text), [99, 100, 416])


class SummarizeRangesTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(apm._summarize_ranges([]), "")

    def test_single(self) -> None:
        self.assertEqual(apm._summarize_ranges([5]), "5")

    def test_contiguous_collapses(self) -> None:
        self.assertEqual(apm._summarize_ranges([1, 2, 3, 4, 5]), "1-5")

    def test_mixed(self) -> None:
        # Mirrors the asaas defect summary: 19-27, 53-61, 130-139, ...
        self.assertEqual(
            apm._summarize_ranges([19, 20, 21, 22, 23, 24, 25, 26, 27, 53, 54, 55, 56, 57, 58, 59, 60, 61]),
            "19-27, 53-61",
        )

    def test_isolated_pages(self) -> None:
        self.assertEqual(apm._summarize_ranges([1, 5, 10]), "1, 5, 10")

    def test_deduplicates(self) -> None:
        self.assertEqual(apm._summarize_ranges([5, 5, 5, 6]), "5-6")


class TopLevelAuditTests(unittest.TestCase):
    """Tests against tempdir fixtures that synthesize a tiny raw + refined
    pair with known page-marker drift."""

    def _write(self, content: str) -> Path:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(content)
        f.close()
        return Path(f.name)

    def test_clean_match(self) -> None:
        raw = self._write("<!-- page 1 -->\n<!-- page 2 -->\n<!-- page 3 -->")
        refined = self._write("<!-- page 1 -->\n<!-- page 2 -->\n<!-- page 3 -->")
        _, _, lost, halluc = apm.audit_top_level(raw, refined)
        self.assertEqual(lost, [])
        self.assertEqual(halluc, [])

    def test_detects_lost_markers(self) -> None:
        raw = self._write("<!-- page 1 -->\n<!-- page 2 -->\n<!-- page 3 -->")
        refined = self._write("<!-- page 1 -->\n<!-- page 3 -->")  # page 2 lost
        _, _, lost, halluc = apm.audit_top_level(raw, refined)
        self.assertEqual(lost, [2])
        self.assertEqual(halluc, [])

    def test_detects_hallucinated_markers(self) -> None:
        raw = self._write("<!-- page 1 -->\n<!-- page 2 -->")
        refined = self._write("<!-- page 1 -->\n<!-- page 2 -->\n<!-- page 99 -->")
        _, _, lost, halluc = apm.audit_top_level(raw, refined)
        self.assertEqual(lost, [])
        self.assertEqual(halluc, [99])

    def test_simultaneous_lost_and_hallucinated(self) -> None:
        # Mimics asaas win-010 + win-003 pattern: one window lost markers,
        # another hallucinated one
        raw = self._write("<!-- page 1 -->\n<!-- page 2 -->\n<!-- page 3 -->")
        refined = self._write("<!-- page 1 -->\n<!-- page 99 -->")
        _, _, lost, halluc = apm.audit_top_level(raw, refined)
        self.assertEqual(lost, [2, 3])
        self.assertEqual(halluc, [99])


class WindowAuditTests(unittest.TestCase):
    """Tests against a synthesized _chunks/0b/ directory."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.chunks_dir = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _write_window(self, name: str, in_pages: list[int], out_pages: list[int]) -> None:
        in_path = self.chunks_dir / f"{name}.in.md"
        out_path = self.chunks_dir / f"{name}.out.md"
        in_path.write_text("\n".join(f"<!-- page {p} -->" for p in in_pages))
        out_path.write_text("\n".join(f"<!-- page {p} -->" for p in out_pages))

    def test_no_chunks_dir_returns_empty(self) -> None:
        missing = Path(self.tmpdir.name) / "nonexistent"
        self.assertEqual(apm.audit_windows(missing), [])

    def test_clean_window(self) -> None:
        self._write_window("win-001", [1, 2, 3], [1, 2, 3])
        audits = apm.audit_windows(self.chunks_dir)
        self.assertEqual(len(audits), 1)
        self.assertTrue(audits[0].is_clean)
        self.assertEqual(audits[0].delta, 0)

    def test_window_with_lost_pages(self) -> None:
        self._write_window("win-003", [19, 20, 21, 22, 23, 24, 25, 26, 27], [])
        audits = apm.audit_windows(self.chunks_dir)
        self.assertEqual(len(audits), 1)
        a = audits[0]
        self.assertFalse(a.is_clean)
        self.assertEqual(a.delta, 9)
        self.assertEqual(a.lost_pages, [19, 20, 21, 22, 23, 24, 25, 26, 27])
        self.assertEqual(a.hallucinated_pages, [])

    def test_window_with_hallucinated_page(self) -> None:
        self._write_window("win-010", [80, 81], [80, 81, 86])
        audits = apm.audit_windows(self.chunks_dir)
        self.assertFalse(audits[0].is_clean)
        self.assertEqual(audits[0].hallucinated_pages, [86])

    def test_window_ordered_by_filename(self) -> None:
        # asaas had 49 windows; audit should iterate in filename order so the
        # per-window breakdown reads top-to-bottom as the run executed
        self._write_window("win-003", [1], [1])
        self._write_window("win-001", [2], [2])
        self._write_window("win-002", [3], [3])
        audits = apm.audit_windows(self.chunks_dir)
        self.assertEqual([a.name for a in audits], ["win-001", "win-002", "win-003"])


class IntegrationTests(unittest.TestCase):
    """End-to-end test of main() with a tempdir book layout."""

    def test_main_exits_zero_on_clean_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Build a fake repo root: <tmp>/content/drafts/<slug>/_system/source/text/
            book_slug = "tiny-test"
            text_dir = Path(tmp) / "content" / "drafts" / book_slug / "_system" / "source" / "text"
            text_dir.mkdir(parents=True)
            (text_dir / "raw-extract.md").write_text("<!-- page 1 -->\nbody\n<!-- page 2 -->")
            (text_dir / "refined-english.md").write_text("<!-- page 1 -->\nrefined\n<!-- page 2 -->")

            # Monkeypatch the repo-root resolver so it points at our temp tree
            orig_resolver = apm._resolve_book_dir
            try:
                apm._resolve_book_dir = lambda slug, cat: text_dir.parent.parent.parent  # noqa: E731
                rc = apm.main(["--book", book_slug, "--skip-window-audit"])
                self.assertEqual(rc, 0)
            finally:
                apm._resolve_book_dir = orig_resolver


if __name__ == "__main__":
    unittest.main()
