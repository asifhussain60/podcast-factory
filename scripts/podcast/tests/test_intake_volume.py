#!/usr/bin/env python3
"""Phase 2 regression — intake_book.py --work/--volume flow.

Asserts a multi-volume intake creates the parent work.yml, a vol-NN volume dir
with its own state stamped with work_slug/volume, a composite slug, and registers
the volume in the manifest. Second volume inherits work identity. The single-book
positional path stays byte-identical (no work.yml, flat dir).
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
import intake_book as ib


@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    monkeypatch.setattr(ib, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ib, "RAW_DIR", tmp_path / "raw")
    pdf = tmp_path / "src.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake\n")
    return tmp_path, root, pdf


class TestVolumeIntake:
    def test_first_volume_creates_work(self, temp_repo):
        _repo, root, pdf = temp_repo
        rc = ib._intake_volume_from_pdf(
            str(pdf),
            "asaas",
            1,
            force=False,
            no_branch=True,
            profile="islamic_scholarly",
            title="Asaas al-Taveel",
        )
        assert rc == 0
        wd = root / "Islamic" / "asaas"
        assert wm.has_manifest(wd)
        m = wm.read_manifest(wd)
        assert m["work_slug"] == "asaas"
        assert m["title"] == "Asaas al-Taveel"
        assert [v["slug"] for v in m["volumes"]] == ["asaas-vol-01"]
        # volume dir + state
        vol = wd / "vol-01"
        assert (vol / "_source" / "src.pdf").is_file()
        st = json.loads((vol / "_system" / "orchestrator-state.json").read_text())
        assert st["book_slug"] == "asaas-vol-01"
        assert st["work_slug"] == "asaas"
        assert st["volume"] == 1
        # resolver agrees
        assert _paths.find_content("asaas-vol-01")[2] == vol

    def test_second_volume_inherits_work(self, temp_repo):
        _repo, root, pdf = temp_repo
        ib._intake_volume_from_pdf(str(pdf), "asaas", 1, force=False, no_branch=True)
        ib._intake_volume_from_pdf(str(pdf), "asaas", 2, force=False, no_branch=True)
        m = wm.read_manifest(root / "Islamic" / "asaas")
        assert [v["slug"] for v in m["volumes"]] == ["asaas-vol-01", "asaas-vol-02"]
        assert _paths.find_content("asaas-vol-02")[2].name == "vol-02"

    def test_volume_sources_role_tagged(self, temp_repo):
        _repo, root, pdf = temp_repo
        ib._intake_volume_from_pdf(str(pdf), "asaas", 1, force=False, no_branch=True)
        v = wm.volume_entry("asaas-vol-01")
        assert v["sources"][0]["role"] == "primary_source"
        assert v["sources"][0]["path"].endswith("src.pdf")

    def test_single_book_path_has_no_manifest(self, temp_repo):
        _repo, root, pdf = temp_repo
        rc = ib._intake_from_pdf(str(pdf), "solo-book", force=False, no_branch=True)
        assert rc == 0
        bd = root / "Islamic" / "solo-book"
        assert not wm.has_manifest(bd)
        assert (bd / "_source" / "src.pdf").is_file()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
