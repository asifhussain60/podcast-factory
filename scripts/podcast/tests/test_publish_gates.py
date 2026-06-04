#!/usr/bin/env python3
"""Tests for the publish_to_library G1–G7 gates.

The publish path had ZERO isolated test coverage before this — it relied on the
e2e suite only. These tests cover the structural gates (G1–G3, G6) as pure
functions and, most importantly, guard the dry-run no-mutation invariant: the
G4 build-clean gate must pass --check to build_episode_txt.py when --dry-run is
set, so the gate never rewrites source episodes/*.txt (the bug fixed in the
Wave 1 safety pass).
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import tempfile
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import publish_to_library as pub  # noqa: E402


def _mk(workspace: Path, chapters: list[str], episodes: list[str]) -> None:
    (workspace / "chapters").mkdir(parents=True, exist_ok=True)
    (workspace / "episodes").mkdir(parents=True, exist_ok=True)
    for c in chapters:
        (workspace / "chapters" / c).write_text("chapter body\n")
    for e in episodes:
        (workspace / "episodes" / e).write_text("episode body\n")


def _quiet(fn, *a, **k):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*a, **k)


class G1StructureTests(unittest.TestCase):
    def test_missing_dirs_fail(self):
        with tempfile.TemporaryDirectory() as d:
            ok, ch, ep = _quiet(pub.gate_g1_structure, Path(d))
            self.assertFalse(ok)
            self.assertEqual((ch, ep), ([], []))

    def test_empty_dirs_fail(self):
        with tempfile.TemporaryDirectory() as d:
            _mk(Path(d), [], [])
            ok, ch, ep = _quiet(pub.gate_g1_structure, Path(d))
            self.assertFalse(ok)

    def test_valid_structure_passes(self):
        with tempfile.TemporaryDirectory() as d:
            _mk(Path(d), ["ch01-a.txt"], ["EP01-a.txt"])
            ok, ch, ep = _quiet(pub.gate_g1_structure, Path(d))
            self.assertTrue(ok)
            self.assertEqual(len(ch), 1)
            self.assertEqual(len(ep), 1)


class G2PairsTests(unittest.TestCase):
    def test_matched_pairs_pass(self):
        ch = [Path("ch01-a.txt"), Path("ch02-b.txt")]
        ep = [Path("EP01-a.txt"), Path("EP02-b.txt")]
        self.assertTrue(_quiet(pub.gate_g2_pairs, ch, ep))

    def test_chapter_without_episode_fails(self):
        ch = [Path("ch01-a.txt"), Path("ch02-b.txt")]
        ep = [Path("EP01-a.txt")]
        self.assertFalse(_quiet(pub.gate_g2_pairs, ch, ep))

    def test_unparseable_name_fails(self):
        ch = [Path("chapter-one.txt")]
        ep = [Path("EP01-a.txt")]
        self.assertFalse(_quiet(pub.gate_g2_pairs, ch, ep))


class G3SequentialTests(unittest.TestCase):
    def test_sequential_passes(self):
        ch = [Path("ch01-a.txt"), Path("ch02-b.txt")]
        ep = [Path("EP01-a.txt"), Path("EP02-b.txt")]
        self.assertTrue(_quiet(pub.gate_g3_sequential, ch, ep))

    def test_gap_fails(self):
        ch = [Path("ch01-a.txt"), Path("ch03-c.txt")]
        ep = [Path("EP01-a.txt"), Path("EP03-c.txt")]
        self.assertFalse(_quiet(pub.gate_g3_sequential, ch, ep))

    def test_letter_suffix_fails(self):
        ch = [Path("ch01-a.txt"), Path("ch02a-b.txt")]
        ep = [Path("EP01-a.txt")]
        self.assertFalse(_quiet(pub.gate_g3_sequential, ch, ep))


class G4DryRunInvariantTests(unittest.TestCase):
    """The regression guard for the Wave 1 dry-run mutation bug."""

    def _run_gate(self, dry_run: bool):
        # workspace must be under REPO_ROOT for workspace.relative_to(REPO_ROOT);
        # it need not exist (pure path op). The real builder must exist so the gate
        # doesn't early-return; subprocess.run is mocked so it never actually runs.
        ws = pub.REPO_ROOT / "content" / "drafts" / "books" / "__pubgate_test__"
        eps = [Path("EP01-test.txt")]
        captured = {}
        fake = mock.Mock(stdout="", stderr="", returncode=0)

        def _fake_run(cmd, *a, **k):
            captured["cmd"] = cmd
            return fake

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
             mock.patch.object(pub.subprocess, "run", side_effect=_fake_run):
            result = pub.gate_g4_build_clean(ws, "test", eps, strict=False, dry_run=dry_run)
        return result, captured["cmd"]

    def test_dry_run_passes_check_flag(self):
        ok, cmd = self._run_gate(dry_run=True)
        self.assertTrue(ok)
        self.assertIn("--check", cmd, "dry-run G4 MUST pass --check so it never rewrites source files")

    def test_live_run_omits_check_flag(self):
        ok, cmd = self._run_gate(dry_run=False)
        self.assertTrue(ok)
        self.assertNotIn("--check", cmd, "live publish keeps the rebuild-then-write behavior")


class G6TargetTests(unittest.TestCase):
    def test_nonexistent_target_passes(self):
        with tempfile.TemporaryDirectory() as lib:
            with mock.patch.object(pub, "LIBRARY", Path(lib)):
                target = Path(lib) / "books" / "x"
                self.assertTrue(_quiet(pub.gate_g6_target, target, False))

    def test_target_outside_library_refuses_wipe(self):
        with tempfile.TemporaryDirectory() as lib, tempfile.TemporaryDirectory() as outside:
            with mock.patch.object(pub, "LIBRARY", Path(lib)):
                self.assertFalse(_quiet(pub.gate_g6_target, Path(outside), False))

    def test_symlink_target_refuses_wipe(self):
        with tempfile.TemporaryDirectory() as lib:
            libp = Path(lib)
            real = libp / "real"
            real.mkdir()
            link = libp / "link"
            link.symlink_to(real)
            with mock.patch.object(pub, "LIBRARY", libp):
                self.assertFalse(_quiet(pub.gate_g6_target, link, False))


if __name__ == "__main__":
    unittest.main()
