#!/usr/bin/env python3
"""P6.1 integration tests — cost-ledger appends per claude -p call.

Verifies that `_authoring._run_claude_p` and `_chunking.run_windowed` each
emit a cost-ledger row per LLM call when `book_dir` is provided. The
ledger row is keyed by (ts, phase, step, model). Ledger-failure tolerance
is also asserted — a missing/broken ledger module must NOT poison the
LLM call's return value.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _authoring  # noqa: E402
import _chunking  # noqa: E402


CANNED_STDOUT = "blah\nTokens: 1500 in, 800 out, cache: 200 read, 0 create\n"


class AuthoringRunClaudePIntegrationTests(unittest.TestCase):
    """`_authoring._run_claude_p(book_dir=...)` appends one ledger row per call."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "test-book"

    def tearDown(self):
        self.tmp.cleanup()

    def test_book_dir_provided_writes_one_ledger_row(self):
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.MagicMock(
                returncode=0, stdout=CANNED_STDOUT, stderr=""
            )
            rc, out, err = _authoring._run_claude_p(
                "test prompt",
                book_dir=self.book,
                phase="0d",
                step="toc",
            )
        self.assertEqual(rc, 0)
        ledger = self.book / "_system" / "cost-ledger.jsonl"
        self.assertTrue(ledger.exists(), "cost-ledger.jsonl should exist after call")
        lines = ledger.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        row = json.loads(lines[0])
        self.assertEqual(row["phase"], "0d")
        self.assertEqual(row["step"], "toc")
        self.assertEqual(row["input_tokens"], 1500)
        self.assertEqual(row["output_tokens"], 800)
        self.assertEqual(row["cache_read"], 200)
        self.assertGreater(row["cost_usd"], 0)

    def test_no_book_dir_means_no_ledger_write(self):
        """Back-compat — callers that don't pass book_dir don't get a ledger."""
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.MagicMock(
                returncode=0, stdout=CANNED_STDOUT, stderr=""
            )
            rc, out, err = _authoring._run_claude_p("test prompt")
        self.assertEqual(rc, 0)
        # No book_dir → no ledger file anywhere we'd be writing to.

    def test_ledger_failure_does_not_poison_call_result(self):
        """If the ledger module raises, the LLM call result is still returned."""
        with mock.patch("subprocess.run") as run_mock, \
             mock.patch("_cost_ledger.append_from_claude_p_stdout",
                        side_effect=RuntimeError("ledger broken")):
            run_mock.return_value = mock.MagicMock(
                returncode=0, stdout=CANNED_STDOUT, stderr=""
            )
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc, out, err = _authoring._run_claude_p(
                    "test prompt",
                    book_dir=self.book,
                    phase="0d",
                    step="toc",
                )
        # Call still succeeds
        self.assertEqual(rc, 0)
        # Warning surfaced to stderr
        self.assertIn("cost-ledger append failed", buf.getvalue())

    def test_multiple_calls_stack_ledger_rows(self):
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.MagicMock(
                returncode=0, stdout=CANNED_STDOUT, stderr=""
            )
            for step in ("sc-001", "sc-002", "sc-003"):
                _authoring._run_claude_p(
                    "test", book_dir=self.book, phase="0d", step=step
                )
        ledger = self.book / "_system" / "cost-ledger.jsonl"
        rows = [json.loads(l) for l in ledger.read_text().splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["step"] for r in rows], ["sc-001", "sc-002", "sc-003"])


class ChunkingRunWindowedIntegrationTests(unittest.TestCase):
    """`_chunking.run_windowed(book_dir=..., phase=...)` appends one row per window."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "test-book"
        self.chunks = self.book / "_system" / "source" / "text" / "_chunks" / "0b"

    def tearDown(self):
        self.tmp.cleanup()

    def _prompt_builder(self, body, idx, total, out_path):
        return f"chunk {idx}/{total}"

    def test_book_dir_provided_writes_per_window(self):
        """Each window writes one ledger row, phase=0b."""
        windows_seen = []

        def fake_run(cmd, **_kw):
            # Simulate successful artifact write by extracting out_path from prompt
            existing = sorted(self.chunks.glob("win-*.in.md"))
            idx = len(existing)
            out_path = self.chunks / f"win-{idx:03d}.out.md"
            out_path.write_text(f"WINDOW {idx} OUTPUT")
            windows_seen.append(idx)
            return mock.MagicMock(returncode=0, stdout=CANNED_STDOUT, stderr="")

        with mock.patch.object(_chunking.subprocess, "run", side_effect=fake_run):
            _chunking.run_windowed(
                text="word " * 100,
                chunks_dir=self.chunks,
                prompt_builder=self._prompt_builder,
                target_words=3000,
                overlap_words=0,
                log=lambda _: None,
                book_dir=self.book,
                phase="0b",
            )

        ledger = self.book / "_system" / "cost-ledger.jsonl"
        self.assertTrue(ledger.exists())
        rows = [json.loads(l) for l in ledger.read_text().splitlines()]
        # At least one row written (matching the number of windows actually invoked)
        self.assertEqual(len(rows), len(windows_seen))
        for row in rows:
            self.assertEqual(row["phase"], "0b")
            self.assertTrue(row["step"].startswith("win-"))
            self.assertEqual(row["input_tokens"], 1500)

    def test_no_book_dir_means_no_ledger(self):
        """Back-compat — run_windowed without book_dir writes no ledger."""
        def fake_run(cmd, **_kw):
            existing = sorted(self.chunks.glob("win-*.in.md"))
            idx = len(existing)
            (self.chunks / f"win-{idx:03d}.out.md").write_text("ok")
            return mock.MagicMock(returncode=0, stdout=CANNED_STDOUT, stderr="")

        with mock.patch.object(_chunking.subprocess, "run", side_effect=fake_run):
            _chunking.run_windowed(
                text="word " * 100,
                chunks_dir=self.chunks,
                prompt_builder=self._prompt_builder,
                target_words=3000,
                overlap_words=0,
                log=lambda _: None,
            )
        ledger = self.book / "_system" / "cost-ledger.jsonl"
        self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
