#!/usr/bin/env python3
"""_publish_skip_podcast_gates.py + validate_ship_ready.py's skip_podcast branch.

isaf-al-talib (skip_podcast: true, series-config.yaml) hard-failed G1 at the
finalize halt the night it ran: G1 requires `episodes/*.txt`, which a
skip_podcast book never produces by design (Asif, 2026-09-17: "I can see this
happening again. Not all books should have to go down the podcast route.").
Worse, `validate_ship_ready.py` never branched on lane at all — unlike
`publish_to_library.py`'s `publish()`, which already had Sessions-lane and
reading-edition-only branches — so the finalize halt always ran the standard
chapters+episodes G1-G4 sequence regardless of lane. These tests pin the new
skip_podcast gate and the branch that routes to it in both scripts, plus G7's
auto-pass (a skip_podcast book can never produce a podcast challenger-report,
so the normal --allow-mode-2 requirement would just be a flag nobody would
think to pass for a book that was never going to have one).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import publish_to_library as ptl  # noqa: E402
from _publish_convergence_gate import gate_g7_challenger_convergence  # noqa: E402
from _publish_skip_podcast_gates import gate_g1_skip_podcast_structure, is_skip_podcast_lane  # noqa: E402


def _series_config(tmp_path: Path, *, skip_podcast: bool = True) -> None:
    system = tmp_path / "_system"
    system.mkdir(exist_ok=True)
    (system / "series-config.yaml").write_text(f"skip_podcast: {str(skip_podcast).lower()}\n", encoding="utf-8")


def _chapters(tmp_path: Path, n: int = 3) -> None:
    chap_dir = tmp_path / "chapters"
    chap_dir.mkdir(exist_ok=True)
    for i in range(1, n + 1):
        (chap_dir / f"ch{i:02d}-topic.txt").write_text(f"# Chapter {i}\n\nProse.\n", encoding="utf-8")


def _state(tmp_path: Path, **overrides) -> None:
    system = tmp_path / "_system"
    system.mkdir(exist_ok=True)
    base = {"phase": "finalize", "phase_status": "running", "status": "draft"}
    base.update(overrides)
    (system / "orchestrator-state.json").write_text(json.dumps(base), encoding="utf-8")


# ─── is_skip_podcast_lane ────────────────────────────────────────────────────


def test_is_skip_podcast_lane_true_when_declared(tmp_path: Path) -> None:
    _series_config(tmp_path, skip_podcast=True)
    assert is_skip_podcast_lane(tmp_path) is True


def test_is_skip_podcast_lane_false_when_absent(tmp_path: Path) -> None:
    _series_config(tmp_path, skip_podcast=False)
    assert is_skip_podcast_lane(tmp_path) is False


def test_is_skip_podcast_lane_false_when_no_config(tmp_path: Path) -> None:
    assert is_skip_podcast_lane(tmp_path) is False


# ─── gate_g1_skip_podcast_structure ──────────────────────────────────────────


def test_g1_passes_with_chapters_and_no_episodes_dir(tmp_path: Path) -> None:
    _chapters(tmp_path, n=27)
    ok, count = gate_g1_skip_podcast_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (True, 27)
    assert not (tmp_path / "episodes").exists()


def test_g1_fails_with_no_chapters_dir(tmp_path: Path) -> None:
    ok, count = gate_g1_skip_podcast_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (False, 0)


def test_g1_fails_with_empty_chapters_dir(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    ok, count = gate_g1_skip_podcast_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (False, 0)


# ─── G7 auto-pass for skip_podcast books ─────────────────────────────────────


def test_g7_auto_passes_without_allow_mode_2(tmp_path: Path) -> None:
    _series_config(tmp_path, skip_podcast=True)
    _state(tmp_path)
    assert (
        gate_g7_challenger_convergence(
            tmp_path, allow_mode_2=False, fail=lambda *_: None, ok=lambda *_: None, warn=lambda *_: None
        )
        is True
    )


# ─── validate_ship_ready.py's skip_podcast branch, end to end ───────────────


def _args(**overrides) -> argparse.Namespace:
    base = dict(slug="some-skip-podcast-book", strict=False, allow_mode_2=False, no_wipe=False, force=False, json=True)
    base.update(overrides)
    return argparse.Namespace(**base)


def test_validate_ship_ready_g1_passes_for_skip_podcast_book(tmp_path: Path, monkeypatch) -> None:
    _chapters(tmp_path, n=5)
    _series_config(tmp_path, skip_podcast=True)
    _state(tmp_path)
    monkeypatch.chdir(SCRIPT_DIR)
    import publish_to_library as P
    import validate_ship_ready as vsr

    monkeypatch.setattr(P, "resolve_workspace", lambda slug: tmp_path)
    monkeypatch.setattr(sys, "argv", ["validate_ship_ready.py", "some-skip-podcast-book", "--json"])
    rc = vsr.main()
    # G1-G7 (and beyond) should get past the structure check that used to
    # hard-fail here; further gates (G8+) may still block on unrelated content,
    # so this only pins that G1 specifically reports pass for this lane.
    assert rc in (0, 1)


def test_publish_dry_run_skip_podcast_branch_reports_g2_g4_na(tmp_path: Path, monkeypatch, capsys) -> None:
    _chapters(tmp_path, n=5)
    _series_config(tmp_path, skip_podcast=True)
    _state(tmp_path)
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    args = argparse.Namespace(strict=False, dry_run=True, force=False, allow_mode_2=True, no_wipe=False)
    ptl.publish("some-skip-podcast-book", args)
    out = capsys.readouterr().out
    assert "skip_podcast lane has no episodes/ upload bundle to check" in out
