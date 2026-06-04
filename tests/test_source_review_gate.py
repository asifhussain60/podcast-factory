"""Tests for scripts/podcast/phases/source_review_gate.py (Wave I, I4)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast" / "phases"))

from source_review_gate import ReviewGate, run_source_review_gate


class TestReviewGateDataStructure(unittest.TestCase):
    """ReviewGate must serialize/deserialize correctly."""

    def test_gate_defaults(self):
        g = ReviewGate()
        self.assertEqual(g.phase, "06a")
        self.assertFalse(g.approved)
        self.assertEqual(g.warnings, [])
        self.assertIsNone(g.reviewed_at)
        self.assertIsNone(g.approved_at)

    def test_gate_to_json(self):
        g = ReviewGate(approved=False, warnings=[{"severity": "P1", "message": "test"}])
        data = json.loads(g.to_json())
        self.assertIn("approved", data)
        self.assertIn("warnings", data)
        self.assertFalse(data["approved"])

    def test_gate_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-gate.json"
            path.write_text(json.dumps({
                "phase": "06a",
                "approved": True,
                "warnings": [],
                "reviewed_at": "2026-01-01T00:00:00Z",
                "approved_at": "2026-01-02T00:00:00Z",
            }))
            g = ReviewGate.from_file(path)
            self.assertTrue(g.approved)
            self.assertEqual(g.reviewed_at, "2026-01-01T00:00:00Z")


class TestRunSourceReviewGate(unittest.TestCase):
    """run_source_review_gate must write gate file and set correct defaults."""

    def _make_book_dir(self, tmp: str) -> Path:
        book_dir = Path(tmp) / "test-book"
        (book_dir / "_system").mkdir(parents=True)
        (book_dir / "chapters").mkdir(parents=True)
        (book_dir / "meta.yml").write_text("title: Test Book\ntradition_affinity: universal\n")
        (book_dir / "chapters" / "ch01.txt").write_text("Chapter one content here.")
        return book_dir

    def test_dry_run_writes_gate_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(tmp)
            gate = run_source_review_gate(book_dir, dry_run=True)
            gate_path = book_dir / "_system" / "review-gate.json"
            self.assertTrue(gate_path.exists())
            self.assertIsInstance(gate, ReviewGate)

    def test_gate_approved_false_initially(self):
        """Gate must not be approved immediately after running — requires human action."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(tmp)
            gate = run_source_review_gate(book_dir, dry_run=True)
            self.assertFalse(gate.approved)

    def test_already_approved_gate_not_overwritten(self):
        """If gate is already approved, run_source_review_gate must not re-run."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(tmp)
            gate_path = book_dir / "_system" / "review-gate.json"
            gate_path.write_text(json.dumps({
                "phase": "06a", "approved": True, "warnings": [],
                "reviewed_at": "2026-01-01T00:00:00Z",
                "approved_at": "2026-01-02T00:00:00Z",
            }))
            gate = run_source_review_gate(book_dir, dry_run=False)
            self.assertTrue(gate.approved)

    def test_gate_has_phase_06a(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(tmp)
            gate = run_source_review_gate(book_dir, dry_run=True)
            self.assertEqual(gate.phase, "06a")

    def test_gate_warnings_is_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(tmp)
            gate = run_source_review_gate(book_dir, dry_run=True)
            self.assertIsInstance(gate.warnings, list)


class TestApproveBookCLI(unittest.TestCase):
    """approve_book.py must correctly set approved=true on the gate file."""

    def test_approve_sets_flag(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "podcast"))
        from approve_book import approve_book
        with tempfile.TemporaryDirectory() as tmp:
            # Mock BOOKS_DIR — use tmp directly
            book_dir = Path(tmp) / "test-book-slug"
            (book_dir / "_system").mkdir(parents=True)
            gate_path = book_dir / "_system" / "review-gate.json"
            gate_path.write_text(json.dumps({
                "phase": "06a", "approved": False, "warnings": [],
                "reviewed_at": "2026-01-01T00:00:00Z", "approved_at": None,
            }))
            # Patch BOOKS_DIR
            import approve_book as ab
            orig = ab.BOOKS_DIR
            ab.BOOKS_DIR = Path(tmp)
            try:
                rc = approve_book("test-book-slug")
            finally:
                ab.BOOKS_DIR = orig
            self.assertEqual(rc, 0)
            updated = json.loads(gate_path.read_text())
            self.assertTrue(updated["approved"])
            self.assertIsNotNone(updated["approved_at"])


if __name__ == "__main__":
    unittest.main()
