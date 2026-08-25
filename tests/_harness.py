"""Shared harness for the three repo-surgeon test modules.

Every repo-surgeon check must be able to FAIL. The skill's own rule is "break the
thing it guards, confirm it fails, restore" — performed by hand, once, by whoever
added the check. That proves the check worked on the day it was written and nothing
thereafter. These tests make it permanent: each one builds a synthetic tree carrying
exactly one defect and asserts the check reports it, plus a clean-tree case asserting
it stays quiet, plus an empty-tree case asserting it cannot crash.

Why synthetic trees rather than the live repo: a test pinned to the repo's current
state fails the day somebody legitimately changes it, and a test that has to be
edited to stay green is one people learn to edit rather than read.

These helpers lived in duplicate at the top of two test modules. They are here so
the third does not make it a triplicate, and so a change to how a synthetic repo is
built cannot land in one copy and not the others.

A MODULE rather than conftest.py because pytest.ini sets `--import-mode=importlib`,
under which `tests/` is not on sys.path and `conftest` is not importable by name.
conftest.py holds the hooks that must be hooks; everything importable lives here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repo_surgeon_probe import Probe  # noqa: E402

# Every probe any test builds, for the coverage ratchet in conftest.py. Registering
# here rather than asking each test to opt in is the point: a new defect case counts
# toward coverage because it used the harness, not because anyone remembered.
PROBES: list[Probe] = []


def make_probe(tmp_path: Path, profile: dict, waivers: list | None = None) -> Probe:
    """A git repo, because several checks read the index rather than the disk."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    probe = Probe(root=tmp_path, profile=profile, waivers=waivers or [])
    PROBES.append(probe)
    return probe


def track(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    # `git grep` reads the working tree only for tracked paths, and an index with
    # no commit behind it is enough — but the files must be ADDED, which is the
    # scope every gate in this repo runs at.


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def ids(probe: Probe) -> list[str]:
    return [f.id for f in probe.findings]
