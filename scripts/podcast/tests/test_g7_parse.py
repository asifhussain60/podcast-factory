#!/usr/bin/env python3
"""Tests for publish_to_library.py::gate_g7_challenger_convergence.

The G7 gate refuses to publish books that either skipped the convergence
loop (pipeline_mode=non_orchestrated_mode_2) or whose challenger-report.md
verdict is not in {SHIP-READY, SHIP-WITH-CAUTION}. The gate's verdict
parsing must accept both `**Verdict:** X` and `**Verdict: X**` shapes.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import publish_to_library as ptl


class G7GateTests(unittest.TestCase):
    def _workspace(self, state: dict, report_body: str) -> Path:
        ws = Path(tempfile.mkdtemp()) / "fake-book"
        (ws / "_system").mkdir(parents=True)
        (ws / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
        (ws / "_system" / "challenger-report.md").write_text(report_body, encoding="utf-8")
        return ws

    def test_passes_with_canonical_ship_ready(self):
        ws = self._workspace(
            {"pipeline_mode": "orchestrated"},
            "**Verdict:** SHIP-READY\n",
        )
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_passes_with_embedded_keyword_ship_with_caution(self):
        """KaR's actual report shape."""
        ws = self._workspace(
            {"pipeline_mode": "orchestrated"},
            "# title\n\n**Verdict:** SHIP-WITH-CAUTION\n\nbody...\n",
        )
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_blocks_mode_2_without_allow_flag(self):
        ws = self._workspace(
            {"pipeline_mode": "non_orchestrated_mode_2"},
            "**Verdict:** SHIP-READY\n",
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_allows_mode_2_with_allow_flag(self):
        ws = self._workspace(
            {"pipeline_mode": "non_orchestrated_mode_2"},
            "**Verdict:** SHIP-READY\n",
        )
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=True))

    def test_blocks_when_report_has_no_verdict(self):
        ws = self._workspace(
            {"pipeline_mode": "orchestrated"},
            "**Status:** N/A — Mode-2 path.\n",
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_blocks_with_blocked_verdict(self):
        ws = self._workspace(
            {"pipeline_mode": "orchestrated"},
            "**Verdict:** BLOCKED\n",
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def _chapter_timings_workspace(
        self, chapter_timings: dict, human_override=None, report_body: str = "**Verdict:** BLOCKED\n"
    ) -> Path:
        per_chapter = {"chapter_timings": chapter_timings}
        if human_override is not None:
            per_chapter["human_override"] = human_override
        state = {"pipeline_mode": "orchestrated", "phases": {"per-chapter": per_chapter}}
        return self._workspace(state, report_body)

    def test_chapter_timings_passes_despite_stale_blocked_report(self):
        """The exact bug: a stale single-chapter BLOCKED report must not
        override a genuinely-converged book once chapter_timings exists."""
        ws = self._chapter_timings_workspace(
            {
                "ch1": {"verdict": "SHIP-WITH-CAUTION"},
                "ch2": {"verdict": "SHIP-READY"},
            }
        )
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_chapter_timings_passes_with_matching_human_override(self):
        ws = self._chapter_timings_workspace(
            {
                "ch1": {"verdict": "SHIP-WITH-CAUTION"},
                "ch2": {"verdict": "HUMAN-OVERRIDE"},
            },
            human_override={"chapter": "ch2", "reason": "known gap, deferred", "decided_by": "Asif"},
        )
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_chapter_timings_blocks_human_override_verdict_without_record(self):
        ws = self._chapter_timings_workspace(
            {
                "ch1": {"verdict": "SHIP-WITH-CAUTION"},
                "ch2": {"verdict": "HUMAN-OVERRIDE"},
            },
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_chapter_timings_blocks_incomplete_override_record(self):
        ws = self._chapter_timings_workspace(
            {"ch1": {"verdict": "HUMAN-OVERRIDE"}},
            human_override={"chapter": "ch1", "reason": "missing decided_by"},
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_chapter_timings_blocks_bare_failed_chapter(self):
        ws = self._chapter_timings_workspace(
            {
                "ch1": {"verdict": "SHIP-WITH-CAUTION"},
                "ch2": {"verdict": "FAILED"},
            }
        )
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))

    def test_chapter_timings_absent_falls_back_to_report_check(self):
        """No chapter_timings key at all (old/legacy state) -> byte-for-byte
        today's report-file behavior, both passing and failing."""
        ws_pass = self._workspace({"pipeline_mode": "orchestrated"}, "**Verdict:** SHIP-READY\n")
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws_pass, allow_mode_2=False))
        ws_fail = self._workspace({"pipeline_mode": "orchestrated"}, "**Verdict:** BLOCKED\n")
        self.assertFalse(ptl.gate_g7_challenger_convergence(ws_fail, allow_mode_2=False))

    def test_chapter_timings_empty_dict_falls_back_to_report_check(self):
        ws = self._chapter_timings_workspace({}, report_body="**Verdict:** SHIP-READY\n")
        self.assertTrue(ptl.gate_g7_challenger_convergence(ws, allow_mode_2=False))


if __name__ == "__main__":
    unittest.main()
