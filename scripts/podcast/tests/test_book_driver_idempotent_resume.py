"""A resume must not re-run the whole design->compose->render chain when the
book already finished it and nothing model-governing has changed since.

Regression test for a live incident on `sharh-al-masail-ghulam-hussain`
(2026-08-18): three separate resumes each re-triggered `_drive_book_branch_body`
from 0book-design, restarting the fluency/augment model passes over an
already-complete, already-validated book. Two of the three were caught
mid-rewrite before the result could be committed. `_compose_scope.needs_model_recompose`
already existed to answer exactly this question but was only ever used to
print an advisory (see `_compose_scope.py` and the spiritual-ethos incident
it documents) — never to actually skip the re-entry.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "phases"))

import _compose_scope  # noqa: E402
import phases.book_driver as bd  # noqa: E402
from _progress import read_state, update_phase  # noqa: E402


def _book(tmp_path: Path, *, all_finished: bool) -> Path:
    d = tmp_path / "slug"
    (d / "_system").mkdir(parents=True)
    (d / "book").mkdir(parents=True)
    (d / "book" / "book.md").write_text("# Book\n", encoding="utf-8")
    phases = {}
    if all_finished:
        for ph in bd._BOOK_PHASES:
            phases[ph] = {"status": "completed"}
    (d / "_system" / "orchestrator-state.json").write_text(
        json.dumps({"slug": "slug", "phases": phases}), encoding="utf-8"
    )
    return d


def test_skips_re_entry_when_everything_already_finished_and_nothing_changed(tmp_path, monkeypatch):
    d = _book(tmp_path, all_finished=True)
    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)
    monkeypatch.setattr(_compose_scope, "needs_model_recompose", lambda _d: False)
    monkeypatch.setattr(bd, "needs_model_recompose", lambda _d: False, raising=False)

    called = []
    monkeypatch.setattr(
        bd,
        "update_phase",
        lambda *a, **kw: called.append(kw.get("phase")) or update_phase(*a, **kw),
    )

    result = bd._drive_book_branch_body(d)

    assert result == 0
    # 0book-design would be the first phase touched by a real re-entry.
    assert "0book-design" not in called


def test_still_runs_when_a_phase_never_finished(tmp_path, monkeypatch):
    """Only SOME phases finished (e.g. 0book-render never ran) — must not skip."""
    d = _book(tmp_path, all_finished=True)
    state = read_state(d)
    state["phases"]["0book-render"] = {"status": "failed"}
    (d / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")

    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)

    # Fail fast the moment it actually tries to re-enter 0book-design, proving
    # the skip did NOT fire — a real author call would need heavier fixtures.
    def boom(*_a, **_kw):
        raise RuntimeError("real re-entry attempted, as expected")

    monkeypatch.setattr(bd, "author_phase_book_design", boom)

    try:
        bd._drive_book_branch_body(d)
    except RuntimeError as e:
        assert "real re-entry attempted" in str(e)
    else:
        raise AssertionError("expected the driver to actually re-enter 0book-design")


def test_still_runs_when_something_model_governing_changed(tmp_path, monkeypatch):
    """All phases finished, but the source (or a governing module) changed since —
    a genuine recompose is still needed, so the skip must not fire."""
    d = _book(tmp_path, all_finished=True)
    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)
    monkeypatch.setattr(_compose_scope, "needs_model_recompose", lambda _d: True)

    def boom(*_a, **_kw):
        raise RuntimeError("real re-entry attempted, as expected")

    monkeypatch.setattr(bd, "author_phase_book_design", boom)

    try:
        bd._drive_book_branch_body(d)
    except RuntimeError as e:
        assert "real re-entry attempted" in str(e)
    else:
        raise AssertionError("expected the driver to actually re-enter 0book-design")


def test_still_runs_when_book_md_is_missing(tmp_path, monkeypatch):
    d = _book(tmp_path, all_finished=True)
    (d / "book" / "book.md").unlink()
    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)

    def boom(*_a, **_kw):
        raise RuntimeError("real re-entry attempted, as expected")

    monkeypatch.setattr(bd, "author_phase_book_design", boom)

    try:
        bd._drive_book_branch_body(d)
    except RuntimeError as e:
        assert "real re-entry attempted" in str(e)
    else:
        raise AssertionError("expected the driver to actually re-enter 0book-design")
