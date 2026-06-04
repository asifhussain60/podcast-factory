#!/usr/bin/env python3
"""Tests for scripts/podcast/_progress.py — orchestrator state machine.

Covers: read_state, write_state, update_phase, initial_state, state_path.
Uses stdlib unittest only — no pytest dependency.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make scripts/podcast/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _progress import (
    initial_state,
    read_state,
    render_status,
    state_path,
    update_phase,
    write_state,
)


class TestStatePath(unittest.TestCase):
    def test_returns_expected_path(self):
        book_dir = Path("/tmp/test-book")
        p = state_path(book_dir)
        self.assertEqual(p, book_dir / "_system" / "orchestrator-state.json")


class TestInitialState(unittest.TestCase):
    def test_required_keys_present(self):
        s = initial_state("test-slug", "books")
        for key in ("phase", "phase_status", "phases", "book_slug", "category"):
            self.assertIn(key, s, f"key {key!r} missing from initial_state")

    def test_slug_and_category_stored(self):
        s = initial_state("kitab-al-riyad", "books")
        self.assertEqual(s["book_slug"], "kitab-al-riyad")
        self.assertEqual(s["category"], "books")

    def test_initial_phase_is_first_phase(self):
        s = initial_state("slug", "books")
        # phase should be set to the first pipeline phase (not None)
        self.assertIsNotNone(s.get("phase"))


class TestWriteAndReadState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.book_dir = self.tmpdir / "test-book"
        self.book_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_roundtrip(self):
        state = initial_state("test-slug", "books")
        write_state(self.book_dir, state)
        loaded = read_state(self.book_dir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["book_slug"], "test-slug")

    def test_read_nonexistent_returns_none(self):
        empty_dir = self.tmpdir / "nonexistent"
        empty_dir.mkdir()
        self.assertIsNone(read_state(empty_dir))

    def test_write_creates_parent_dirs(self):
        nested = self.book_dir / "deep" / "nested"
        state = initial_state("test-slug", "books")
        write_state(nested, state)
        self.assertTrue((nested / "_system" / "orchestrator-state.json").exists())

    def test_write_is_valid_json(self):
        state = initial_state("test-slug", "books")
        write_state(self.book_dir, state)
        p = state_path(self.book_dir)
        parsed = json.loads(p.read_text())
        self.assertIsInstance(parsed, dict)

    def test_write_updates_ts_updated(self):
        state = initial_state("test-slug", "books")
        state.pop("ts_updated", None)
        write_state(self.book_dir, state)
        loaded = read_state(self.book_dir)
        self.assertIn("ts_updated", loaded)

    def test_read_invalid_json_returns_none(self):
        p = state_path(self.book_dir)
        p.parent.mkdir(parents=True)
        p.write_text("not-json-at-all{{{")
        self.assertIsNone(read_state(self.book_dir))


class TestUpdatePhase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.book_dir = self.tmpdir / "test-book"
        self.book_dir.mkdir()
        state = initial_state("test-slug", "books")
        write_state(self.book_dir, state)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _first_phase(self):
        """Return the first phase name from the state."""
        state = read_state(self.book_dir)
        return list(state["phases"].keys())[0] if state["phases"] else state["phase"]

    def test_update_to_running(self):
        phase = read_state(self.book_dir)["phase"]
        updated = update_phase(self.book_dir, phase=phase, status="running")
        self.assertEqual(updated["phase_status"], "running")
        loaded = read_state(self.book_dir)
        self.assertEqual(loaded["phase_status"], "running")

    def test_update_to_completed_sets_last_completed(self):
        phase = read_state(self.book_dir)["phase"]
        update_phase(self.book_dir, phase=phase, status="running")
        updated = update_phase(self.book_dir, phase=phase, status="completed")
        self.assertEqual(updated["last_completed_phase"], phase)

    def test_update_with_error_stores_last_error(self):
        phase = read_state(self.book_dir)["phase"]
        update_phase(self.book_dir, phase=phase, status="running")
        updated = update_phase(
            self.book_dir, phase=phase, status="failed", error="Azure timeout"
        )
        self.assertIsNotNone(updated.get("last_error"))
        self.assertEqual(updated["last_error"]["message"], "Azure timeout")

    def test_completed_clears_last_error(self):
        phase = read_state(self.book_dir)["phase"]
        update_phase(self.book_dir, phase=phase, status="running")
        update_phase(self.book_dir, phase=phase, status="failed", error="boom")
        update_phase(self.book_dir, phase=phase, status="running")
        updated = update_phase(self.book_dir, phase=phase, status="completed")
        self.assertIsNone(updated.get("last_error"))

    def test_unknown_phase_raises(self):
        with self.assertRaises((ValueError, KeyError)):
            update_phase(self.book_dir, phase="phase-does-not-exist", status="running")

    def test_unknown_status_raises(self):
        phase = read_state(self.book_dir)["phase"]
        with self.assertRaises(ValueError):
            update_phase(self.book_dir, phase=phase, status="bogus-status")

    def test_update_phase_requires_existing_state(self):
        empty = self.tmpdir / "empty"
        empty.mkdir()
        phase = read_state(self.book_dir)["phase"]
        with self.assertRaises(RuntimeError):
            update_phase(empty, phase=phase, status="running")

    def test_extras_stored_in_phase_block(self):
        phase = read_state(self.book_dir)["phase"]
        update_phase(
            self.book_dir,
            phase=phase,
            status="running",
            extras={"chapter_count": 12},
        )
        loaded = read_state(self.book_dir)
        self.assertEqual(loaded["phases"][phase].get("chapter_count"), 12)


class TestRenderStatus(unittest.TestCase):
    def test_returns_non_empty_string(self):
        state = initial_state("test-slug", "books")
        rendered = render_status(state)
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)

    def test_includes_slug(self):
        state = initial_state("kitab-al-riyad", "books")
        rendered = render_status(state)
        self.assertIn("kitab-al-riyad", rendered)


if __name__ == "__main__":
    unittest.main()
