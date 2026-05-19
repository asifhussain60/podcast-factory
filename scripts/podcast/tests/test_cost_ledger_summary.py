#!/usr/bin/env python3
"""Tests for scripts/podcast/cost_ledger_summary.py (P6.2 deliverable)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import cost_ledger_summary as cls  # noqa: E402


SAMPLE_ROWS = [
    {"ts": "2026-05-19T12:00:00Z", "phase": "05-refine-english", "step": "win-001",
     "model": "claude-opus-4-7", "input_tokens": 1000, "output_tokens": 500,
     "cache_read": 0, "cache_create": 0, "cost_usd": 0.052500},
    {"ts": "2026-05-19T12:01:00Z", "phase": "05-refine-english", "step": "win-002",
     "model": "claude-opus-4-7", "input_tokens": 1200, "output_tokens": 600,
     "cache_read": 100, "cache_create": 0, "cost_usd": 0.063150},
    {"ts": "2026-05-19T12:05:00Z", "phase": "06-phonetics", "step": "(global)",
     "model": "claude-sonnet-4-6", "input_tokens": 5000, "output_tokens": 2000,
     "cache_read": 0, "cache_create": 0, "cost_usd": 0.045000},
]


class SummarizeTests(unittest.TestCase):
    def test_grand_totals(self):
        s = cls.summarize(SAMPLE_ROWS)
        self.assertEqual(s["row_count"], 3)
        self.assertEqual(s["totals"]["calls"], 3)
        self.assertEqual(s["totals"]["input_tokens"], 7200)
        self.assertEqual(s["totals"]["output_tokens"], 3100)
        self.assertAlmostEqual(s["totals"]["cost_usd"], 0.1607, places=3)

    def test_by_phase_aggregates(self):
        s = cls.summarize(SAMPLE_ROWS)
        self.assertEqual(s["by_phase"]["05-refine-english"]["calls"], 2)
        self.assertEqual(s["by_phase"]["06-phonetics"]["calls"], 1)
        self.assertEqual(s["by_phase"]["05-refine-english"]["input_tokens"], 2200)

    def test_by_model_aggregates(self):
        s = cls.summarize(SAMPLE_ROWS)
        self.assertIn("claude-opus-4-7", s["by_model"])
        self.assertIn("claude-sonnet-4-6", s["by_model"])
        self.assertEqual(s["by_model"]["claude-opus-4-7"]["calls"], 2)

    def test_empty_rows_zero_totals(self):
        s = cls.summarize([])
        self.assertEqual(s["row_count"], 0)
        self.assertEqual(s["totals"]["calls"], 0)
        self.assertEqual(s["totals"]["cost_usd"], 0.0)

    def test_missing_fields_default_to_zero(self):
        rows = [{"phase": "x", "model": "claude-opus-4-7"}]
        s = cls.summarize(rows)
        self.assertEqual(s["totals"]["input_tokens"], 0)
        self.assertEqual(s["totals"]["cost_usd"], 0.0)
        self.assertEqual(s["totals"]["calls"], 1)


class LoadLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )

    def tearDown(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_loads_valid_rows(self):
        for r in SAMPLE_ROWS:
            self.tmp.write(json.dumps(r) + "\n")
        self.tmp.close()
        loaded = cls.load_ledger(Path(self.tmp.name))
        self.assertEqual(len(loaded), 3)

    def test_skips_malformed_lines(self):
        self.tmp.write(json.dumps(SAMPLE_ROWS[0]) + "\n")
        self.tmp.write("not json\n")
        self.tmp.write("\n")  # blank
        self.tmp.write(json.dumps(SAMPLE_ROWS[1]) + "\n")
        self.tmp.close()
        buf = io.StringIO()
        with redirect_stderr(buf):
            loaded = cls.load_ledger(Path(self.tmp.name))
        self.assertEqual(len(loaded), 2)
        self.assertIn("unparseable", buf.getvalue())


class MainCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "test-book"
        (self.book_dir / "_system").mkdir(parents=True)
        self.ledger = self.book_dir / "_system" / "cost-ledger.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self, rows):
        with self.ledger.open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def test_main_writes_validation_snapshot(self):
        self._seed(SAMPLE_ROWS)
        with redirect_stdout(io.StringIO()):
            rc = cls.main([str(self.book_dir)])
        self.assertEqual(rc, 0)
        snap = self.book_dir / "_system" / "cost-validation.json"
        self.assertTrue(snap.exists())
        data = json.loads(snap.read_text())
        self.assertEqual(data["row_count"], 3)

    def test_main_no_write_flag_suppresses_snapshot(self):
        self._seed(SAMPLE_ROWS)
        with redirect_stdout(io.StringIO()):
            rc = cls.main([str(self.book_dir), "--no-write"])
        self.assertEqual(rc, 0)
        self.assertFalse((self.book_dir / "_system" / "cost-validation.json").exists())

    def test_main_json_flag(self):
        self._seed(SAMPLE_ROWS)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cls.main([str(self.book_dir), "--json", "--no-write"])
        self.assertEqual(rc, 0)
        # Output should parse as JSON
        data = json.loads(buf.getvalue())
        self.assertEqual(data["row_count"], 3)

    def test_main_missing_ledger_returns_1(self):
        with redirect_stderr(io.StringIO()):
            rc = cls.main([str(self.book_dir / "no-such")])
        self.assertEqual(rc, 1)

    def test_main_empty_ledger_returns_2(self):
        self.ledger.write_text("")
        with redirect_stderr(io.StringIO()):
            rc = cls.main([str(self.book_dir)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
