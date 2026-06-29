#!/usr/bin/env python3
"""Phase 1 regression suite — multi-volume foundation.

Pins three invariants:
  1. FLAT byte-identity — the existing flat books resolve EXACTLY as before, and
     a flat book whose name ends in `-vol-N` (journey-to-the-west-vol-1) is NEVER
     mistaken for a volume of a work. This is the must-not-regress pin.
  2. NESTED happy-path — a work.yml-marked parent yields independent per-volume
     status, composite-slug resolution, and a single shared branch.
  3. _work_manifest.py I/O — read/write/round-trip + slug mapping.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths  # noqa: E402
import _branching  # noqa: E402
import _work_manifest as wm  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────
def _write_state(book_dir: Path, status: str) -> None:
    sysd = book_dir / "_system"
    sysd.mkdir(parents=True, exist_ok=True)
    (sysd / "orchestrator-state.json").write_text(json.dumps({"status": status}), encoding="utf-8")


@pytest.fixture
def temp_content(tmp_path, monkeypatch):
    """Point _paths at an isolated content root with no legacy trees."""
    root = tmp_path / "content"
    for b in _paths.BUCKETS:
        (root / b).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "DRAFTS_ROOT", root / "drafts")
    monkeypatch.setattr(_paths, "PUBLISHED_ROOT", root / "published")
    return root


def _make_flat_book(root: Path, bucket: str, slug: str, status: str = "draft") -> Path:
    d = root / bucket / slug
    d.mkdir(parents=True, exist_ok=True)
    _write_state(d, status)
    return d


def _make_work(root: Path, bucket: str, work_slug: str, volumes: list[tuple[str, str]]) -> Path:
    """volumes = [(vol_dir, status), …]. Writes a work.yml marker + per-volume state."""
    wd = root / bucket / work_slug
    wd.mkdir(parents=True, exist_ok=True)
    vol_entries = []
    for i, (vdir, status) in enumerate(volumes, start=1):
        vol = wd / vdir
        vol.mkdir(parents=True, exist_ok=True)
        _write_state(vol, status)
        vol_entries.append({"order": i, "slug": f"{work_slug}-{vdir}", "dir": vdir, "status": status})
    wm.write_manifest(wd, {
        "work_slug": work_slug, "title": work_slug.title(),
        "content_profile": "islamic_scholarly", "bucket": bucket,
        "volumes": vol_entries,
    })
    return wd


# ── 1. FLAT byte-identity ──────────────────────────────────────────────────────
class TestFlatByteIdentity:
    def test_flat_book_resolves_unchanged(self, temp_content):
        _make_flat_book(temp_content, "Islamic", "the-master-and-the-disciple", "published")
        found = _paths.find_content("the-master-and-the-disciple")
        assert found is not None
        status, bucket, path = found
        assert (status, bucket) == ("published", "Islamic")
        assert path.name == "the-master-and-the-disciple"

    def test_vol_suffixed_flat_book_is_not_a_volume(self, temp_content):
        """journey-to-the-west AND journey-to-the-west-vol-1 are SEPARATE flat books.
        The vol-suffixed one must resolve to its own dir, never descend the other."""
        _make_flat_book(temp_content, "Fiction", "journey-to-the-west", "draft")
        _make_flat_book(temp_content, "Fiction", "journey-to-the-west-vol-1", "published")
        found = _paths.find_content("journey-to-the-west-vol-1")
        assert found is not None
        status, bucket, path = found
        assert (status, bucket) == ("published", "Fiction")
        assert path.name == "journey-to-the-west-vol-1"
        # work_slug_of must say it is NOT a multi-volume work (no parent manifest).
        assert wm.work_slug_of("journey-to-the-west-vol-1") is None
        assert _paths.slug_of(path) == "journey-to-the-west-vol-1"

    def test_iter_content_no_volume_descent_without_manifest(self, temp_content):
        _make_flat_book(temp_content, "Islamic", "ayyuhal-walad")
        _make_flat_book(temp_content, "Fiction", "journey-to-the-west-vol-1")
        slugs = {_paths.slug_of(p) for _s, _b, p in _paths.iter_content()}
        assert slugs == {"ayyuhal-walad", "journey-to-the-west-vol-1"}

    def test_branch_for_flat_book_unchanged(self):
        assert _branching.branch_for_work(
            "ayyuhal-walad", profile="islamic_scholarly"
        ) == _branching.branch_name(None, "ayyuhal-walad", profile="islamic_scholarly")


# ── 2. NESTED happy-path ────────────────────────────────────────────────────────
class TestNestedWork:
    def test_composite_slug_resolves_to_volume_dir(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "published"), ("vol-02", "draft")])
        f1 = _paths.find_content("asaas-vol-01")
        f2 = _paths.find_content("asaas-vol-02")
        assert f1 and f1[0] == "published" and f1[2].name == "vol-01"
        assert f2 and f2[0] == "draft" and f2[2].name == "vol-02"

    def test_bare_work_slug_rolls_up_status(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "published"), ("vol-02", "draft")])
        f = _paths.find_content("asaas")
        assert f is not None
        status, bucket, path = f
        assert bucket == "Islamic" and path.name == "asaas"
        assert status == "draft"  # not all volumes published → rollup is draft
        assert _paths.is_work_parent(path)

    def test_rollup_published_only_when_all_published(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "published"), ("vol-02", "published")])
        assert _paths.find_content("asaas")[0] == "published"

    def test_iter_content_yields_composite_volume_slugs(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "draft"), ("vol-02", "draft")])
        _make_flat_book(temp_content, "Islamic", "ayyuhal-walad")
        slugs = {_paths.slug_of(p) for _s, _b, p in _paths.iter_content()}
        assert slugs == {"asaas-vol-01", "asaas-vol-02", "ayyuhal-walad"}
        # the work parent itself is never yielded as a book
        assert "asaas" not in slugs

    def test_one_work_one_branch(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "draft"), ("vol-02", "draft")])
        b1 = _branching.branch_for_work("asaas-vol-01", profile="islamic_scholarly")
        b2 = _branching.branch_for_work("asaas-vol-02", profile="islamic_scholarly")
        bw = _branching.branch_for_work("asaas", profile="islamic_scholarly")
        assert b1 == b2 == bw == "Islamic/asaas"

    def test_two_works_same_vol_name_no_collision(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "draft")])
        _make_work(temp_content, "Fiction", "epic", [("vol-01", "published")])
        assert _paths.find_content("asaas-vol-01")[0] == "draft"
        assert _paths.find_content("epic-vol-01")[0] == "published"


# ── 3. _work_manifest I/O ───────────────────────────────────────────────────────
class TestManifestIO:
    def test_round_trip(self, temp_content):
        wd = temp_content / "Islamic" / "asaas"
        wd.mkdir(parents=True)
        manifest = {"work_slug": "asaas", "title": "Asaas", "volumes": [{"order": 1, "slug": "asaas-vol-01", "dir": "vol-01"}]}
        wm.write_manifest(wd, manifest)
        assert wm.has_manifest(wd)
        assert wm.read_manifest(wd) == manifest

    def test_read_absent_returns_none(self, temp_content):
        assert wm.read_manifest(temp_content / "Islamic" / "nope") is None

    def test_volumes_of_ordered(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-02", "draft"), ("vol-01", "draft")])
        # manifest is written in insertion order (vol-02 first); volumes_of sorts by `order`
        vols = wm.volumes_of("asaas")
        assert [v["dir"] for v in vols] == ["vol-02", "vol-01"]  # order field follows insertion
        assert [v["order"] for v in vols] == [1, 2]

    def test_work_slug_of_and_composite(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "draft")])
        assert wm.work_slug_of("asaas-vol-01") == "asaas"
        assert wm.work_slug_of("asaas-vol-99") == "asaas"  # belongs to work even if not listed
        assert wm.work_slug_of("nonexistent-vol-01") is None
        assert wm.composite_slug("asaas", "vol-03") == "asaas-vol-03"
        assert wm.is_volume_slug("asaas-vol-01") is True

    def test_volume_entry(self, temp_content):
        _make_work(temp_content, "Islamic", "asaas", [("vol-01", "published")])
        e = wm.volume_entry("asaas-vol-01")
        assert e and e["status"] == "published" and e["dir"] == "vol-01"

    def test_shared_dir(self, temp_content):
        wd = _make_work(temp_content, "Islamic", "asaas", [("vol-01", "draft")])
        m = wm.read_manifest(wd)
        m["shared"] = {"pronunciation": "_shared/pron.yml"}
        wm.write_manifest(wd, m)
        sp = wm.shared_dir("asaas", "pronunciation")
        assert sp == (wd / "_shared" / "pron.yml").resolve()
        assert wm.shared_dir("asaas", "missing") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
