#!/usr/bin/env python3
"""A failed Podcast Factory Library deploy is recorded, not just printed.

`_publish_downstream.deliver` is non-fatal by design: a book that passed every
gate is published in the repo whether or not Cloudflare answered. That rule is
right and stays. What was wrong is that the failure went nowhere but a warning
line in a subprocess's stdout — `publish_to_library.py` returned 0, the driver
marked the publish phase completed, committed, trained and merged, and nothing
in the state file said the site never got the book.

Pinned here: `deliver` returns a structured outcome; `publish()` writes it into
the publish phase's block of `orchestrator-state.json`; the driver's own
`update_phase(... completed)` keeps it; and the driver can turn it into the
warning it prints. The exit code stays 0 throughout — the book IS published.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _publish_downstream as downstream  # noqa: E402
import publish_to_library as pub  # noqa: E402
from _progress import initial_state, read_state, update_phase, write_state  # noqa: E402
from phases.publish_driver import listener_deploy_warning  # noqa: E402

RETRY = "scripts/podcast/deploy_listener.sh the-book"


def failing_run(argv, check=False, **_kw):
    raise subprocess.CalledProcessError(1, argv)


def passing_run(argv, check=False, **_kw):
    return None


def fake_subprocess(run):
    """Only the deploy's own `subprocess.run` — the real module is shared with
    every other caller in the process, git_sha included."""
    return SimpleNamespace(run=run, CalledProcessError=subprocess.CalledProcessError)


def test_a_failed_deploy_comes_back_as_a_structured_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(downstream, "subprocess", fake_subprocess(failing_run))
    warned: list[str] = []
    outcome = downstream.deliver("the-book", SimpleNamespace(skip_export=True), info=lambda m: None, warn=warned.append)
    result = outcome["listener_deploy"]
    assert result["status"] == "failed"
    assert "returned non-zero" in result["reason"]
    assert result["retry"] == RETRY
    assert any("listener deploy failed" in w for w in warned), "the warning line still prints"


def test_a_deploy_that_ran_reports_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(downstream, "subprocess", fake_subprocess(passing_run))
    outcome = downstream.deliver("the-book", SimpleNamespace(skip_export=True), info=lambda m: None, warn=print)
    assert outcome["listener_deploy"] == {"status": "ok"}


def test_skipping_the_deploy_is_not_a_failure() -> None:
    outcome = downstream.deliver(
        "the-book", SimpleNamespace(skip_export=True, skip_listener=True), info=lambda m: None, warn=print
    )
    assert outcome["listener_deploy"]["status"] == "skipped"


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A book whose gates all pass, so `publish()` reaches the deliveries."""
    directory = tmp_path / "the-book"
    (directory / "_system").mkdir(parents=True)
    write_state(directory, initial_state("the-book", "sessions"))
    monkeypatch.setenv("PODCAST_PHASE_GATES", "off")
    monkeypatch.setattr(pub, "REPO_ROOT", tmp_path)  # publish() logs the workspace relative to it
    monkeypatch.setattr(pub, "resolve_workspace", lambda slug: directory)
    monkeypatch.setattr(pub, "is_sessions_lane", lambda ws: True)
    monkeypatch.setattr(pub, "gate_g1_sessions_structure", lambda ws, fail, ok: (True, 3))
    monkeypatch.setattr(pub, "gate_g5_sessions_state", lambda ws, force, fail, ok: True)
    monkeypatch.setattr(pub, "gate_g7_challenger_convergence", lambda ws, allow: True)
    monkeypatch.setattr(pub, "_update_meta_publication_status", lambda ws: None)
    monkeypatch.setattr(pub, "update_catalog", lambda slug, n, sha: None)
    monkeypatch.setattr(pub, "git_sha", lambda: "0000000")
    import hydrate_search_index

    monkeypatch.setattr(hydrate_search_index, "hydrate", lambda slugs, log: {"chapters": 0})
    return directory


ARGS = SimpleNamespace(dry_run=False, strict=False, force=False, allow_mode_2=False, skip_export=True)


def test_publish_records_the_failed_deploy_and_still_returns_zero(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(downstream, "subprocess", fake_subprocess(failing_run))

    assert pub.publish("the-book", ARGS) == 0

    state = read_state(workspace)
    assert state["status"] == "published", "the book is published in the repo regardless"
    marker = state["phases"]["publish"]["listener_deploy"]
    assert marker["status"] == "failed"
    assert marker["retry"] == RETRY


def test_the_marker_survives_the_driver_marking_the_phase_completed(workspace: Path, monkeypatch) -> None:
    """The driver runs publish_to_library as a subprocess, then calls
    update_phase(completed) itself. That call must not wipe what the subprocess
    recorded, or the warning would have nothing to read."""
    monkeypatch.setattr(downstream, "subprocess", fake_subprocess(failing_run))
    update_phase(workspace, phase="publish", status="running")
    pub.publish("the-book", ARGS)
    update_phase(workspace, phase="publish", status="completed")

    state = read_state(workspace)
    assert state["phases"]["publish"]["status"] == "completed"
    assert state["phases"]["publish"]["listener_deploy"]["status"] == "failed"
    warning = listener_deploy_warning(workspace)
    assert warning is not None and RETRY in warning


def test_no_warning_when_the_deploy_went_through(workspace: Path, monkeypatch) -> None:
    monkeypatch.setattr(downstream, "subprocess", fake_subprocess(passing_run))
    pub.publish("the-book", ARGS)
    assert listener_deploy_warning(workspace) is None


def test_no_warning_for_a_book_that_never_recorded_an_outcome(workspace: Path) -> None:
    assert listener_deploy_warning(workspace) is None
