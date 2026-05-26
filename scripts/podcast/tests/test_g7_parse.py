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

import publish_to_library as ptl  # noqa: E402


class G7GateTests(unittest.TestCase):

    def _workspace(self, state: dict, report_body: str) -> Path:
        ws = Path(tempfile.mkdtemp()) / "fake-book"
        (ws / "_system").mkdir(parents=True)
        (ws / "_system" / "orchestrator-state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        (ws / "_system" / "challenger-report.md").write_text(
            report_body, encoding="utf-8"
        )
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


if __name__ == "__main__":
    unittest.main()
