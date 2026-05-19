#!/usr/bin/env python3
"""Tests for P5.2 — artifact-validation hardening.

P5.2 acceptance (from podcast-plan.yaml):
  • If out_path missing OR file_size == 0, raise typed error with stdout/stderr
    capture (post --permission-mode acceptEdits, this is the P5.1 failure class:
    rc=0 with no file written = a refusal / quota / content-filter issue; not
    retryable; must surface fatally).
  • No silent 'NO ARTIFACT' continuation — every failure surfaces.

Covers:
  • ChunkingError gained stdout/stderr kwargs (parity with AuthoringError)
  • _chunking.py: rc=0-no-artifact raises with stdout/stderr captured
  • _chunking.py: rc!=0 captures stdout AND stderr in failure record (was stderr-only)
  • _authoring.py 07-chapter-design loop: rc=0-no-artifact raises (was continue)
  • _authoring.py 08-enrichment loop: rc=0-no-artifact raises (was continue)
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _chunking  # noqa: E402
import _authoring  # noqa: E402


class ChunkingErrorKwargsTests(unittest.TestCase):
    """ChunkingError must now accept stdout + stderr like AuthoringError does."""

    def test_chunking_error_accepts_stdout_kwarg(self):
        err = _chunking.ChunkingError(
            "boom",
            manual_fallback="retry it",
            stdout="hello stdout",
            stderr="hello stderr",
        )
        self.assertEqual(str(err), "boom")
        self.assertEqual(err.manual_fallback, "retry it")
        self.assertEqual(err.stdout, "hello stdout")
        self.assertEqual(err.stderr, "hello stderr")

    def test_chunking_error_back_compat_minimal(self):
        """Existing call sites that pass only the message still work."""
        err = _chunking.ChunkingError("oops")
        self.assertEqual(err.stdout, "")
        self.assertEqual(err.stderr, "")
        self.assertEqual(err.manual_fallback, "")


class ChunkingArtifactValidationTests(unittest.TestCase):
    """run_windowed — the P5.1 failure class is now fatal, not silent."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.chunks_dir = Path(self.tmp.name) / "_chunks" / "test"

    def tearDown(self):
        self.tmp.cleanup()

    def _prompt_builder(self, body, idx, total, out_path):
        return f"chunk {idx}/{total}"

    def _make_proc(self, rc: int, stdout: str = "", stderr: str = "", *, write_path: Path | None = None):
        """Build a CompletedProcess that optionally writes a file to simulate
        a successful (or unsuccessful) artifact-producing run."""
        if write_path is not None:
            write_path.write_text("WINDOW OUTPUT")
        return mock.MagicMock(returncode=rc, stdout=stdout, stderr=stderr)

    def test_rc_zero_no_artifact_raises_fatal(self):
        """The P5.1 failure mode: rc=0 + no file written → must RAISE, not continue."""
        # Mock subprocess.run so the first (and only) window returns rc=0 but
        # does NOT write the expected out file.
        def fake_run(cmd, **_):
            return self._make_proc(
                rc=0,
                stdout="I cannot help with that request.",
                stderr="",
            )

        with mock.patch.object(_chunking.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(_chunking.ChunkingError) as cm:
                _chunking.run_windowed(
                    text="word " * 100,
                    chunks_dir=self.chunks_dir,
                    prompt_builder=self._prompt_builder,
                    target_words=3000,
                    overlap_words=0,
                    log=lambda _msg: None,
                )

        err = cm.exception
        self.assertIn("rc=0 but produced no artifact", str(err))
        self.assertIn("P5.1 failure class", str(err))
        self.assertEqual(err.stdout, "I cannot help with that request.")
        self.assertIn("DO NOT silently advance", err.manual_fallback)

    def test_rc_nonzero_all_fail_raises_with_summary(self):
        """When EVERY window has rc != 0, ChunkingError raises with the summary."""
        def fake_run(cmd, **_):
            return self._make_proc(rc=1, stdout="bad-stdout", stderr="bad-stderr")

        with mock.patch.object(_chunking.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(_chunking.ChunkingError) as cm:
                _chunking.run_windowed(
                    text="word " * 100,
                    chunks_dir=self.chunks_dir,
                    prompt_builder=self._prompt_builder,
                    target_words=3000,
                    overlap_words=0,
                    log=lambda _msg: None,
                )
        # The summary message captures the failure trail; the rc!=0 path
        # now appends BOTH stdout and stderr to the failure record (P5.2).
        msg = str(cm.exception)
        self.assertIn("all 1 windows failed", msg)
        # The captured failure record format includes "stderr=" and "stdout=".
        self.assertIn("stderr=", msg)
        self.assertIn("stdout=", msg)

    def test_rc_zero_with_artifact_succeeds_silently(self):
        """Happy path — rc=0 AND the artifact is written → no exception."""
        def fake_run(cmd, **_):
            # Determine which window we're on from the chunks_dir contents
            existing = sorted(self.chunks_dir.glob("win-*.in.md"))
            idx = len(existing)
            out_path = self.chunks_dir / f"win-{idx:03d}.out.md"
            return self._make_proc(rc=0, stdout="ok", stderr="", write_path=out_path)

        with mock.patch.object(_chunking.subprocess, "run", side_effect=fake_run):
            paths = _chunking.run_windowed(
                text="word " * 100,
                chunks_dir=self.chunks_dir,
                prompt_builder=self._prompt_builder,
                target_words=3000,
                overlap_words=0,
                log=lambda _msg: None,
            )
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].exists())


