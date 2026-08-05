"""A crash must never leave a phase pinned at "running".

The live incident, 2026-07-21: `0book-render` produced its PDF, the process then
died on something that was not an `AuthoringError`, and the state file kept
`status: "running"` with no `last_error`. Nothing downstream could tell a dead
run from a live one, and recovery had to wait out the 900-second staleness window
before a resume would touch the book at all.

`_drive_book_branch` now wraps its body: whatever escapes, the phase that was
running is recorded as failed with the exception on it before it propagates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "phases"))

import phases.book_driver as bd  # noqa: E402
from _progress import read_state  # noqa: E402


def _book(tmp_path: Path) -> Path:
    d = tmp_path / "slug"
    (d / "_system").mkdir(parents=True)
    (d / "book").mkdir(parents=True)
    (d / "_system" / "orchestrator-state.json").write_text(json.dumps({"slug": "slug", "phases": {}}), encoding="utf-8")
    return d


def _running_phases(d: Path) -> list[str]:
    return [k for k, v in (read_state(d).get("phases") or {}).items() if (v or {}).get("status") == "running"]


def _failed(d: Path) -> dict:
    return {k: v for k, v in (read_state(d).get("phases") or {}).items() if (v or {}).get("status") == "failed"}


def _last_error(d: Path) -> dict:
    """update_phase records the text at the TOP level, not on the phase block."""
    return read_state(d).get("last_error") or {}


def test_a_non_authoring_crash_marks_the_running_phase_failed(tmp_path, monkeypatch) -> None:
    d = _book(tmp_path)

    def boom(book_dir):
        from _progress import update_phase

        update_phase(book_dir, phase="0book-compose", status="running")
        raise json.JSONDecodeError("bad toc", "", 0)

    monkeypatch.setattr(bd, "_drive_book_branch_body", boom)

    with pytest.raises(json.JSONDecodeError):
        bd._drive_book_branch(d)

    assert _running_phases(d) == [], "a dead phase must not still read as running"
    assert "0book-compose" in _failed(d)
    err = _last_error(d)
    assert err.get("phase") == "0book-compose"
    assert "JSONDecodeError" in (err.get("message") or "")


def test_a_keyboard_interrupt_is_recorded_too(tmp_path, monkeypatch) -> None:
    """BaseException, not Exception — a Ctrl-C mid-compose used to pin the phase."""
    d = _book(tmp_path)

    def boom(book_dir):
        from _progress import update_phase

        update_phase(book_dir, phase="0book-render", status="running")
        raise KeyboardInterrupt()

    monkeypatch.setattr(bd, "_drive_book_branch_body", boom)

    with pytest.raises(KeyboardInterrupt):
        bd._drive_book_branch(d)

    assert _running_phases(d) == []
    assert "0book-render" in _failed(d)


def test_an_authoring_error_is_left_to_the_bodys_own_handlers(tmp_path, monkeypatch) -> None:
    """Those handlers already record a failure WITH its manual_fallback; the
    wrapper must not overwrite that with a poorer record."""
    from _authoring import AuthoringError

    d = _book(tmp_path)

    def boom(book_dir):
        raise AuthoringError("0book-compose", "handled elsewhere")

    monkeypatch.setattr(bd, "_drive_book_branch_body", boom)

    with pytest.raises(AuthoringError):
        bd._drive_book_branch(d)


def test_a_clean_run_is_untouched(tmp_path, monkeypatch) -> None:
    d = _book(tmp_path)
    monkeypatch.setattr(bd, "_drive_book_branch_body", lambda book_dir: 0)
    assert bd._drive_book_branch(d) == 0
    assert _failed(d) == {}


def test_the_recorder_never_masks_the_real_exception(tmp_path, monkeypatch) -> None:
    """If reading state fails too, the ORIGINAL error is what must surface."""
    d = _book(tmp_path)

    def boom(book_dir):
        raise RuntimeError("the real problem")

    monkeypatch.setattr(bd, "_drive_book_branch_body", boom)
    monkeypatch.setattr(bd, "read_state", lambda _d: (_ for _ in ()).throw(OSError("state unreadable")))

    with pytest.raises(RuntimeError, match="the real problem"):
        bd._drive_book_branch(d)
