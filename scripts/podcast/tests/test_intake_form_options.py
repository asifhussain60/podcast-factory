#!/usr/bin/env python3
"""Phase 6 regression — intake_form_options (smart-form dropdown single-source).

Defaults come from the pipeline's OWN vocabularies (registry + blueprint enums);
user add/rename/remove persist to form-options.yml and survive a reload.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths
import intake_form_options as fo
from _rules import BUCKETS, CONTENT_PROFILES


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    root = tmp_path / "content"
    root.mkdir()
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    return root


class TestDefaults:
    def test_defaults_track_the_registry(self):
        d = fo.default_options()
        assert d["content_profile"] == list(CONTENT_PROFILES)
        assert d["bucket"] == list(BUCKETS)
        assert d["host_dynamic"] == ["deep_dive", "debate"]
        assert "teaching_hybrid" in d["video_style"]
        assert set(fo.FIELDS) == set(d.keys())

    def test_get_options_no_overrides_equals_defaults(self, temp_root):
        assert fo.get_form_options() == fo.default_options()


class TestPersistence:
    def test_add_persists_and_survives_reload(self, temp_root):
        merged = fo.add_option("source_language", "zh")
        assert "zh" in merged["source_language"]
        assert fo.options_path().is_file()
        # fresh read (simulates reload)
        assert "zh" in fo.get_form_options()["source_language"]

    def test_add_is_idempotent(self, temp_root):
        fo.add_option("source_language", "zh")
        fo.add_option("source_language", "zh")
        assert fo.get_form_options()["source_language"].count("zh") == 1

    def test_add_existing_default_is_noop(self, temp_root):
        before = fo.get_form_options()["bucket"]
        fo.add_option("bucket", "Islamic")  # already a default
        assert fo.get_form_options()["bucket"] == before

    def test_rename_default_value(self, temp_root):
        merged = fo.rename_option("content_profile", "fiction", "novel")
        assert "novel" in merged["content_profile"]
        assert "fiction" not in merged["content_profile"]
        assert "novel" in fo.get_form_options()["content_profile"]  # persisted

    def test_rename_user_added_value(self, temp_root):
        fo.add_option("source_language", "zh")
        fo.rename_option("source_language", "zh", "zh-Hant")
        opts = fo.get_form_options()["source_language"]
        assert "zh-Hant" in opts and "zh" not in opts

    def test_unknown_field_rejected(self, temp_root):
        with pytest.raises(ValueError):
            fo.add_option("not_a_field", "x")

    def test_empty_value_rejected(self, temp_root):
        with pytest.raises(ValueError):
            fo.add_option("source_language", "  ")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
