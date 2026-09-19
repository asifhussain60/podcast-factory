"""The pre-commit hook must never wait forever.

2026-09-18: a `git commit` went uninterruptible while the machine's I/O was stalled, and the hook
had no time limit on ANY step (the repo probe, the 30 MB corpus export, the site linters), so every
stall left a stale `.git/index.lock` and a hung shell. Every heavy step is now bounded. A GATING
step that times out refuses the commit (fail-closed, releasing git's lock); the advisory corpus
export just skips. Driven against the real hook in a throwaway repo with stub steps.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "infra" / "git-hooks" / "pre-commit"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    hook = repo / ".git" / "hooks" / "pre-commit"
    shutil.copy(HOOK, hook)
    hook.chmod(0o755)
    (repo / "notes.txt").write_text("hello\n")
    run("git", "add", "notes.txt")
    return repo


def _stub(repo: Path, rel: str, body: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))


def _commit(repo: Path, **env) -> tuple[int, str, float]:
    started = time.monotonic()
    proc = subprocess.run(
        ["git", "commit", "-q", "-m", "x"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=60,
    )
    return proc.returncode, proc.stdout + proc.stderr, time.monotonic() - started


HANG = "import time\ntime.sleep(60)\n"


def test_a_hanging_probe_is_killed_and_the_commit_refused_without_leaving_a_lock(tmp_path):
    repo = _repo(tmp_path)
    _stub(repo, "scripts/repo_surgeon_probe.py", HANG)
    rc, out, took = _commit(repo, PF_HOOK_TIMEOUT="2")
    assert rc != 0, out
    assert "timed out" in out and "repo-surgeon probe" in out
    assert took < 30, f"the hook waited {took:.0f}s — it must be bounded"
    assert not (repo / ".git" / "index.lock").exists(), "a killed step must not leave git's lock behind"


def test_a_fast_probe_lets_the_commit_through(tmp_path):
    repo = _repo(tmp_path)
    _stub(repo, "scripts/repo_surgeon_probe.py", "print('ok')\n")
    rc, out, _ = _commit(repo, PF_HOOK_TIMEOUT="20")
    assert rc == 0, out


def test_a_hanging_corpus_export_is_skipped_not_fatal(tmp_path):
    repo = _repo(tmp_path)
    (repo / "content" / "knowledge-base").mkdir(parents=True)
    (repo / "content" / "knowledge-base" / "knowledge.db").write_text("")
    _stub(repo, "scripts/podcast/intelligence/corpus_sync.py", HANG)
    rc, out, took = _commit(repo, PF_HOOK_TIMEOUT="2")
    assert rc == 0, f"the corpus export is advisory and must never block a commit:\n{out}"
    assert "corpus export" in out and "timed out" in out
    assert took < 30


def test_the_corpus_skip_notice_is_shown_once_not_on_every_commit(tmp_path):
    repo = _repo(tmp_path)
    (repo / "content" / "knowledge-base").mkdir(parents=True)
    (repo / "content" / "knowledge-base" / "knowledge.db").write_text("")
    _stub(repo, "scripts/podcast/intelligence/corpus_sync.py", "import sys\nsys.exit(1)\n")
    _, first, _ = _commit(repo)
    (repo / "more.txt").write_text("more\n")
    subprocess.run(["git", "add", "more.txt"], cwd=repo, check=True)
    _, second, _ = _commit(repo)
    assert "corpus export skipped" in first
    assert "corpus export skipped" not in second, "the same advice on every commit trains people to ignore it"


@pytest.mark.parametrize("step", ["repo-surgeon probe"])
def test_every_bounded_step_is_named_in_its_timeout_message(step, tmp_path):
    repo = _repo(tmp_path)
    _stub(repo, "scripts/repo_surgeon_probe.py", HANG)
    _, out, _ = _commit(repo, PF_HOOK_TIMEOUT="1")
    assert step in out
