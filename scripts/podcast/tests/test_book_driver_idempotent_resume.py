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

import pytest

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


def _stub_downstream(monkeypatch, tmp_calls):
    """Stand in for everything AFTER compose so a test can run the driver to the end."""
    import types

    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)
    monkeypatch.setattr(bd, "phase_git_commit", lambda *a, **kw: None)
    monkeypatch.setattr(_compose_scope, "needs_model_recompose", lambda _d: False)

    def _boom(name):
        def _f(*_a, **_kw):
            raise AssertionError(f"{name} was re-entered by a retry of a LATER phase")

        return _f

    monkeypatch.setattr(bd, "author_phase_book_design", _boom("0book-design"))
    import _book_pipeline_v2

    monkeypatch.setattr(_book_pipeline_v2, "compose_book_v2", _boom("0book-compose"))
    render = types.ModuleType("build_book_pdf")
    render.build_book = lambda *_a, **_kw: tmp_calls.append("render")
    monkeypatch.setitem(sys.modules, "build_book_pdf", render)
    checks = types.ModuleType("_book_render_checks")
    checks.run_render_checks = lambda *_a, **_kw: {}
    monkeypatch.setitem(sys.modules, "_book_render_checks", checks)
    ready = types.ModuleType("validate_book_ready")
    ready.validate_book = lambda *_a, **_kw: {"verdict": "SOUND", "gates": []}
    monkeypatch.setitem(sys.modules, "validate_book_ready", ready)


@pytest.mark.parametrize("render_status", ["failed", "pending", "running", "halted"])
def test_retrying_only_the_render_never_re_enters_design_or_compose(tmp_path, monkeypatch, render_status):
    """The 2026-09-18 incident: `--retry-phase 0book-render` re-entered 0book-compose and
    re-ran the fluency/augment passes over a 33-chapter book — hours of model spend and
    zero textual change. Design and compose finished and nothing governing them changed,
    so only the render (and whatever follows it) may run."""
    d = _book(tmp_path, all_finished=True)
    state = read_state(d)
    state["phases"]["0book-render"] = {"status": render_status}
    (d / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
    calls: list[str] = []
    _stub_downstream(monkeypatch, calls)

    assert bd._drive_book_branch_body(d) == 0

    # The render ran (its final status is decided by post-phase reviews that a stub PDF
    # cannot satisfy); design and compose were never entered and stay as they were.
    assert calls == ["render"]
    phases = read_state(d)["phases"]
    assert phases["0book-design"]["status"] == "completed"
    assert phases["0book-compose"]["status"] == "completed"


def test_an_unfinished_compose_is_still_run_even_though_a_book_md_exists(tmp_path, monkeypatch):
    """Skipping applies only when compose itself FINISHED. A half-written book.md from a
    compose that failed or was killed must not be treated as a finished one."""
    d = _book(tmp_path, all_finished=True)
    state = read_state(d)
    state["phases"]["0book-compose"] = {"status": "failed"}
    (d / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(bd, "_book_branch_enabled", lambda _d: True)
    monkeypatch.setattr(_compose_scope, "needs_model_recompose", lambda _d: False)
    monkeypatch.setattr(bd, "phase_git_commit", lambda *a, **kw: None)
    monkeypatch.setattr(bd, "author_phase_book_design", lambda *_a, **_kw: None)

    def boom(*_a, **_kw):
        raise RuntimeError("compose re-entered, as expected")

    import _book_pipeline_v2

    monkeypatch.setattr(_book_pipeline_v2, "compose_book_v2", boom)
    with pytest.raises(RuntimeError, match="compose re-entered"):
        bd._drive_book_branch_body(d)


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
