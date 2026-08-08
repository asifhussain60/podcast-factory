#!/usr/bin/env python3
"""Phase 0g: the dual-auditor sweep over every chapter bundle.

`phase_0g_audit_bundles` had no test naming it. It is worth one for a specific reason:
it is the phase that spends money on TWO model calls per chapter and then decides, from
mtimes alone, whether to spend them again. On a twenty-chapter book a broken freshness
check is forty model calls repeated — the same shape of waste as the 0b window cache
re-paying $8 a book.

The other property pinned here is graceful degradation. The Gemini auditor is optional:
without a key the phase must still run the Claude auditor and report a result, because
0g is informational and must never be able to stop a book at the finalize halt.

No auditor actually runs — both are subprocesses and both are replaced.
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

import phases.bundle_audit as ba  # noqa: E402

FIXES = [
    {"severity": "p0", "note": "fabricated citation"},
    {"severity": "high", "note": "thin enrichment"},
    {"severity": "medium", "note": "wording"},
    {"severity": "low", "note": "nit"},
]


class _FakeProc:
    """Stands in for a Popen'd auditor: writes its report, then exits."""

    def __init__(self, out_path: Path, *, rc: int = 0, body: str | None = None, hang: bool = False) -> None:
        self._out, self.returncode, self._body, self._hang = out_path, rc, body, hang
        self.killed = False

    def communicate(self, timeout=None):
        if self._hang:
            import subprocess

            raise subprocess.TimeoutExpired(cmd="auditor", timeout=timeout or 0)
        if self.returncode == 0:
            self._out.write_text(
                self._body
                if self._body is not None
                else "# Report\n\n```claude-code-fixes\n" + json.dumps(FIXES) + "\n```\n",
                encoding="utf-8",
            )
        return "", ""

    def kill(self) -> None:
        self.killed = True


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "a-book"
        self.draft = self.book_dir / "_system" / "episode-drafts" / "EP01-a-chapter"
        self.draft.mkdir(parents=True)
        (self.draft / "00-framing.md").write_text("framing\n", encoding="utf-8")
        self.procs: list[_FakeProc] = []

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, *, gemini: bool = True, rc: int = 0, body: str | None = None, hang: bool = False) -> dict:
        def _popen(argv, *a, **k):
            out = Path(argv[argv.index("--out") + 1])
            p = _FakeProc(out, rc=rc, body=body, hang=hang)
            self.procs.append(p)
            return p

        with (
            mock.patch.object(ba, "_gemini_key_available", lambda: gemini),
            mock.patch.object(ba.subprocess, "Popen", _popen),
            mock.patch.object(ba, "_info", lambda *_a, **_k: None),
        ):
            return ba.phase_0g_audit_bundles(self.book_dir, ["a-chapter"])


class SeverityRollupTests(_Fixture):
    def test_findings_are_counted_into_p0_p1_p2(self) -> None:
        # Both auditors report the same four findings, so each bucket doubles. The
        # severity words the auditors actually emit — p0/high/medium/low — must all map.
        out = self._run()
        self.assertEqual(out["a-chapter"]["status"], "audited")
        self.assertEqual((out["a-chapter"]["p0"], out["a-chapter"]["p1"], out["a-chapter"]["p2"]), (2, 2, 4))

    def test_only_the_claude_auditor_counts_when_there_is_no_gemini_key(self) -> None:
        out = self._run(gemini=False)
        self.assertEqual((out["a-chapter"]["p0"], out["a-chapter"]["p1"]), (1, 1))
        self.assertIsNone(out["a-chapter"]["gemini_rc"])
        self.assertEqual(len(self.procs), 1, "a second auditor was launched with no key")

    def test_a_report_with_no_fixes_block_contributes_nothing(self) -> None:
        out = self._run(body="# Report\n\nNothing structured here.\n")
        self.assertEqual((out["a-chapter"]["p0"], out["a-chapter"]["p1"], out["a-chapter"]["p2"]), (0, 0, 0))

    def test_unparseable_json_does_not_raise(self) -> None:
        # A truncated model reply must degrade to zero findings, not abort the phase.
        out = self._run(body="# Report\n\n```claude-code-fixes\n[{'not': json\n```\n")
        self.assertEqual(out["a-chapter"]["p0"], 0)


class FreshnessTests(_Fixture):
    """The money question: when does 0g pay for the auditors again?"""

    def test_a_second_run_skips_when_both_reports_are_newer_than_the_framing(self) -> None:
        self._run()
        self.procs.clear()
        out = self._run()
        self.assertEqual(out["a-chapter"]["status"], "skipped-fresh")
        self.assertEqual(self.procs, [], "the auditors were paid for twice on unchanged input")

    def test_a_re_authored_framing_re_audits(self) -> None:
        import os
        import time

        self._run()
        self.procs.clear()
        # Touch the framing into the future: the reports are now stale by mtime.
        future = time.time() + 60
        os.utime(self.draft / "00-framing.md", (future, future))
        out = self._run()
        self.assertEqual(out["a-chapter"]["status"], "audited")
        self.assertEqual(len(self.procs), 2)

    def test_a_claude_only_book_is_not_held_stale_by_a_missing_gemini_report(self) -> None:
        # Without a key there will never be a Gemini report. If freshness required one,
        # every 0g run would re-pay the Claude auditor for the life of the book.
        self._run(gemini=False)
        self.procs.clear()
        out = self._run(gemini=False)
        self.assertEqual(out["a-chapter"]["status"], "skipped-fresh")
        self.assertEqual(self.procs, [])


class DegradationTests(_Fixture):
    def test_a_chapter_with_no_bundle_is_reported_rather_than_crashing(self) -> None:
        with (
            mock.patch.object(ba, "_gemini_key_available", lambda: False),
            mock.patch.object(ba, "_info", lambda *_a, **_k: None),
        ):
            out = ba.phase_0g_audit_bundles(self.book_dir, ["no-such-chapter"])
        self.assertEqual(out["no-such-chapter"]["status"], "missing-bundle")

    def test_a_hanging_auditor_is_killed_and_recorded(self) -> None:
        out = self._run(hang=True)
        self.assertTrue(all(p.killed for p in self.procs), "a hung auditor was left running")
        self.assertEqual(out["a-chapter"]["status"], "audited")
        self.assertEqual(out["a-chapter"]["p0"], 0)

    def test_a_failing_auditor_leaves_the_phase_reporting_a_result(self) -> None:
        out = self._run(rc=2)
        self.assertEqual(out["a-chapter"]["claude_rc"], 2)
        self.assertEqual(out["a-chapter"]["p0"], 0)

    def test_the_summary_table_is_always_written(self) -> None:
        self._run()
        summary = self.book_dir / "audits" / "0g-audit-summary.md"
        self.assertTrue(summary.exists())
        text = summary.read_text(encoding="utf-8")
        self.assertIn("EP01-a-chapter", text)
        self.assertIn("| Episode | Status |", text)

    def test_the_summary_names_a_chapter_that_was_skipped_for_a_missing_bundle(self) -> None:
        # Otherwise a book whose bundles vanished reports an empty, clean-looking table.
        with (
            mock.patch.object(ba, "_gemini_key_available", lambda: False),
            mock.patch.object(ba, "_info", lambda *_a, **_k: None),
        ):
            ba.phase_0g_audit_bundles(self.book_dir, ["no-such-chapter"])
        text = (self.book_dir / "audits" / "0g-audit-summary.md").read_text(encoding="utf-8")
        self.assertIn("no-such-chapter", text)
        self.assertIn("missing-bundle", text)


if __name__ == "__main__":
    unittest.main()
