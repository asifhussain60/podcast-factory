#!/usr/bin/env python3
"""Phase 6 regression — intake_preflight cost/time estimator.

The estimate is chapter_count × historical mean, capped per-chapter by the rail
Phase 3 enforces, and surfaces the caps in effect. Pure — no LLM, no launch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths  # noqa: E402
import intake_preflight as pf  # noqa: E402


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    return root


def _book_with_timings(root: Path, slug: str, timings: dict) -> None:
    bd = root / "Islamic" / slug / "_system"
    bd.mkdir(parents=True)
    (bd / "orchestrator-state.json").write_text(json.dumps({
        "status": "draft",
        "phases": {"per-chapter": {"chapter_timings": timings}},
    }), encoding="utf-8")


class TestEstimate:
    def test_explicit_means(self):
        est = pf.estimate(chapter_count=10, mean_cost_usd=3.0, mean_sec=3600,
                          per_chapter_cost_cap_usd=5.0)
        assert est["projected_cost_usd"] == 30.0
        assert est["projected_sec"] == 36000
        assert est["projected_human"] == "10h"

    def test_per_chapter_cap_bounds_estimate(self):
        # mean above the cap → the cap is used so we never over-promise spend.
        est = pf.estimate(chapter_count=4, mean_cost_usd=99.0, per_chapter_cost_cap_usd=5.0)
        assert est["projected_cost_usd"] == 20.0  # 4 × $5 cap

    def test_caps_surfaced(self):
        est = pf.estimate(chapter_count=1, mean_cost_usd=1.0,
                          per_chapter_cost_cap_usd=5.0, book_cost_cap_usd=40.0)
        assert est["caps"]["book_cost_cap_active"] is True
        assert est["caps"]["book_cost_cap_usd"] == 40.0

    def test_zero_chapters(self):
        est = pf.estimate(chapter_count=0, mean_cost_usd=3.0, mean_sec=10)
        assert est["projected_cost_usd"] == 0.0 and est["projected_sec"] == 0

    def test_negative_chapters_rejected(self):
        with pytest.raises(ValueError):
            pf.estimate(chapter_count=-1)


class TestHistoricalMeans:
    def test_falls_back_to_defaults_when_no_history(self, temp_root):
        c, s, n = pf.historical_means()
        assert c == pf.DEFAULT_PER_CHAPTER_COST_USD
        assert s == pf.DEFAULT_PER_CHAPTER_SEC
        assert n == 0

    def test_averages_recorded_chapters(self, temp_root):
        _book_with_timings(temp_root, "book-a", {
            "ch01": {"cost_usd": 2.0, "duration_sec": 1000, "verdict": "SHIP-READY"},
            "ch02": {"cost_usd": 4.0, "duration_sec": 3000, "verdict": "SHIP-READY"},
        })
        c, s, n = pf.historical_means()
        assert c == 3.0           # (2+4)/2
        assert s == 2000.0        # (1000+3000)/2
        assert n == 2

    def test_skips_zero_cost_partial_chapters(self, temp_root):
        _book_with_timings(temp_root, "book-a", {
            "ch01": {"cost_usd": 6.0, "duration_sec": 1200},
            "ch02": {"cost_usd": 0, "duration_sec": None},  # partial — skipped
        })
        c, _s, _n = pf.historical_means()
        assert c == 6.0


def test_count_chapters(tmp_path):
    bd = tmp_path / "book"
    (bd / "chapter-contracts").mkdir(parents=True)
    for n in ("ch01-a", "ch02-b", "ch03-c"):
        (bd / "chapter-contracts" / f"{n}.yml").write_text("x: 1", encoding="utf-8")
    assert pf.count_chapters(bd) == 3
    assert pf.count_chapters(tmp_path / "nope") == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
