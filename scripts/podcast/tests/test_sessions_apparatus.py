#!/usr/bin/env python3
"""`sessions-apparatus` was a step name and a status field with no driver behind
it — the same gap `sessions-articulate` had until 2026-08-11, one step further
down `LANE_STEPS`. Found while planning Surah Al-Fateha's finish line: the state
file could report the step pending forever because nothing in the Sessions lane
ever called `apply_book_apparatus`.

These tests cover the two things worth pinning: the driver REFUSES to run over a
book whose articulation is not `completed` (running the apparatus over
half-rewritten prose would vowel and cite text articulation is about to discard),
and a run that IS allowed stamps `orchestrator-state.json` through the lane's
final step using the SAME writer `ingest.py` already uses — no second state
schema. `apply_book_apparatus` itself is exercised by the compose-path tests
elsewhere; nothing here re-proves what it does, only that this module calls it
under the right conditions and records the result correctly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions import apparatus as app  # noqa: E402
from sessions.ingest import ARTICULATE_STEP, LANE_STEPS  # noqa: E402
from sessions.series import SERIES  # noqa: E402

SLUG = "surah-al-fateha"


@pytest.fixture()
def book_dir(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text("# A Series\n\n## A Chapter\n\nProse.\n", encoding="utf-8")
    return tmp_path


def write_state(book_dir: Path, *, articulate_status: str) -> None:
    phases = {step: {"status": "completed"} for step in LANE_STEPS}
    phases[ARTICULATE_STEP] = {"status": articulate_status}
    (book_dir / "_system" / "orchestrator-state.json").write_text(
        json.dumps({"phase": "sessions-preface", "phases": phases}), encoding="utf-8"
    )


@pytest.mark.parametrize("status", ["running", "pending", None])
def test_refuses_over_unfinished_articulation(book_dir: Path, status) -> None:
    """A `running` or `pending` articulation means the prose on the page is not
    final — apparatus vowelling and citing it now would be immediately
    invalidated the moment articulation touches that chapter again."""
    if status is None:
        write_state(book_dir, articulate_status="completed")
        state_path = book_dir / "_system" / "orchestrator-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        del state["phases"][ARTICULATE_STEP]["status"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
    else:
        write_state(book_dir, articulate_status=status)

    with patch("sessions.apparatus.content_dir", return_value=book_dir):
        with patch("sessions.apparatus.apply_book_apparatus") as mock_apply:
            result = app.run_apparatus(SLUG, log=lambda *_: None)

    assert result["ran"] is False
    mock_apply.assert_not_called()


def test_runs_and_stamps_state_when_articulation_is_complete(book_dir: Path) -> None:
    write_state(book_dir, articulate_status="completed")

    with patch("sessions.apparatus.content_dir", return_value=book_dir):
        with patch("sessions.apparatus.apply_book_apparatus") as mock_apply:
            result = app.run_apparatus(SLUG, log=lambda *_: None)

    assert result["ran"] is True
    mock_apply.assert_called_once()
    assert mock_apply.call_args.args[0] == book_dir

    state = json.loads((book_dir / "_system" / "orchestrator-state.json").read_text(encoding="utf-8"))
    assert state["phase"] == LANE_STEPS[-1]
    assert state["phases"][LANE_STEPS[-1]]["status"] == "completed"
    # The articulate step's own record must survive the rewrite untouched —
    # `_write_state` carries it over rather than deriving it from position.
    assert state["phases"][ARTICULATE_STEP]["status"] == "completed"


def test_force_overrides_an_unfinished_articulation(book_dir: Path) -> None:
    write_state(book_dir, articulate_status="running")

    with patch("sessions.apparatus.content_dir", return_value=book_dir):
        with patch("sessions.apparatus.apply_book_apparatus") as mock_apply:
            result = app.run_apparatus(SLUG, force=True, log=lambda *_: None)

    assert result["ran"] is True
    mock_apply.assert_called_once()


def test_it_reuses_the_lane_writer_not_a_second_schema() -> None:
    """Two answers to "how is this lane's progress recorded" would drift the
    first time either changed — this pins that `apparatus.py` calls the very
    function object `ingest.py` uses, not a re-implementation of it."""
    import sessions.ingest as ingest_mod

    assert app._write_state is ingest_mod._write_state


def test_every_series_slug_is_still_covered() -> None:
    """`run_apparatus` resolves `SERIES[slug]` directly — a slug this module does
    not know about would raise, not silently do nothing."""
    for slug in SERIES:
        assert slug  # sanity: the loop body exercises dict access below
        assert SERIES[slug].slug == slug
