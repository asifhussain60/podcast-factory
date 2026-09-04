#!/usr/bin/env python3
"""`deploy_listener.sh` must leave the caller's branch exactly as it found it.

The orchestrator's publish phase runs this script from a BOOK branch, with the
state file and meta.yml just rewritten and not yet committed. The script's first
act is `git checkout develop`, which either refuses (and the deploy dies for a
reason that has nothing to do with deploying) or succeeds and carries the dirty
files across, after which every `die` leaves the pipeline sitting on develop and
the next phase commit lands there. Two guards, both pinned here:

  * a dirty working tree is refused BEFORE any checkout or fetch, by name;
  * whatever path the script exits by, the branch it started on is restored.

The script is copied into a throwaway repository so `REPO_ROOT`, which it derives
from its own location, resolves there and never to this checkout. That repository
has no remote, so the run stops at the sweep's fast-forward pull — before the
keychain, before wrangler, before anything that leaves the machine.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "deploy_listener.sh"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "scripts" / "podcast").mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "checkout", "-q", "-b", "develop")
    shutil.copy2(SCRIPT, repo / "scripts" / "podcast" / "deploy_listener.sh")
    (repo / "meta.yml").write_text("status: draft\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seed")
    git(repo, "checkout", "-q", "-b", "Islamic/a-book")
    return repo


def run_deploy(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/podcast/deploy_listener.sh", "a-book", "--dry-run"],
        cwd=repo,
        capture_output=True,
        text=True,
    )


class BranchSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.repo = make_repo(Path(self._td.name))

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_a_dirty_tracked_file_is_refused_before_any_checkout(self) -> None:
        (self.repo / "meta.yml").write_text("status: published\n", encoding="utf-8")

        result = run_deploy(self.repo)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uncommitted", result.stderr.lower(), result.stderr)
        self.assertNotIn("switching to develop", result.stdout, result.stdout)
        self.assertEqual(git(self.repo, "branch", "--show-current"), "Islamic/a-book")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "M meta.yml")  # still dirty, still here

    def test_a_clean_feature_branch_is_restored_on_exit(self) -> None:
        result = run_deploy(self.repo)

        # No remote, so the sweep's fast-forward pull is where it stops — after
        # the checkout to develop, which is the point: the restore has to work on
        # a failure path, because that is the path the orchestrator hit.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("switching to develop", result.stdout, result.stdout)
        self.assertEqual(git(self.repo, "branch", "--show-current"), "Islamic/a-book")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
