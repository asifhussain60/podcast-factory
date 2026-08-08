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
        for artifact in (
            "/_system/status-velocity.json",
            "/_system/status-card.txt",
            # Appended by the authoring phases as they call models — same class,
            # found the same way: it stranded the 0d retry an hour after the
            # heartbeat files stranded the 0b one.
            "/_system/model-provenance.jsonl",
        ):
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

    def test_the_observability_artifacts_are_allowlisted(self) -> None:
        # Added 2026-08-08 with the step ledger and the phase reviews, and caught by
        # this exact class of check before either had ever run: the ledger is appended
        # by EVERY step of every phase and a review report is written at every phase
        # completion (~26 per run). Neither is gitignored, so off this list they
        # reproduce the 2026-07-31 deadlock through two new files — a run dirties the
        # tree and the next resume rejects it over output only the run produced.
        self.assertIn(
            '"/_system/step-ledger.jsonl"',
            self.text,
            "the step ledger is appended by every step but would fail the clean-tree gate",
        )
        self.assertIn(
            "_system/phase-reviews/",
            self.text,
            "phase-review reports are written at every phase completion but would fail the clean-tree gate",
        )


class AllowlistIsNotTooBroadTests(unittest.TestCase):
    """The allowlist must not have grown into "ignore everything under _system".

    Widening it far enough to cover the new artifacts by accident would silence the
    gate for genuine source changes too, which is the opposite failure and much
    quieter — a book would resume over uncommitted edits nobody meant to keep.
    """

    def setUp(self) -> None:
        self.text = PREFLIGHT.read_text(encoding="utf-8")

    def test_the_system_directory_is_not_wholesale_allowlisted(self) -> None:
        for too_broad in ('"_system/"', '"/_system/"', '"/_system"'):
            self.assertNotIn(
                too_broad,
                self.text,
                f"{too_broad} would allowlist every _system file, including ones a human edits",
            )

    def test_tracked_source_paths_are_not_allowlisted(self) -> None:
        for never in ("scripts/podcast/_rules.py", "book/book.md", "_system/series-config.yaml"):
            self.assertNotIn(
                f'"{never}"',
                self.text,
                f"{never} is human-authored and must always block a resume when dirty",
            )


if __name__ == "__main__":
    unittest.main()
