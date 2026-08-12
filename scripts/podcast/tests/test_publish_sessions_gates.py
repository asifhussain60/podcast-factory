#!/usr/bin/env python3
"""_publish_sessions_gates.py + publish_to_library.py's Sessions-lane branch.

A Sessions-lane book never produces chapters/*.txt or episodes/*.txt, so
publish_to_library.py's G1 (structure) and G5 (state checkpoint) hard-failed
on both books in this lane the day they existed — reproduced live via
`--dry-run` before this fix. These tests pin the Sessions-lane equivalents
and the branch in publish() that routes to them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import publish_to_library as ptl  # noqa: E402
from _publish_sessions_gates import (  # noqa: E402
    gate_g1_sessions_structure,
    gate_g5_sessions_state,
    is_sessions_lane,
)


def _state(tmp_path: Path, **overrides) -> None:
    system = tmp_path / "_system"
    system.mkdir(exist_ok=True)
    base = {
        "pipeline_mode": "sessions_lane",
        "phase": "sessions-preface",
        "phases": {"sessions-apparatus": {"status": "pending"}},
        "status": "draft",
    }
    base.update(overrides)
    (system / "orchestrator-state.json").write_text(json.dumps(base), encoding="utf-8")


def _real_structure(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text("## A Chapter\n\nSome prose.\n", encoding="utf-8")
    (tmp_path / "chapter-contracts").mkdir()
    (tmp_path / "chapter-contracts" / "ep01-book.yml").write_text("episode_number: 1\n", encoding="utf-8")
    (tmp_path / "m4a" / "Episodes").mkdir(parents=True)
    (tmp_path / "m4a" / "Episodes" / "ep01.mp3").write_bytes(b"\x00")


# ─── is_sessions_lane ───────────────────────────────────────────────────────


def test_is_sessions_lane_true_when_declared(tmp_path: Path) -> None:
    _state(tmp_path)
    assert is_sessions_lane(tmp_path) is True


def test_is_sessions_lane_false_for_an_orchestrated_book(tmp_path: Path) -> None:
    _state(tmp_path, pipeline_mode="orchestrated")
    assert is_sessions_lane(tmp_path) is False


def test_is_sessions_lane_false_when_no_state_file(tmp_path: Path) -> None:
    assert is_sessions_lane(tmp_path) is False


# ─── gate_g1_sessions_structure ─────────────────────────────────────────────


def test_g1_passes_with_book_md_contracts_and_audio(tmp_path: Path) -> None:
    _real_structure(tmp_path)
    ok, count = gate_g1_sessions_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert ok is True
    assert count == 1


def test_g1_fails_with_no_book_md(tmp_path: Path) -> None:
    (tmp_path / "chapter-contracts").mkdir()
    (tmp_path / "chapter-contracts" / "ep01-book.yml").write_text("x", encoding="utf-8")
    ok, count = gate_g1_sessions_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (False, 0)


def test_g1_fails_with_no_chapter_contracts(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text("## A Chapter\n\nProse.\n", encoding="utf-8")
    ok, count = gate_g1_sessions_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (False, 0)


def test_g1_fails_with_no_episode_audio(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text("## A Chapter\n\nProse.\n", encoding="utf-8")
    (tmp_path / "chapter-contracts").mkdir()
    (tmp_path / "chapter-contracts" / "ep01-book.yml").write_text("x", encoding="utf-8")
    ok, count = gate_g1_sessions_structure(tmp_path, fail=lambda *_: None, ok=lambda *_: None)
    assert (ok, count) == (False, 0)


# ─── gate_g5_sessions_state ─────────────────────────────────────────────────


def test_g5_passes_when_apparatus_completed(tmp_path: Path) -> None:
    _state(tmp_path, phases={"sessions-apparatus": {"status": "completed"}})
    assert gate_g5_sessions_state(tmp_path, force=False, fail=lambda *_: None, ok=lambda *_: None) is True


def test_g5_fails_when_apparatus_pending(tmp_path: Path) -> None:
    _state(tmp_path)  # default: sessions-apparatus pending
    assert gate_g5_sessions_state(tmp_path, force=False, fail=lambda *_: None, ok=lambda *_: None) is False


def test_g5_force_bypasses_regardless_of_state(tmp_path: Path) -> None:
    assert gate_g5_sessions_state(tmp_path, force=True, fail=lambda *_: None, ok=lambda *_: None) is True


def test_g5_fails_with_no_state_file(tmp_path: Path) -> None:
    assert gate_g5_sessions_state(tmp_path, force=False, fail=lambda *_: None, ok=lambda *_: None) is False


# ─── publish()'s Sessions-lane branch, end to end (dry-run only) ──────────


def _args(**overrides) -> argparse.Namespace:
    base = dict(strict=False, dry_run=True, force=False, allow_mode_2=False, no_wipe=False)
    base.update(overrides)
    return argparse.Namespace(**base)


def test_publish_dry_run_passes_all_gates_for_a_finished_sessions_book(tmp_path: Path, monkeypatch) -> None:
    _real_structure(tmp_path)
    _state(tmp_path, phases={"sessions-apparatus": {"status": "completed"}})
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    rc = ptl.publish("some-lecture", _args(allow_mode_2=True))
    assert rc == 0


def test_publish_dry_run_blocks_on_g5_when_apparatus_not_done(tmp_path: Path, monkeypatch) -> None:
    _real_structure(tmp_path)
    _state(tmp_path)  # sessions-apparatus still pending
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    rc = ptl.publish("some-lecture", _args(allow_mode_2=True))
    assert rc == 1


def test_publish_dry_run_blocks_on_g7_without_allow_mode_2(tmp_path: Path, monkeypatch) -> None:
    _real_structure(tmp_path)
    _state(tmp_path, phases={"sessions-apparatus": {"status": "completed"}})
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    rc = ptl.publish("some-lecture", _args())  # no --allow-mode-2
    assert rc == 1


def test_publish_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    _real_structure(tmp_path)
    _state(tmp_path, phases={"sessions-apparatus": {"status": "completed"}})
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    before = (tmp_path / "book" / "book.md").read_text(encoding="utf-8")
    ptl.publish("some-lecture", _args(allow_mode_2=True))
    after = (tmp_path / "book" / "book.md").read_text(encoding="utf-8")
    assert before == after


def test_orchestrated_book_still_uses_the_original_g1_g5_gates(tmp_path: Path, monkeypatch) -> None:
    """A non-Sessions book with no chapters/episodes txt still fails the
    ORIGINAL G1 — the branch must not accidentally widen who gets the new,
    looser-looking structure check."""
    (tmp_path / "_system").mkdir()
    (tmp_path / "_system" / "orchestrator-state.json").write_text(
        json.dumps({"pipeline_mode": "orchestrated", "phase": "done"}), encoding="utf-8"
    )
    monkeypatch.setattr(ptl, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ptl, "resolve_workspace", lambda slug: tmp_path)
    rc = ptl.publish("some-orchestrated-book", _args())
    assert rc == 1
