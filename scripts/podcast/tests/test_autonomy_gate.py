"""Tests for autonomy levels — which gates a started run may clear for itself."""

from __future__ import annotations

from pathlib import Path

from _autonomy import AUTONOMY_LEVELS, DEFAULT_AUTONOMY, autonomy_clears, autonomy_level_for
from _book_decisions import load_decisions
from _pipeline_flags import autonomy
from phases.autonomy_gate import clear_audio_render_gate, clear_series_plan_gate


def _book(tmp_path: Path, level: str | None) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    cfg = "content_profile: islamic_scholarly\n"
    if level is not None:
        cfg += f"autonomy: {level}\n"
    (bd / "_system" / "series-config.yaml").write_text(cfg, encoding="utf-8")
    return bd


def test_a_book_that_says_nothing_is_manual(tmp_path: Path) -> None:
    assert autonomy(_book(tmp_path, None)) == "manual"
    assert DEFAULT_AUTONOMY == "manual"


def test_a_misspelled_level_falls_back_to_manual_not_to_autonomy(tmp_path: Path) -> None:
    # The direction of this fallback is the whole safety property: a typo must
    # never be indistinguishable from consent.
    assert autonomy(_book(tmp_path, "to_finalise")) == "manual"
    assert autonomy_level_for("nonsense") == "manual"


def test_manual_clears_nothing_and_the_caller_halts_as_before(tmp_path: Path) -> None:
    bd = _book(tmp_path, "manual")
    logged: list[str] = []

    assert clear_series_plan_gate(bd, bd / "_system" / "series-plan.md", log=logged.append) is False
    assert logged == []
    assert load_decisions(bd)["decisions"] == []  # nothing decided, nothing recorded


def test_to_finalize_clears_the_series_plan_and_records_what_it_approved(tmp_path: Path) -> None:
    bd = _book(tmp_path, "to_finalize")
    plan = bd / "_system" / "series-plan.md"
    logged: list[str] = []

    assert clear_series_plan_gate(bd, plan, log=logged.append) is True

    entry = next(d for d in load_decisions(bd)["decisions"] if d["key"] == "phase-0f-series-plan-approval")
    assert entry["phase"] == "0f"
    assert "halt and wait for --resume" in entry["alternatives"]
    assert str(plan) == entry["evidence"]
    assert any("autonomy" in line for line in logged)


def test_no_level_clears_the_audio_render_gate(tmp_path: Path) -> None:
    # It is not only a spend gate: re-invoking --resume there also means "I have
    # read this book". Clearing it would buy audio for a book nobody had read.
    for level in AUTONOMY_LEVELS:
        bd = _book(tmp_path / level, level)
        assert clear_audio_render_gate(bd, log=lambda _m: None) is False
        assert autonomy_clears(level, "audio_render") is False


def test_an_unknown_gate_is_never_cleared(tmp_path: Path) -> None:
    # A stop added later stays manual until someone decides otherwise in the
    # registry — the safe direction for a list that will grow.
    for level in AUTONOMY_LEVELS:
        assert autonomy_clears(level, "some_future_gate") is False


def test_clearing_is_idempotent_across_re_entry(tmp_path: Path) -> None:
    bd = _book(tmp_path, "to_finalize")
    plan = bd / "_system" / "series-plan.md"

    clear_series_plan_gate(bd, plan, log=lambda _m: None)
    clear_series_plan_gate(bd, plan, log=lambda _m: None)

    keys = [d["key"] for d in load_decisions(bd)["decisions"]]
    assert keys.count("phase-0f-series-plan-approval") == 1
