#!/usr/bin/env python3
"""Tests for scripts/podcast/_cost_ledger.py (P6.1 deliverable)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _cost_ledger  # noqa: E402


class PricingTests(unittest.TestCase):
    def test_known_model_costs(self):
        # opus 4.7 @ 1M input + 1M output ≈ $15 + $75 = $90
        cost = _cost_ledger.compute_cost_usd(
            "claude-opus-4-7",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        self.assertAlmostEqual(cost, 90.0, places=2)

    def test_sonnet_pricing(self):
        cost = _cost_ledger.compute_cost_usd(
            "claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        self.assertAlmostEqual(cost, 18.0, places=2)  # $3 + $15

    def test_cache_read_discount(self):
        """Cache reads should be ~10% of input price."""
        normal = _cost_ledger.compute_cost_usd(
            "claude-opus-4-7", input_tokens=1_000_000, output_tokens=0,
        )
        cached = _cost_ledger.compute_cost_usd(
            "claude-opus-4-7", input_tokens=0, output_tokens=0,
            cache_read=1_000_000,
        )
        self.assertAlmostEqual(cached / normal, 0.10, places=2)

    def test_unknown_model_warns_and_returns_zero(self):
        """No silent zero — must emit a stderr warning."""
        import io
        buf = io.StringIO()
        from contextlib import redirect_stderr
        with redirect_stderr(buf):
            cost = _cost_ledger.compute_cost_usd(
                "totally-made-up-model", input_tokens=1000, output_tokens=500,
            )
        self.assertEqual(cost, 0.0)
        self.assertIn("WARNING", buf.getvalue())
        self.assertIn("totally-made-up-model", buf.getvalue())

    def test_zero_tokens_zero_cost(self):
        self.assertEqual(
            _cost_ledger.compute_cost_usd("claude-opus-4-7", input_tokens=0, output_tokens=0),
            0.0,
        )


class UsageParsingTests(unittest.TestCase):
    def test_parses_in_out_pattern(self):
        stdout = "blah blah\nTokens: 12345 in, 6789 out"
        u = _cost_ledger.parse_usage_from_stdout(stdout)
        self.assertEqual(u["input"], 12345)
        self.assertEqual(u["output"], 6789)

    def test_parses_cache_read_create(self):
        stdout = "Tokens: 100 in, 50 out, cache: 1024 read, 256 create"
        u = _cost_ledger.parse_usage_from_stdout(stdout)
        self.assertEqual(u["cache_read"], 1024)
        self.assertEqual(u["cache_create"], 256)

    def test_missing_fields_default_to_zero(self):
        u = _cost_ledger.parse_usage_from_stdout("no usage data here")
        self.assertEqual(u, {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0})

    def test_empty_stdout_returns_zeros(self):
        self.assertEqual(
            _cost_ledger.parse_usage_from_stdout(""),
            {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0},
        )

    def test_never_raises_on_garbage(self):
        # Random junk shouldn't crash the parser.
        u = _cost_ledger.parse_usage_from_stdout("\x00\x01\x02junk{}\n  random ")
        self.assertEqual(u["input"], 0)


class AppendCostRowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "book-slug"
        # don't pre-create _system; the function should mkdir

    def tearDown(self):
        self.tmp.cleanup()

    def test_appends_one_row(self):
        row = _cost_ledger.append_cost_row(
            self.book,
            phase="05-refine-english",
            step="win-001",
            model="claude-opus-4-7",
            input_tokens=1000,
            output_tokens=500,
        )
        self.assertEqual(row.phase, "05-refine-english")
        ledger = self.book / "_system" / "cost-ledger.jsonl"
        self.assertTrue(ledger.exists())
        lines = ledger.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["step"], "win-001")
        self.assertEqual(parsed["input_tokens"], 1000)
        self.assertGreater(parsed["cost_usd"], 0)

    def test_multiple_appends_stack(self):
        for i in range(3):
            _cost_ledger.append_cost_row(
                self.book,
                phase="06-phonetics",
                step=f"win-{i:03d}",
                model="claude-sonnet-4-6",
                input_tokens=500,
                output_tokens=250,
            )
        lines = (self.book / "_system" / "cost-ledger.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 3)

    def test_creates_system_dir_if_missing(self):
        _cost_ledger.append_cost_row(
            self.book,
            phase="04-ocr-translate",
            step="(toc)",
            model="claude-opus-4-7",
            input_tokens=100,
            output_tokens=50,
        )
        self.assertTrue((self.book / "_system").is_dir())

    def test_ts_override(self):
        row = _cost_ledger.append_cost_row(
            self.book,
            phase="05-refine-english",
            step="win-001",
            model="claude-opus-4-7",
            input_tokens=100,
            output_tokens=50,
            ts="2026-01-01T00:00:00Z",
        )
        self.assertEqual(row.ts, "2026-01-01T00:00:00Z")

    def test_unknown_model_records_zero_cost_with_warning(self):
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            row = _cost_ledger.append_cost_row(
                self.book,
                phase="05-refine-english",
                step="win-001",
                model="unknown-model-xyz",
                input_tokens=1000,
                output_tokens=500,
            )
        self.assertEqual(row.cost_usd, 0.0)
        self.assertIn("WARNING", buf.getvalue())
        # The row IS still written — operator sees the warning + investigates.
        ledger = self.book / "_system" / "cost-ledger.jsonl"
        self.assertEqual(len(ledger.read_text().splitlines()), 1)


class AppendFromStdoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "book-slug"

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end_stdout_to_ledger(self):
        stdout = "(some output)\nTokens: 2000 in, 800 out, cache: 500 read, 0 create\n"
        row = _cost_ledger.append_from_claude_p_stdout(
            self.book,
            phase="05-refine-english",
            step="win-007",
            model="claude-opus-4-7",
            stdout=stdout,
        )
        self.assertEqual(row.input_tokens, 2000)
        self.assertEqual(row.output_tokens, 800)
        self.assertEqual(row.cache_read, 500)
        self.assertGreater(row.cost_usd, 0)


if __name__ == "__main__":
    unittest.main()
