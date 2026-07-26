"""The Python half of the content-paths <-> _paths mirror pair.

The JS half is `plan-dashboard/scripts/lib/content-paths.test.mjs`, reading the
SAME fixture file. Neither side owns it.

Until 2026-07-26 the two implementations were kept in step by a prose comment in
each file plus a rule in CLAUDE.md, and nothing checked it. They had drifted: the
legacy resolution ladders disagreed about precedence, so a repo carrying both a
flat `content/drafts/<slug>` and a categorised `content/published/books/<slug>`
resolved to two DIFFERENT directories depending on whether the pipeline or the
Astro site asked. Silent, and worse than a crash. See the `_comment` block in the
fixture file for the full rationale.

`_paths` reads PODCAST_FACTORY_ROOT once at import, so every layout case reloads
the module against its own temp tree.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "scripts" / "podcast"
FIXTURES = REPO_ROOT / "plan-dashboard" / "scripts" / "lib" / "content-paths.fixtures.json"

if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))


def _fixtures() -> dict:
    assert FIXTURES.is_file(), f"shared fixture file missing: {FIXTURES}"
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


FIX = _fixtures()


def _paths_rooted_at(root: Path):
    """Import `_paths` with REPO_ROOT bound to `root`.

    The module snapshots the env var at import time, so a reload is the only way
    to retarget it. Restores the caller's environment on the way out — but NOT the
    module, which stays bound to `root` until the autouse fixture below puts it
    back. See that fixture for why this matters.
    """
    previous = os.environ.get("PODCAST_FACTORY_ROOT")
    os.environ["PODCAST_FACTORY_ROOT"] = str(root)
    try:
        import _paths

        return importlib.reload(_paths)
    finally:
        if previous is None:
            os.environ.pop("PODCAST_FACTORY_ROOT", None)
        else:
            os.environ["PODCAST_FACTORY_ROOT"] = previous


@pytest.fixture(autouse=True)
def _restore_paths_module():
    """Rebind `_paths` to the real repo root after every test in this module.

    Non-negotiable, and learned the hard way: `_paths` derives CONTENT_ROOT,
    SHARED_ROOT, ARCHIVE_ROOT and friends at import time, and `sys.modules` is
    shared across the whole pytest session. Leaving the module pointed at a temp
    tree that pytest has since deleted broke three unrelated tests in
    test_episode_engine_and_style.py — they passed alone and failed in the full
    suite, which is the most expensive kind of failure to diagnose.
    """
    yield
    _paths_rooted_at(REPO_ROOT)


def _fs_is_case_sensitive(root: Path) -> bool:
    probe = root / "CaseProbe"
    probe.mkdir()
    return not (root / "caseprobe").exists()


def _materialise(root: Path, case: dict) -> None:
    for d in case.get("tree", []):
        (root / d).mkdir(parents=True, exist_ok=True)
    for rel, body in (case.get("files") or {}).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


# ── vocabulary ────────────────────────────────────────────────────────────────
def test_vocabulary_matches_the_shared_fixtures() -> None:
    """Catches an enum extended on one side only."""
    p = _paths_rooted_at(REPO_ROOT)
    v = FIX["vocabulary"]
    assert list(p.BUCKETS) == v["buckets"]
    assert list(p.STAGES) == v["stages"]
    assert list(p.STATUSES) == v["statuses"]
    assert list(p.ALLOWED_CATEGORIES) == v["allowed_categories"]
    assert p.WORK_MANIFEST_NAME == v["work_manifest_name"]
    assert p._CATEGORY_TO_BUCKET == v["category_to_bucket"]


# ── pure functions ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["resolve_bucket_cases"], ids=lambda c: c["why"])
def test_resolve_bucket_matches_the_shared_fixtures(case: dict) -> None:
    p = _paths_rooted_at(REPO_ROOT)
    assert p.resolve_bucket(bucket=case["bucket"], profile=None, category=case["category"]) == case["out"]


@pytest.mark.parametrize("case", FIX["vol_dir_cases"], ids=lambda c: c["in"])
def test_vol_dir_pattern_matches_the_shared_fixtures(case: dict) -> None:
    """JS `\\d` is ASCII-only and Python's is Unicode-aware. Arabic-Indic digits
    must be rejected on BOTH sides or a volume dir keys differently per language —
    the same class of bug anchorKey hit in July."""
    p = _paths_rooted_at(REPO_ROOT)
    assert bool(p._VOL_DIR_RE.match(case["in"])) is case["is_vol"]


@pytest.mark.parametrize("case", FIX["composite_slug_cases"], ids=lambda c: c["in"])
def test_composite_slug_pattern_matches_the_shared_fixtures(case: dict) -> None:
    p = _paths_rooted_at(REPO_ROOT)
    m = p._COMPOSITE_SLUG_RE.match(case["in"])
    if case["work"] is None:
        assert m is None
    else:
        assert m is not None, case["in"]
        assert m.group("work") == case["work"]
        assert m.group("dir") == case["dir"]


# ── on-disk resolution ────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["layout_cases"], ids=lambda c: c["name"])
def test_layout_resolution_matches_the_shared_fixtures(case: dict, tmp_path: Path) -> None:
    """The precedence assertions. A tie broken differently on the two sides means
    the site and the pipeline read different folders for the same book."""
    if case.get("requires_case_sensitive_fs") and not _fs_is_case_sensitive(tmp_path):
        pytest.skip("case-insensitive filesystem — outcome would vary by platform, not by implementation")

    _materialise(tmp_path, case)
    p = _paths_rooted_at(tmp_path)
    found = p.find_content(case["slug"])

    if case["expect_dir"] is None:
        assert found is None, f"expected no match for {case['slug']!r}, got {found}"
        return

    assert found is not None, f"expected {case['expect_dir']} for {case['slug']!r}, got no match"
    assert found[2].relative_to(tmp_path).as_posix() == case["expect_dir"]


@pytest.mark.parametrize("case", FIX["status_cases"], ids=lambda c: c["name"])
def test_status_of_matches_the_shared_fixtures(case: dict, tmp_path: Path) -> None:
    p = _paths_rooted_at(tmp_path)
    book = tmp_path / "content" / "Islamic" / "book"
    (book / "_system").mkdir(parents=True)
    (book / "_system" / "orchestrator-state.json").write_text(case["state"], encoding="utf-8")
    assert p.status_of(book) == case["expect"]


def test_slug_of_returns_the_composite_slug_for_a_volume(tmp_path: Path) -> None:
    """Two works can each contain a `vol-01`; the plain dir name is not a stable
    identity. Mirrors slugOf on the TypeScript side."""
    p = _paths_rooted_at(tmp_path)
    work = tmp_path / "content" / "Islamic" / "work-a"
    (work / "vol-01").mkdir(parents=True)
    (work / "work.yml").write_text("title: Work A\n", encoding="utf-8")
    assert p.slug_of(work / "vol-01") == "work-a-vol-01"
    assert p.slug_of(work) == "work-a"

    loose = tmp_path / "content" / "Islamic" / "notwork"
    (loose / "vol-01").mkdir(parents=True)
    assert p.slug_of(loose / "vol-01") == "vol-01", "no work.yml marker means no composite slug"
