"""Tests for the decision ledger — the forks the pipeline settles on the author's behalf."""

from __future__ import annotations

import json
from pathlib import Path

from _book_decisions import (
    load_decisions,
    open_decisions,
    render_decisions,
    resolve,
    sidecar_path,
)


def _book(tmp_path: Path) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    return bd


def test_resolve_returns_the_default_and_records_it(tmp_path: Path) -> None:
    bd = _book(tmp_path)

    chosen = resolve(
        bd,
        key="chapter-07-qad-alimtu-person",
        default="first person — 'I know your father'",
        alternatives=["second person — 'you know your father'"],
        why="the scan is unvowelled and reads both ways; follows the refined English",
        evidence="raw-extract.md 1160",
        phase="0book-compose",
    )

    assert chosen.startswith("first person")
    entry = load_decisions(bd)["decisions"][0]
    assert entry["source"] == "pipeline default"
    assert entry["override"] == ""
    assert entry["alternatives"] == ["second person — 'you know your father'"]
    assert entry["evidence"] == "raw-extract.md 1160"


def test_an_override_wins_and_is_marked_as_the_authors(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    resolve(bd, key="k", default="the default", alternatives=["the other one"], phase="p")

    # The whole override protocol: edit one field in the sidecar, re-run.
    data = load_decisions(bd)
    data["decisions"][0]["override"] = "the other one"
    sidecar_path(bd).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert resolve(bd, key="k", default="the default", phase="p") == "the other one"
    entry = load_decisions(bd)["decisions"][0]
    assert entry["source"] == "author override"
    assert entry["chose"] == "the other one"
    assert entry["default"] == "the default"  # what the pipeline would have done is not lost


def test_re_running_is_idempotent_and_refreshes_the_reasoning(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    resolve(bd, key="k", default="a", why="first reasoning", phase="p")
    resolve(bd, key="k", default="a", why="better reasoning", phase="p")

    decisions = load_decisions(bd)["decisions"]
    assert len(decisions) == 1  # a convergence loop re-enters constantly
    assert decisions[0]["why"] == "better reasoning"


def test_open_decisions_lists_only_what_the_author_has_not_ruled_on(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    resolve(bd, key="settled", default="a", phase="p")
    resolve(bd, key="still-ours", default="b", phase="p")
    data = load_decisions(bd)
    for d in data["decisions"]:
        if d["key"] == "settled":
            d["override"] = "a"
    sidecar_path(bd).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert [d["key"] for d in open_decisions(bd)] == ["still-ours"]


def test_render_is_empty_when_nothing_was_decided(tmp_path: Path) -> None:
    assert render_decisions(_book(tmp_path)) == ""


def test_render_names_the_choice_the_alternative_and_the_evidence(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    resolve(
        bd,
        key="chapter-07-qad-alimtu-person",
        default="first person",
        alternatives=["second person"],
        why="the scan is unvowelled",
        evidence="raw-extract.md 1160",
        phase="0book-compose",
    )

    out = render_decisions(bd)

    assert "chapter-07-qad-alimtu-person" in out
    assert "pipeline default" in out
    assert "passed over: second person" in out
    assert "raw-extract.md 1160" in out
    assert "override" in out  # the halt tells the author how to overrule it


def test_a_corrupt_sidecar_does_not_take_the_run_down(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    sidecar_path(bd).write_text("{not json at all", encoding="utf-8")

    assert resolve(bd, key="k", default="a", phase="p") == "a"
    assert load_decisions(bd)["decisions"][0]["key"] == "k"
