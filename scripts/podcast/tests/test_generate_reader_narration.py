#!/usr/bin/env python3
"""Tests for generate_reader_narration.py — the Compose tab's on-demand
narration CLI. Mocks reader_narration.render_reader_narration so no network
call (or real Azure spend) happens in the test suite; this module is a thin
status-file wrapper around that function and the tests are scoped to that
wrapping, not to the TTS engine itself (already covered by
test_reader_narration.py).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_reader_narration as grn  # noqa: E402
from reader_narration import RenderSummary  # noqa: E402


def make_book(tmp_path: Path) -> Path:
    book = tmp_path / "content" / "Islamic" / "sample-book"
    (book / "_system").mkdir(parents=True)
    (book / "book").mkdir()
    return book


def status_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "narration-status.json"


def test_generate_writes_running_status_with_pid_before_the_call(tmp_path: Path) -> None:
    """The `pid` field is load-bearing, not decoration: the Astro POST route
    stamps the SAME pid into this file the instant it spawns the process, and
    the GET route's liveness check (`pidAlive`) treats a `running` status with
    no pid as a dead worker. Regression guard for the bug this caught in
    manual testing: an earlier version of `generate()` omitted `pid` from its
    own "running" write, which clobbered the Node-written value and made the
    very next poll report "worker exited without a result" while the worker
    was still running."""
    book = make_book(tmp_path)
    seen_pid_at_call_time = {}

    def fake_render(book_dir: Path) -> RenderSummary:
        # The running-status write must have already landed by the time the
        # engine is invoked, and it must carry a real pid.
        payload = json.loads(status_path(book_dir).read_text())
        seen_pid_at_call_time["pid"] = payload.get("pid")
        seen_pid_at_call_time["state"] = payload.get("state")
        return RenderSummary(outcome="completed", rendered=["ch1"], skipped=[], chars=42)

    with mock.patch.object(grn, "render_reader_narration", fake_render):
        result = grn.generate(book, log=lambda *a, **k: None)

    assert seen_pid_at_call_time["state"] == "running"
    assert seen_pid_at_call_time["pid"] == os.getpid()
    assert result["state"] == "done"
    assert result["rendered"] == ["ch1"]


def test_generate_reports_skipped_with_book_level_reason(tmp_path: Path) -> None:
    book = make_book(tmp_path)

    def fake_render(book_dir: Path) -> RenderSummary:
        return RenderSummary(outcome="skipped", rendered=[], skipped=[], reason="not an Islamic source book")

    with mock.patch.object(grn, "render_reader_narration", fake_render):
        result = grn.generate(book, log=lambda *a, **k: None)

    assert result["state"] == "skipped"
    assert result["reason"] == "not an Islamic source book"


def test_generate_writes_final_status_to_disk(tmp_path: Path) -> None:
    book = make_book(tmp_path)

    def fake_render(book_dir: Path) -> RenderSummary:
        return RenderSummary(outcome="completed", rendered=["intro"], skipped=["outro"], chars=7)

    with mock.patch.object(grn, "render_reader_narration", fake_render):
        grn.generate(book, log=lambda *a, **k: None)

    on_disk = json.loads(status_path(book).read_text())
    assert on_disk["state"] == "done"
    assert on_disk["rendered"] == ["intro"]
    assert on_disk["skipped"] == ["outro"]


def test_main_writes_error_status_and_exits_nonzero_on_exception(tmp_path: Path) -> None:
    book = make_book(tmp_path)

    def boom(_book_dir: Path) -> RenderSummary:
        raise RuntimeError("Azure Speech synthesis exhausted retries")

    argv = ["generate_reader_narration.py", "--book-dir", str(book), "--json"]
    with (
        mock.patch.object(grn, "render_reader_narration", boom),
        mock.patch.object(sys, "argv", argv),
    ):
        rc = grn.main()

    assert rc == 1
    on_disk = json.loads(status_path(book).read_text())
    assert on_disk["state"] == "error"
    assert "exhausted retries" in on_disk["error"]
