"""The agent-spec mirror gate — that it passes on a fresh clone AND can still fail.

`scripts/podcast/sync-agent-wrappers.sh` propagates `infra/claude-agents/*.md`
(canonical) to three generated homes: `.github/agents/*.agent.md` and
`.codex/agents/*.toml`, both tracked, and `.claude/agents/*.md`, which is the
per-repo activation copy Claude Code reads at runtime and is GITIGNORED.

The gate was wired into CI on 2026-08-05 and failed every run from that day until
2026-08-11, because `--check` compared against the activation copy unconditionally.
`.claude/` cannot exist on a fresh clone, so a runner reported all 22 specs as
drifted and the pipeline job was unconditionally red. Two consequences, and the
second is the expensive one: the gate carried no signal, and a permanently red
job hid a real listener typecheck break for a day.

Check mode also called `mkdir -p` on the directory it was auditing, so the first
run created an empty `.claude/agents/` and every later run still flagged all 22 —
a check that writes to the tree it inspects cannot converge.

The fix skips the activation comparison in check mode when the directory is
absent, which is the guard the reverse sweep in the same file already applied.
The DANGER in that fix is making the gate always-green, which is the same disease
as always-red — so most of what follows asserts the gate still FAILS: cases 3 and
4 are the ones that matter, and they fail without the guard's companion logic.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "podcast" / "sync-agent-wrappers.sh"
CODEX_GEN = REPO_ROOT / "scripts" / "podcast" / "sync_codex_agents.py"


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(root / "scripts" / "podcast" / "sync-agent-wrappers.sh"), *args],
        capture_output=True,
        text=True,
        cwd=root,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal tree with two canonical specs, synced to every mirror.

    Deliberately NOT the real repo: the activation directory is live runtime
    state on a developer's machine, and a test that renames it to prove a point
    would sign the operator out of their own agent roster if it died halfway.
    """
    root = tmp_path / "repo"
    (root / "scripts" / "podcast").mkdir(parents=True)
    (root / "infra" / "claude-agents").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts" / "podcast" / SCRIPT.name)
    shutil.copy(CODEX_GEN, root / "scripts" / "podcast" / CODEX_GEN.name)

    for name in ("alpha", "beta"):
        (root / "infra" / "claude-agents" / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: fixture spec\n---\n\ncanonical {name}\n",
            encoding="utf-8",
        )

    synced = _run(root, "sync")
    assert synced.returncode == 0, f"fixture sync failed: {synced.stderr}"
    assert (root / ".claude" / "agents" / "alpha.md").is_file()
    return root


def test_passes_when_everything_is_in_sync(repo: Path) -> None:
    assert _run(repo, "--check").returncode == 0


def test_passes_on_a_fresh_clone_with_no_activation_directory(repo: Path) -> None:
    """The CI case. A runner has no `.claude/` and no Claude Code runtime."""
    shutil.rmtree(repo / ".claude")
    result = _run(repo, "--check")
    assert result.returncode == 0, (
        "the mirror gate fails on a tree without the gitignored activation copy — "
        f"this is the CI-always-red bug:\n{result.stderr}"
    )


def test_still_fails_on_a_fresh_clone_when_a_TRACKED_mirror_drifted(repo: Path) -> None:
    """The gate must keep its teeth in CI — this is what the fix must not cost.

    Skipping the activation copy is only safe because the two TRACKED mirrors are
    still compared. If this passes, the gate has been made worthless.
    """
    shutil.rmtree(repo / ".claude")
    (repo / ".github" / "agents" / "alpha.agent.md").write_text("tampered\n", encoding="utf-8")
    result = _run(repo, "--check")
    assert result.returncode != 0, "a drifted .github wrapper went unreported on a fresh clone"
    assert "alpha" in result.stderr


def test_still_fails_locally_when_the_activation_copy_is_stale(repo: Path) -> None:
    """The local value the gate was built for is preserved.

    A stale activation copy is what Claude Code would actually invoke, so on a
    machine that HAS the directory this must still be caught.
    """
    (repo / ".claude" / "agents" / "alpha.md").write_text("stale runtime copy\n", encoding="utf-8")
    result = _run(repo, "--check")
    assert result.returncode != 0, "a stale activation copy went unreported"
    assert "activation copy" in result.stderr


def test_still_fails_when_a_retired_agent_lingers_in_a_mirror(repo: Path) -> None:
    """The reverse sweep — a generated copy with no canonical source is an orphan."""
    (repo / ".github" / "agents" / "ghost.agent.md").write_text("retired\n", encoding="utf-8")
    result = _run(repo, "--check")
    assert result.returncode != 0, "an orphaned wrapper went unreported"
    assert "ORPHAN" in result.stderr


def test_check_mode_writes_nothing(repo: Path) -> None:
    """A check that mutates the tree it audits can never converge.

    This is why re-running the gate did not clear the drift: `mkdir -p` created an
    empty activation directory on the first run, and every run after compared
    against it.
    """
    shutil.rmtree(repo / ".claude")
    _run(repo, "--check")
    assert not (repo / ".claude").exists(), "check mode created the directory it was auditing"


def test_sync_mode_still_creates_the_activation_copy(repo: Path) -> None:
    """The guard is scoped to check mode — sync must still provision a fresh clone."""
    shutil.rmtree(repo / ".claude")
    assert _run(repo, "sync").returncode == 0
    assert (repo / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8") == (
        repo / "infra" / "claude-agents" / "alpha.md"
    ).read_text(encoding="utf-8")


def test_a_brand_new_agent_reaches_BOTH_mirrors_in_one_sync(repo: Path) -> None:
    """One sync run must leave a new agent invokable, not just mirrored.

    A separate bug from the CI one, found while fixing it and fixed with it: the
    branch that CREATED a missing `.github` wrapper used to `continue` past the
    activation sync, so the run that introduced an agent wrote the tracked mirror
    and not the runtime copy. The agent existed, the gate said the wrapper was
    fine, and Claude Code could not invoke it until sync happened to run again.
    """
    (repo / "infra" / "claude-agents" / "gamma.md").write_text(
        "---\nname: gamma\ndescription: brand new spec\n---\n\ncanonical gamma\n",
        encoding="utf-8",
    )

    assert _run(repo, "sync").returncode == 0

    wrapper = repo / ".github" / "agents" / "gamma.agent.md"
    activation = repo / ".claude" / "agents" / "gamma.md"
    assert wrapper.is_file(), "the tracked wrapper was not created"
    assert activation.is_file(), (
        "the new agent reached .github/agents but not the runtime activation copy — "
        "it would be uninvokable until sync ran a second time"
    )
    assert _run(repo, "--check").returncode == 0, "one sync must leave the gate green"
