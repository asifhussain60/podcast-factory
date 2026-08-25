#!/usr/bin/env python3
"""Tests for validate_ship_ready.py::_gate_override.

G13 (arabic-script-in-chapters) has no built-in exception path — it's an
unconditional block for any islamic_scholarly book with zero glossary Arabic
terms. _gate_override lets a specific, attributed human decision recorded on
the book's own orchestrator-state.json exempt one named gate, without
inferring anything the state file doesn't explicitly say.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import validate_ship_ready as vsr


class GateOverrideTests(unittest.TestCase):
    def _workspace(self, state: dict | None) -> Path:
        ws = Path(tempfile.mkdtemp()) / "fake-book"
        (ws / "_system").mkdir(parents=True)
        if state is not None:
            (ws / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
        return ws

    def test_no_state_file_returns_none(self):
        ws = self._workspace(None)
        self.assertIsNone(vsr._gate_override(ws, "G13"))

    def test_no_human_overrides_key_returns_none(self):
        ws = self._workspace({})
        self.assertIsNone(vsr._gate_override(ws, "G13"))

    def test_matching_override_returned(self):
        ws = self._workspace(
            {
                "human_overrides": [
                    {"gate": "G13", "reason": "known gap, deferred", "decided_by": "Asif", "decided_at": "x"},
                ]
            }
        )
        override = vsr._gate_override(ws, "G13")
        self.assertIsNotNone(override)
        self.assertEqual(override["decided_by"], "Asif")

    def test_override_for_different_gate_not_matched(self):
        ws = self._workspace({"human_overrides": [{"gate": "G7", "reason": "x", "decided_by": "Asif"}]})
        self.assertIsNone(vsr._gate_override(ws, "G13"))

    def test_incomplete_override_rejected(self):
        """Missing reason or decided_by never counts — never inferred."""
        ws = self._workspace({"human_overrides": [{"gate": "G13", "reason": "x"}]})
        self.assertIsNone(vsr._gate_override(ws, "G13"))
        ws2 = self._workspace({"human_overrides": [{"gate": "G13", "decided_by": "Asif"}]})
        self.assertIsNone(vsr._gate_override(ws2, "G13"))

    def test_malformed_state_file_returns_none(self):
        ws = Path(tempfile.mkdtemp()) / "fake-book"
        (ws / "_system").mkdir(parents=True)
        (ws / "_system" / "orchestrator-state.json").write_text("not json", encoding="utf-8")
        self.assertIsNone(vsr._gate_override(ws, "G13"))


if __name__ == "__main__":
    unittest.main()
