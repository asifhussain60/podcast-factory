#!/usr/bin/env python3
"""Phase 3 regression — orchestrate_work.py pause-between-volumes (the HARD req).

Asserts the sequencer NEVER launches vol-2 without --advance once vol-1 is
complete, and that --advance unblocks exactly one volume. Uses a fake state
reader so no pipeline runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths
import _work_manifest as wm
import orchestrate_work as ow


@pytest.fixture
def two_vol_work(tmp_path, monkeypatch):
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    wd = root / "Islamic" / "asaas"
    for vd in ("vol-01", "vol-02"):
        (wd / vd / "_system").mkdir(parents=True)
    wm.write_manifest(
        wd,
        {
            "work_slug": "asaas",
            "title": "Asaas",
            "volumes": [
                {"order": 1, "slug": "asaas-vol-01", "dir": "vol-01"},
                {"order": 2, "slug": "asaas-vol-02", "dir": "vol-02"},
            ],
        },
    )
    return "asaas"


def _reader(states: dict):
    return lambda slug: states.get(slug)


class TestPause:
    def test_runs_first_volume_initially(self, two_vol_work):
        states = {"asaas-vol-01": {"phase": "preflight"}, "asaas-vol-02": {"phase": "preflight"}}
        a = ow.plan_next_action(two_vol_work, advance=False, state_reader=_reader(states))
        assert a.kind == "run" and a.volume_slug == "asaas-vol-01"

    def test_continues_in_progress_volume_without_advance(self, two_vol_work):
        states = {
            "asaas-vol-01": {"phase": "per-chapter", "phase_status": "running"},
            "asaas-vol-02": {"phase": "preflight"},
        }
        a = ow.plan_next_action(two_vol_work, advance=False, state_reader=_reader(states))
        assert a.kind == "run" and a.volume_slug == "asaas-vol-01"

    def test_pauses_after_vol1_complete_no_advance(self, two_vol_work):
        states = {"asaas-vol-01": {"phase": "done", "status": "published"}, "asaas-vol-02": {"phase": "preflight"}}
        a = ow.plan_next_action(two_vol_work, advance=False, state_reader=_reader(states))
        assert a.kind == "pause-between-volumes"
        assert a.volume_slug == "asaas-vol-02"

    def test_advance_unblocks_next_volume(self, two_vol_work):
        states = {"asaas-vol-01": {"phase": "done", "status": "published"}, "asaas-vol-02": {"phase": "preflight"}}
        a = ow.plan_next_action(two_vol_work, advance=True, state_reader=_reader(states))
        assert a.kind == "run" and a.volume_slug == "asaas-vol-02"

    def test_all_done(self, two_vol_work):
        states = {"asaas-vol-01": {"status": "published"}, "asaas-vol-02": {"status": "published"}}
        a = ow.plan_next_action(two_vol_work, advance=False, state_reader=_reader(states))
        assert a.kind == "all-done"

    def test_run_work_never_ensures_vol2_on_pause(self, two_vol_work, monkeypatch):
        """Integration guard: run_work must NOT shell out to supervise_run for
        vol-2 when paused. We spy on _ensure_volume."""
        states = {"asaas-vol-01": {"phase": "done", "status": "published"}, "asaas-vol-02": {"phase": "preflight"}}
        monkeypatch.setattr(ow, "_read_volume_state", _reader(states))
        ensured = []
        monkeypatch.setattr(ow, "_ensure_volume", lambda slug: ensured.append(slug) or 0)
        rc = ow.run_work(two_vol_work, advance=False)
        assert rc == 0
        assert ensured == []  # vol-2 NEVER launched without --advance


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