class AuthoringErrorAlreadyCapturesTests(unittest.TestCase):
    """AuthoringError already supported stdout/stderr — confirm the contract held."""

    def test_authoring_error_stdout_stderr_kwargs(self):
        err = _authoring.AuthoringError(
            phase="07-chapter-design",
            message="boom",
            stdout="captured-out",
            stderr="captured-err",
        )
        self.assertEqual(err.phase, "07-chapter-design")
        self.assertEqual(err.stdout, "captured-out")
        self.assertEqual(err.stderr, "captured-err")


class AssertArtifactTests(unittest.TestCase):
    """_authoring._assert_artifact must raise with stdout/stderr captured on missing/empty."""

    def test_missing_artifact_raises_with_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.md"
            with self.assertRaises(_authoring.AuthoringError) as cm:
                _authoring._assert_artifact(
                    phase="06-phonetics",
                    path=missing,
                    rc=0,
                    stdout="I cannot",
                    stderr="",
                    manual_fallback="retry",
                )
        err = cm.exception
        self.assertEqual(err.stdout, "I cannot")
        self.assertEqual(err.phase, "06-phonetics")

    def test_empty_artifact_raises_with_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.md"
            empty.write_text("")
            with self.assertRaises(_authoring.AuthoringError) as cm:
                _authoring._assert_artifact(
                    phase="08-enrichment",
                    path=empty,
                    rc=0,
                    stdout="cleared",
                    stderr="oops",
                    manual_fallback="retry",
                )
        self.assertEqual(cm.exception.stderr, "oops")

    def test_nonzero_rc_raises_first(self):
        """rc != 0 short-circuits before the artifact check."""
        with tempfile.TemporaryDirectory() as tmp:
            ok = Path(tmp) / "ok.md"
            ok.write_text("content")
            with self.assertRaises(_authoring.AuthoringError) as cm:
                _authoring._assert_artifact(
                    phase="05-refine-english",
                    path=ok,
                    rc=1,
                    stdout="",
                    stderr="api hiccup",
                    manual_fallback="retry",
                )
            # The rc-nonzero branch fires first.
            self.assertIn("exited rc=1", str(cm.exception))

    def test_nonempty_artifact_with_rc_zero_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok = Path(tmp) / "ok.md"
            ok.write_text("real content")
            # Should return None silently.
            self.assertIsNone(
                _authoring._assert_artifact(
                    phase="05-refine-english",
                    path=ok,
                    rc=0,
                    stdout="",
                    stderr="",
                    manual_fallback="retry",
                )
            )


if __name__ == "__main__":
    unittest.main()
