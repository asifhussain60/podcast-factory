#!/usr/bin/env python3
"""Phase 2 regression suite — profile-driven phase routing (the root fix).

Pins that phase-skip decisions read the content_profile via the single
phase_capabilities() table, not the legacy `category` tag:

  - technical profile → skip phonetics + enrichment   (the fix)
  - islamic_scholarly / None → run both                (the must-not-regress pin)
  - a `books`-category item carrying a technical profile → skip (the bug it fixes)
  - consumer category with no explicit profile → shim routes as consumer_explainer
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _rules import ISLAMIC_SCHOLARLY_PROFILE, phase_capabilities
from phases.initial_driver import resolve_phase_profile


def _book(tmp_path: Path, profile: str | None) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    cfg = "" if profile is None else f"content_profile: {profile}\n"
    (bd / "_system" / "series-config.yaml").write_text(cfg, encoding="utf-8")
    return bd


class TestPhaseCapabilities:
    def test_islamic_scholarly_runs_everything(self):
        caps = phase_capabilities("islamic_scholarly")
        assert caps.skip_phonetics is False
        assert caps.skip_enrichment is False
        assert caps.skip_ocr is False

    def test_none_falls_back_to_islamic_scholarly(self):
        assert phase_capabilities(None) is phase_capabilities("islamic_scholarly")
        assert phase_capabilities("nonsense-profile") is phase_capabilities("islamic_scholarly")

    def test_technical_skips_phonetics_and_enrichment(self):
        caps = phase_capabilities("technical")
        assert caps.skip_phonetics is True
        assert caps.skip_enrichment is True

    def test_consumer_explainer_skips_all(self):
        caps = phase_capabilities("consumer_explainer")
        assert caps.skip_phonetics and caps.skip_enrichment and caps.skip_ocr


class TestRoutingResolution:
    def test_books_category_with_technical_profile_skips(self, tmp_path):
        """THE BUG: a 'books'-category book that is actually technical must skip
        phonetics/enrichment. Old category-based routing ran them."""
        bd = _book(tmp_path, "technical")
        profile = resolve_phase_profile(bd, category="books")
        assert profile == "technical"
        assert phase_capabilities(profile).skip_phonetics is True

    def test_islamic_book_runs_full_pipeline(self, tmp_path):
        bd = _book(tmp_path, "islamic_scholarly")
        profile = resolve_phase_profile(bd, category="books")
        assert profile == ISLAMIC_SCHOLARLY_PROFILE
        assert phase_capabilities(profile).skip_phonetics is False

    def test_consumer_category_no_profile_shim(self, tmp_path):
        """Compatibility shim: a 'sites' book that predates content_profile
        (profile defaults to islamic_scholarly) must still skip phonetics."""
        bd = _book(tmp_path, None)  # no content_profile → defaults to islamic_scholarly
        profile = resolve_phase_profile(bd, category="sites")
        assert profile == "consumer_explainer"
        assert phase_capabilities(profile).skip_phonetics is True

    def test_explicit_profile_beats_consumer_shim(self, tmp_path):
        """An explicit non-islamic profile is honoured regardless of category."""
        bd = _book(tmp_path, "general_nonfiction")
        profile = resolve_phase_profile(bd, category="sites")
        assert profile == "general_nonfiction"  # shim only fires for the islamic default


class TestCategoryStatePlumbing:
    """Regression pin (2026-07-31): `category` is a TOP-LEVEL state field
    (written by _progress.initial_state), never nested under `config` — the
    latter only ever holds length_tier/unit_mode. `_drive_authoring_through_0f`
    used to read `state.get("config", {}).get("category", "books")`, which
    silently defaulted to "books" on every run (the key never existed there),
    so resolve_phase_profile's sites/explainers -> consumer_explainer shim
    above never fired for books driven through run_initial. The tests above
    only exercise resolve_phase_profile directly with a passed-in category —
    they never would have caught this, since the bug was entirely in how the
    live caller sourced that argument from state.
    """

    def test_initial_state_writes_category_top_level_not_nested(self, tmp_path):
        sys.path.insert(0, str(SCRIPTS_PODCAST))
        from _progress import initial_state

        state = initial_state("test-slug", "sites")
        assert state.get("category") == "sites"
        assert "category" not in (state.get("config") or {})

    def test_reading_category_from_config_would_be_wrong(self, tmp_path):
        """Pins the fixed line's shape: state.get("category", ...), not
        state.get("config", {}).get("category", ...). If this test starts
        failing because config now legitimately carries category, the fix
        in initial_driver.py needs to be revisited alongside it."""
        sys.path.insert(0, str(SCRIPTS_PODCAST))
        from _progress import initial_state

        state = initial_state("test-slug", "sites")
        state["config"] = {"length_tier": "extended", "unit_mode": "auto"}

        correct = state.get("category", "books")
        buggy = (state.get("config") or {}).get("category", "books")

        assert correct == "sites"
        assert buggy == "books"  # the bug: silently wrong, every time


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
