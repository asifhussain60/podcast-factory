"""Intake's branch creation: one implementation, and it can never hang.

`_create_branch` (PDF intake) and `_create_branch_for_work` (audio/work intake) each carried
the same 25-line rev-parse-then-branch block with no timeout on either git call. The shared
tail is now `_ensure_branch`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import intake_book  # noqa: E402


class _Git:
    """Records git calls and answers rev-parse/branch from a script."""

    def __init__(self, exists: bool, create_ok: bool = True):
        self.calls: list[tuple[list[str], dict]] = []
        self.exists, self.create_ok = exists, create_ok

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0 if self.exists else 1, "", "")
        return subprocess.CompletedProcess(cmd, 0 if self.create_ok else 1, "", "fatal: nope")


def test_an_existing_branch_is_kept_and_not_recreated(monkeypatch):
    git = _Git(exists=True)
    monkeypatch.setattr(intake_book.subprocess, "run", git)
    assert intake_book._ensure_branch("Islamic/x") == "Islamic/x"
    assert [c[0][1] for c in git.calls] == ["rev-parse"]


def test_a_missing_branch_is_created_off_develop(monkeypatch):
    git = _Git(exists=False)
    monkeypatch.setattr(intake_book.subprocess, "run", git)
    assert intake_book._ensure_branch("Islamic/x") == "Islamic/x"
    assert git.calls[-1][0] == ["git", "branch", "Islamic/x", "develop"]


def test_a_failed_create_returns_none_so_intake_can_warn(monkeypatch):
    monkeypatch.setattr(intake_book.subprocess, "run", _Git(exists=False, create_ok=False))
    assert intake_book._ensure_branch("Islamic/x") is None


def test_every_git_call_carries_a_timeout(monkeypatch):
    git = _Git(exists=False)
    monkeypatch.setattr(intake_book.subprocess, "run", git)
    intake_book._ensure_branch("Islamic/x")
    assert git.calls and all(kw.get("timeout") for _, kw in git.calls)


def test_both_public_helpers_share_it(monkeypatch):
    git = _Git(exists=True)
    monkeypatch.setattr(intake_book.subprocess, "run", git)
    assert intake_book._create_branch("books", "some-slug")
    assert intake_book._create_branch_for_work("some-slug", profile="islamic_scholarly")
    assert len(git.calls) == 2
