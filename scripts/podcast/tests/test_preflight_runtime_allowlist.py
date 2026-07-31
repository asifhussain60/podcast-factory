#!/usr/bin/env python3
"""Nothing the watchdog writes may block the watchdog.

The heartbeat rewrites `_system/status-velocity.json` and `_system/status-card.txt`
every 270s. Neither was on preflight's runtime allowlist, so on 2026-07-31 the
Degrees of Excellence restart died with "working tree not clean" naming a file
that only the watchdog itself had touched — a deadlock a book cannot escape
without a human committing the heartbeat's own output.

This pins the whole class: every per-book artifact the pipeline writes while it
runs must be on the allowlist, or it can strand the next resume.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

PREFLIGHT = SCRIPTS_PODCAST / "phases" / "preflight.py"


class RuntimeAllowlistTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = PREFLIGHT.read_text(encoding="utf-8")

    def test_the_heartbeat_artifacts_are_allowlisted(self) -> None:
        for artifact in ("/_system/status-velocity.json", "/_system/status-card.txt"):
            self.assertIn(
                f'"{artifact}"',
                self.text,
                f"{artifact} is written while the pipeline runs but would fail the clean-tree gate",
            )

    def test_the_state_file_the_driver_rewrites_is_allowlisted(self) -> None:
        # Regression anchor for the pre-existing entries — a trim here re-creates
        # the same deadlock through a different file.
        for artifact in (
            "/_system/orchestrator-state.json",
            "/_system/cost-ledger.jsonl",
            "/_system/watchdog.json",
        ):
            self.assertIn(f'"{artifact}"', self.text, f"{artifact} dropped off the runtime allowlist")


if __name__ == "__main__":
    unittest.main()
