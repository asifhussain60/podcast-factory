#!/usr/bin/env python3
"""Tests for the per-book orchestrator lock in orchestrate_book.py.

The flock is the liveness authority: the kernel releases a dead holder's lock,
so `_try_acquire` can only ever fail against a LIVE holder. Before 2026-09-04 a
lock file whose pid line was missing or unreadable was treated as stale and
unlinked, so a second orchestrator acquired a fresh inode while the first still
held the old one -- two drivers on one book. These tests pin the refusal.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import orchestrate_book as ob

HOLDER = textwrap.dedent(
    """
    import fcntl, os, sys
    fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Deliberately no body: the pid line is what the old code keyed on.
    print("locked", flush=True)
    sys.stdin.readline()  # hold until the test lets go
    """
)


class BookLockTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_locks_dir = ob.LOCKS_DIR
        ob.LOCKS_DIR = Path(self._tmp.name)
        self.slug = "lock-demo"
        self.lock_path = ob.LOCKS_DIR / f"{self.slug}.lock"

    def tearDown(self):
        ob.LOCKS_DIR = self._orig_locks_dir
        self._tmp.cleanup()

    def _start_holder(self) -> subprocess.Popen:
        proc = subprocess.Popen(
            [sys.executable, "-c", HOLDER, str(self.lock_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(proc.wait)
        self.addCleanup(proc.stdin.close)
        self.assertEqual(proc.stdout.readline().strip(), "locked")
        return proc

    def test_live_holder_with_empty_body_is_refused_and_file_survives(self):
        self._start_holder()
        inode_before = self.lock_path.stat().st_ino

        got = ob._acquire_book_lock(self.slug)

        self.assertIsNone(got, "a second orchestrator must be refused while the flock is held")
        self.assertTrue(self.lock_path.exists(), "the holder's lock file must not be unlinked")
        self.assertEqual(self.lock_path.stat().st_ino, inode_before, "same inode: no lock steal")

    def test_unheld_lock_is_acquired_and_stamped(self):
        got = ob._acquire_book_lock(self.slug)
        self.assertIsNotNone(got)
        fd, path = got
        try:
            self.assertEqual(path, self.lock_path)
            self.assertIn(f"pid: {os.getpid()}", self.lock_path.read_text())
        finally:
            ob._release_book_lock(fd, path)
        self.assertFalse(self.lock_path.exists())


if __name__ == "__main__":
    unittest.main()
