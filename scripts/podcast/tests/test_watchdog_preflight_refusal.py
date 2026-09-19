#!/usr/bin/env python3
"""A pre-flight refusal must be LOUD, not a quiet exit.

isaf-al-talib, 2026-09-18: three resumes were refused with "working tree not clean" because
compose wrote new untracked files; the watchdog logged one line and exited, and one stall
lasted ~50 minutes because nothing anywhere said so. The watchdog now writes
`_system/NEEDS-ATTENTION.txt` carrying the orchestrator's own refusal text and the exact fix,
and removes it on the next launch. The marker is itself allowlisted in pre-flight — otherwise
the flag would dirty the tree it is complaining about.
"""

from __future__ import annotations

import sys
import textwrap
import unittest
import unittest.mock
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_watchdog_halt_stops as base  # noqa: E402

REFUSING_ORCHESTRATOR = textwrap.dedent(
    """\
    import sys
    print("preflight: working tree not clean (non-runtime files modified or untracked). Files:")
    print("  ?? content/Islamic/halting-book/book/notes.txt")
    sys.exit(1)
    """
)


class PreflightRefusalIsLoud(unittest.TestCase):
    def setUp(self):
        # No real desktop notification from a test run.
        patcher = unittest.mock.patch.dict("os.environ", {"PF_NO_NOTIFY": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        base.HaltingPhaseStopsTheWatchdog.setUp(self)

    tearDown = base.HaltingPhaseStopsTheWatchdog.tearDown
    _run_watchdog = base.HaltingPhaseStopsTheWatchdog._run_watchdog

    def _use_refusing_stub(self) -> Path:
        (self.repo / "scripts" / "podcast" / "orchestrate_book.py").write_text(REFUSING_ORCHESTRATOR, encoding="utf-8")
        return self.book / "_system" / "NEEDS-ATTENTION.txt"

    def test_a_refusal_writes_an_attention_marker_with_the_reason_and_the_fix(self):
        marker = self._use_refusing_stub()
        rc, log = self._run_watchdog(max_retries=3)
        self.assertEqual(rc, 1, log)
        self.assertTrue(marker.exists(), f"no NEEDS-ATTENTION marker was written:\n{log}")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("working tree not clean", text, "the marker must carry the orchestrator's own reason")
        self.assertIn("notes.txt", text, "and the offending file, so nobody has to go looking")
        self.assertIn("watch_orchestrator.sh " + base.SLUG, text, "and the command that resumes")

    def test_the_marker_is_cleared_when_the_watchdog_starts_again(self):
        marker = self._use_refusing_stub()
        marker.write_text("stale", encoding="utf-8")
        # A stub that succeeds: completes the book, so the watchdog exits 0 and must have cleared it.
        (self.repo / "scripts" / "podcast" / "orchestrate_book.py").write_text(
            textwrap.dedent(
                f"""\
                import json
                from pathlib import Path
                p = Path(__file__).resolve().parents[2] / "content" / "Islamic" / "{base.SLUG}" / "_system" / "orchestrator-state.json"
                s = json.loads(p.read_text()); s["phase"] = "done"; s["phase_status"] = "completed"; p.write_text(json.dumps(s))
                """
            ),
            encoding="utf-8",
        )
        self._run_watchdog(max_retries=1)
        self.assertFalse(marker.exists(), "a stale attention marker must not outlive the problem it reported")

    def test_the_marker_cannot_dirty_the_tree_it_complains_about(self):
        text = (SCRIPTS_PODCAST / "phases" / "preflight.py").read_text(encoding="utf-8").lower()
        self.assertIn('"/_system/needs-attention.txt"', text)


if __name__ == "__main__":
    unittest.main()
