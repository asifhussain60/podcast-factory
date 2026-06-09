#!/usr/bin/env python3
"""Phase 6 Screen-4 regression — intake_status cockpit view (read-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths  # noqa: E402
import intake_status as iss  # noqa: E402


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    return root


def _book(root: Path, slug: str, state: dict, *, series_plan: str | None = None) -> Path:
    bd = root / "Islamic" / slug
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
    if series_plan is not None:
        (bd / "_system" / "series-plan.md").write_text(series_plan, encoding="utf-8")
    return bd


class TestStatusView:
    def test_unknown_slug(self, temp_root):
        v = iss.status_view("nope")
        assert v["found"] is False

    def test_running_phase_no_gate(self, temp_root):
        _book(temp_root, "bk", {
            "phase": "per-chapter", "phase_status": "running", "status": "draft",
            "phases": {"per-chapter": {"completed_slugs": ["a", "b"], "failed_slugs": [],
                                       "chapter_timings": {"a": {}, "b": {}, "c": {}}}},
        })
        v = iss.status_view("bk")
        assert v["found"] and v["at_human_gate"] is False and v["gate"] is None
        assert v["chapters"]["completed"] == 2
        assert v["chapters"]["total"] == 3  # from timings union

    def test_human_gate_surfaced(self, temp_root):
        _book(temp_root, "bk", {"phase": "finalize", "phase_status": "halted", "status": "draft"})
        v = iss.status_view("bk")
        assert v["at_human_gate"] is True
        assert v["gate"]["name"] == "finalize"
        assert "publish" in v["gate"]["label"].lower()

    def test_failed_phase_is_not_a_gate(self, temp_root):
        _book(temp_root, "bk", {"phase": "per-chapter", "phase_status": "failed",
                                "status": "draft", "last_error": {"message": "boom"}})
        v = iss.status_view("bk")
        assert v["at_human_gate"] is False
        assert v["last_error"] == "boom"

    def test_cost_vs_cap(self, temp_root):
        bd = _book(temp_root, "bk", {"phase": "per-chapter", "phase_status": "running", "status": "draft"},
                   series_plan="**Book Cost Cap Usd:** 40\n**Per Chapter Cost Cap Usd:** 5\n")
        # one ledger row
        (bd / "_system" / "cost-ledger.jsonl").write_text(
            json.dumps({"cost_usd": 12.5, "step": "x"}) + "\n", encoding="utf-8")
        v = iss.status_view("bk")
        assert v["cost"]["book_spend_usd"] == 12.5
        assert v["cost"]["book_cap_usd"] == 40.0
        assert v["cost"]["book_cap_active"] is True
        assert v["cost"]["over_book_cap"] is False

    def test_composite_volume_slug_resolves(self, temp_root):
        import _work_manifest as wm
        wd = temp_root / "Islamic" / "asaas"
        (wd / "vol-01" / "_system").mkdir(parents=True)
        (wd / "vol-01" / "_system" / "orchestrator-state.json").write_text(
            json.dumps({"phase": "0f", "phase_status": "halted", "status": "draft",
                        "work_slug": "asaas", "volume": 1}), encoding="utf-8")
        wm.write_manifest(wd, {"work_slug": "asaas", "volumes": [
            {"order": 1, "slug": "asaas-vol-01", "dir": "vol-01"}]})
        v = iss.status_view("asaas-vol-01")
        assert v["found"] and v["work_slug"] == "asaas" and v["volume"] == 1
        assert v["gate"]["name"] == "0f"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
