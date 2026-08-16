"""The cleanup script's refusals are the part that has to be right.

Reclaiming a cache wrong costs a rebuild. Reclaiming the wrong thing costs work
that does not come back — so every one of the four structural refusals gets a test
that puts a real file in harm's way and asserts it survives.

The one that matters most is the local D1. Deleting it wipes the `session` table,
which signs the operator out of localhost; the site then shows a sign-in page and
looks like nothing shipped. CLAUDE.md bans it by name, and the ban is worth
exactly as much as the test under it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repo_cleanup import Cleanup  # noqa: E402


def make(tmp_path: Path, profile: dict) -> Cleanup:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    c = Cleanup(root=tmp_path, profile=profile)
    return c


def write(root: Path, rel: str, text: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


CACHE_PROFILE = {"hygiene": {"reclaimable": [{"name": "python-bytecode", "match": "**/__pycache__"}]}}


def rels(c: Cleanup) -> list[str]:
    return [x.rel for x in c.candidates]


def why(c: Cleanup, rel: str) -> str:
    return next(w for p, w in c.refused if p == rel)


# ---------- it does the job ----------


def test_it_finds_and_removes_a_cache_directory(tmp_path):
    c = make(tmp_path, CACHE_PROFILE)
    write(tmp_path, "pkg/__pycache__/a.pyc", "x" * 1000)
    c.load_tracked()
    c.collect(set())
    assert rels(c) == ["pkg/__pycache__"]
    assert c.apply() == 1000
    assert not (tmp_path / "pkg/__pycache__").exists()


def test_a_dry_run_removes_nothing(tmp_path):
    c = make(tmp_path, CACHE_PROFILE)
    write(tmp_path, "pkg/__pycache__/a.pyc")
    c.load_tracked()
    c.collect(set())
    # collect() is the survey; apply() is the only thing that deletes.
    assert (tmp_path / "pkg/__pycache__").exists()


# ---------- refusal 1: a tracked file is never debris ----------


def test_it_refuses_a_tracked_file_however_the_glob_reads(tmp_path):
    c = make(tmp_path, {"hygiene": {"reclaimable": [{"name": "junk", "match": "**/*.pyc"}]}})
    write(tmp_path, "kept.pyc", "important")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    c.load_tracked()
    c.collect(set())
    assert rels(c) == []
    assert "tracked by git" in why(c, "kept.pyc")
    assert (tmp_path / "kept.pyc").exists()


def test_it_refuses_a_directory_holding_a_tracked_file(tmp_path):
    c = make(tmp_path, CACHE_PROFILE)
    write(tmp_path, "pkg/__pycache__/generated.pyc")
    write(tmp_path, "pkg/__pycache__/committed.txt")
    subprocess.run(["git", "add", "pkg/__pycache__/committed.txt"], cwd=tmp_path, check=True)
    c.load_tracked()
    c.collect(set())
    assert rels(c) == []
    assert "contains tracked files" in why(c, "pkg/__pycache__")


# ---------- refusal 2: protected runtime state ----------


def test_it_refuses_the_local_d1_however_broad_the_pattern(tmp_path):
    """The rule CLAUDE.md bans by name: never destroy the local environment."""
    d1 = "listener/.wrangler/state/v3/d1"
    c = make(
        tmp_path,
        {
            "hygiene": {
                "reclaimable": [{"name": "wrangler", "match": "listener/.wrangler/state/v3/*"}],
                "protected_runtime": [{"path": d1, "why": "wiping it signs the operator out of localhost"}],
            }
        },
    )
    write(tmp_path, f"{d1}/miniflare-D1DatabaseObject/db.sqlite", "sessions live here")
    write(tmp_path, "listener/.wrangler/state/v3/cache/x", "disposable")
    c.load_tracked()
    c.collect(set())
    assert rels(c) == ["listener/.wrangler/state/v3/cache"]
    assert "protected by the contract" in why(c, d1)
    c.apply()
    assert (tmp_path / d1 / "miniflare-D1DatabaseObject/db.sqlite").exists()


def test_the_contracts_protected_list_governs_the_sweep_too(tmp_path):
    c = make(
        tmp_path,
        {
            "protected": ["content/**", "_learning/**"],
            "hygiene": {"reclaimable": [{"name": "os-debris", "match": "**/.DS_Store"}]},
        },
    )
    write(tmp_path, "content/book/.DS_Store")
    write(tmp_path, "docs/.DS_Store")
    c.load_tracked()
    c.collect(set())
    assert rels(c) == ["docs/.DS_Store"]
    assert "protected by the contract" in why(c, "content/book/.DS_Store")


# ---------- refusal 3: nothing outside the repo ----------


def test_it_refuses_a_symlink_pointing_out_of_the_repo(tmp_path):
    outside = tmp_path.parent / "outside-the-repo"
    outside.mkdir(exist_ok=True)
    (outside / "precious.txt").write_text("not ours to delete", encoding="utf-8")

    c = make(tmp_path, {"hygiene": {"reclaimable": [{"name": "junk", "match": "*.cache"}]}})
    (tmp_path / "link.cache").symlink_to(outside)
    c.load_tracked()
    c.collect(set())
    assert rels(c) == []
    assert "symlink" in why(c, "link.cache")
    assert (outside / "precious.txt").exists()


# ---------- refusal 4: confirm-required categories ----------


def test_a_confirm_category_is_skipped_unless_named(tmp_path):
    profile = {"hygiene": {"reclaimable": [{"name": "big", "match": "**/__pycache__", "confirm": True}]}}
    c = make(tmp_path, profile)
    write(tmp_path, "pkg/__pycache__/a.pyc")
    c.load_tracked()
    c.collect(set())
    assert rels(c) == []
    assert any("needs --include big" in n for n in c.notes)


def test_a_confirm_category_runs_when_named(tmp_path):
    profile = {"hygiene": {"reclaimable": [{"name": "big", "match": "**/__pycache__", "confirm": True}]}}
    c = make(tmp_path, profile)
    write(tmp_path, "pkg/__pycache__/a.pyc")
    c.load_tracked()
    c.collect({"big"})
    assert rels(c) == ["pkg/__pycache__"]


# ---------- the sweep never guesses at working files ----------


def test_large_untracked_trees_are_reported_and_never_swept(tmp_path):
    c = make(tmp_path, CACHE_PROFILE)
    write(tmp_path, "experiments/run/output.wav", "y" * (60 * 1024 * 1024))
    c.load_tracked()
    c.collect(set())
    found = c.survey_untracked()
    assert [rel for rel, _ in found] == ["experiments"]
    assert rels(c) == []  # reported, not queued for deletion
    c.apply()
    assert (tmp_path / "experiments/run/output.wav").exists()


def test_git_maintenance_is_never_a_path_sweep(tmp_path):
    """`.git` appears in the contract as a category. It must reach `git gc` and
    never a glob: loose objects are only garbage if nothing references them, and
    the only thing that knows that is git."""
    c = make(tmp_path, {"hygiene": {"reclaimable": [{"name": "git-maintenance", "match": ".git", "confirm": True}]}})
    write(tmp_path, "a.txt")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=tmp_path, check=True)
    c.load_tracked()
    c.collect({"git-maintenance"})
    assert rels(c) == []  # not queued as a deletable path
    c.run_git_maintenance()
    assert (tmp_path / ".git").is_dir()
    assert subprocess.run(["git", "log", "-1"], cwd=tmp_path, capture_output=True).returncode == 0


# ---------- the survey is not the authority ----------


def test_a_path_that_becomes_tracked_between_survey_and_sweep_is_spared(tmp_path):
    c = make(tmp_path, {"hygiene": {"reclaimable": [{"name": "junk", "match": "*.cache"}]}})
    write(tmp_path, "x.cache", "was debris")
    c.load_tracked()
    c.collect(set())
    assert rels(c) == ["x.cache"]

    subprocess.run(["git", "add", "x.cache"], cwd=tmp_path, check=True)
    c.load_tracked()  # the tree changed under us
    assert c.apply() == 0
    assert (tmp_path / "x.cache").exists()
