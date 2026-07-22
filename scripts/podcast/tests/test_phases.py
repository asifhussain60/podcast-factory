#!/usr/bin/env python3
"""Drift guard for the canonical orchestrator phase registry.

The single source of truth is ``_progress.PHASES``. This test guards against the
three failure modes that previously coexisted in the codebase:

  1. Parallel hardcoded phase lists drifting apart (orchestrate_book.CANONICAL_PHASES,
     the resume dispatcher, _phases.py all used to re-declare their own copy).
  2. A driver emitting a phase id that update_phase() doesn't recognise — which
     raises ValueError mid-run (this is exactly what hid the missing '0literary'
     and 'publish' entries until the e2e suite caught them).
  3. update_phase() silently accepting an unknown phase name.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _phases
import _progress
import orchestrate_book

# Phase ids that drivers pass to update_phase(). Each MUST be in the registry or
# the orchestrator crashes when that phase runs.
DRIVER_EMITTED_PHASES = (
    "pre-flight",
    "branch",
    "scaffold",
    "0a",
    "0b",
    "0c",
    "0d",
    "0e",
    "0literary",
    "06a",
    "0f",
    "0g",
    "per-chapter",
    "per-chapter-optimize",
    "per-chapter-slides",
    "audio-script",
    "audio-render",
    "finalize",
    "audio-ingest",
    "publish",
    "trainer",
    "merge",
    "done",
)


class PhaseRegistryTests(unittest.TestCase):
    def test_single_source_of_truth(self):
        # orchestrate_book aliases the registry; _phases re-exports it. All three
        # views must be the identical object/sequence — no parallel copies.
        self.assertEqual(orchestrate_book.CANONICAL_PHASES, _progress.PHASES)
        self.assertEqual(_phases.PHASE_ORDER, _progress.PHASES)

    def test_no_duplicate_phases(self):
        self.assertEqual(len(_progress.PHASES), len(set(_progress.PHASES)))

    def test_every_driver_emitted_phase_is_registered(self):
        missing = [p for p in DRIVER_EMITTED_PHASES if p not in _progress.PHASES]
        self.assertEqual(missing, [], f"phases emitted by drivers but absent from PHASES: {missing}")

    def test_update_phase_accepts_every_registered_phase(self):
        # update_phase() validates the phase name against PHASES; every entry must pass.
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            book_dir = Path(d)
            (book_dir / "_system").mkdir()
            _progress.write_state(book_dir, _progress.initial_state("t", "books"))
            for phase in _progress.PHASES:
                try:
                    _progress.update_phase(book_dir, phase=phase, status="running")
                except ValueError as e:  # pragma: no cover - failure path
                    self.fail(f"update_phase rejected registered phase {phase!r}: {e}")

    def test_update_phase_rejects_unknown_phase(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            book_dir = Path(d)
            (book_dir / "_system").mkdir()
            _progress.write_state(book_dir, _progress.initial_state("t", "books"))
            with self.assertRaises(ValueError):
                _progress.update_phase(book_dir, phase="definitely-not-a-phase", status="running")

    def test_key_phase_ordering(self):
        # Anchors that downstream logic and humans rely on, in order.
        order = list(_progress.PHASES)
        self.assertLess(order.index("0e"), order.index("0literary"))
        # audio-ingest runs AFTER the finalize review gate but BEFORE the PDF book
        # branch and publish (it normalizes + transcribes dropped NotebookLM audio
        # so the book is built and published from complete content).
        self.assertLess(order.index("finalize"), order.index("audio-ingest"))
        self.assertLess(order.index("audio-ingest"), order.index("0book-design"))
        self.assertLess(order.index("audio-ingest"), order.index("publish"))
        self.assertLess(order.index("0literary"), order.index("0f"))
        self.assertLess(order.index("finalize"), order.index("publish"))
        self.assertLess(order.index("publish"), order.index("trainer"))
        self.assertEqual(order[0], "pre-flight")
        self.assertEqual(order[-1], "done")


if __name__ == "__main__":
    unittest.main()
