#!/usr/bin/env python3
"""Phase 6 Screen-4 regression — intake_launch.prepare_launch (prep only, no spawn).

Commits staged files into canonical _source/, writes series-config.yaml, upserts
work.yml for a multi-volume work, scaffolds state at preflight, returns the launch
argv. NEVER spawns the orchestrator (the confirm is the Tier-2 gate).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths
import _work_manifest as wm
import intake_launch as launch
import intake_staging as staging

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    (root / "_system").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "SYSTEM_ROOT", root / "_system")
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    return root


def _staged(role_files: list[tuple[str, str]]) -> str:
    """role_files = [(filename, role)] → token with those files staged."""
    token = staging.new_session()
    for fn, role in role_files:
        rec = staging.register_file(token, fn, role=role)
        staging.stored_path(token, rec["id"]).write_bytes(b"data")
    return token


SETTINGS = {
    "content_profile": "islamic_scholarly",
    "source_language": "ar",
    "audience_profile": "traditional",
    "host_dynamic": "deep_dive",
    "length_tier": "extended",
    "video_style": "teaching_hybrid",
    "episode_planning_mode": "tribunal_arc",
}


class TestSingleBook:
    def test_prepares_single_book(self, temp_root):
        token = _staged([("book.pdf", "primary_source"), ("gloss.md", "pronunciation_reference")])
        res = launch.prepare_launch(title="My Book", settings=SETTINGS, staging_token=token, slug="my-book")
        bd = temp_root / "Islamic" / "my-book"
        assert (bd / "_source" / "book.pdf").is_file()
        assert (bd / "_source" / "gloss.md").is_file()
        assert res["slug"] == "my-book" and res["is_work"] is False
        assert res["branch"] == "Islamic/my-book"
        # series-config written with the routing-critical profile
        cfg = yaml.safe_load((bd / "_system" / "series-config.yaml").read_text())
        assert cfg["content_profile"] == "islamic_scholarly"
        assert cfg["video_style"] == "teaching_hybrid"
        # state scaffolded at preflight
        st = json.loads((bd / "_system" / "orchestrator-state.json").read_text())
        assert st["phase"] == "preflight" and st["status"] == "draft"
        # launch argv = orchestrator, built but NOT executed. The source is the
        # POSITIONAL pdf_path argument: this asserted `--start` until 2026-08-30,
        # a flag orchestrate_book.py has never declared, so the test was pinning
        # a launch line that died at argparse with exit 2 every time it ran.
        assert res["launch"]["script"] == "orchestrate_book.py"
        args = res["launch"]["args"]
        assert "--start" not in args
        assert args[0].endswith("_source/book.pdf")
        assert args[1:] == ["--slug", "my-book"]
        # And the real parser accepts it — the check whose absence let the
        # original defect ship under a passing test.
        import orchestrate_book

        parsed = orchestrate_book.build_parser().parse_args(args)
        assert parsed.slug == "my-book"
        assert str(parsed.pdf_path).endswith("_source/book.pdf")
        # staging cleaned
        assert not staging.staging_dir(token).exists()


class TestMultiVolume:
    def test_prepares_work_volume_and_upserts_manifest(self, temp_root):
        token = _staged([("vol2.pdf", "primary_source")])
        res = launch.prepare_launch(title="Asaas", settings=SETTINGS, staging_token=token, work_slug="asaas", volume=2)
        assert res["slug"] == "asaas-vol-02" and res["is_work"] is True
        assert res["branch"] == "Islamic/asaas"
        # work.yml upserted with the volume + role-tagged sources
        m = wm.read_manifest(temp_root / "Islamic" / "asaas")
        v = [x for x in m["volumes"] if x["dir"] == "vol-02"][0]
        assert v["slug"] == "asaas-vol-02"
        assert v["sources"][0]["role"] == "primary_source"
        assert v["sources"][0]["path"] == "vol-02/_source/vol2.pdf"
        # files committed to vol-02/_source
        assert (temp_root / "Islamic" / "asaas" / "vol-02" / "_source" / "vol2.pdf").is_file()
        # work launch → sequencer
        assert res["launch"]["script"] == "orchestrate_work.py"
        assert res["launch"]["args"] == ["asaas"]
        # resolver sees the new volume
        assert _paths.find_content("asaas-vol-02") is not None


class TestGuards:
    def test_requires_slug_xor_work(self, temp_root):
        token = _staged([("a.pdf", "primary_source")])
        with pytest.raises(ValueError):
            launch.prepare_launch(title="x", settings=SETTINGS, staging_token=token, slug="a", work_slug="b", volume=1)

    def test_commit_fails_without_primary(self, temp_root):
        token = _staged([("a.txt", "supplementary_text")])  # no primary
        with pytest.raises(ValueError):
            launch.prepare_launch(title="x", settings=SETTINGS, staging_token=token, slug="a")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
