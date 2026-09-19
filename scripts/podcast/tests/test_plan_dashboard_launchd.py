"""The admin site's auto-start job must be able to find `node`.

Live evidence, 2026-09-19: `launchctl print` for com.asif.podcast-factory.plan-dashboard showed 8,334 runs,
last exit code 127 (command not found), and a 21 MB error log of "command not found: node". The generated plist
runs `zsh -lc` with PATH hard-coded to /opt/homebrew/bin, but node lives under nvm
(~/.nvm/versions/node/<version>/bin) which only nvm.sh puts on PATH. The tracked generator now sources nvm and
throttles restarts so a future failure cannot spin thousands of times.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "plan-dashboard-launchd.sh"


def _plist(tmp_path: Path) -> dict:
    out = subprocess.run(
        ["bash", str(SCRIPT), "print-plist"],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(tmp_path), "PLAN_DASHBOARD_PORT": "4399"},
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    return plistlib.loads(out.stdout.encode())


def test_print_plist_is_valid_and_writes_nothing(tmp_path):
    data = _plist(tmp_path)
    assert data["Label"] == "com.asif.podcast-factory.plan-dashboard"
    assert not (tmp_path / "Library").exists(), "print-plist must be read-only"


def test_the_command_loads_nvm_before_it_needs_node(tmp_path):
    command = _plist(tmp_path)["ProgramArguments"][2]
    assert "nvm.sh" in command
    assert command.index("nvm.sh") < command.index("node scripts/regenerate-snapshots.mjs")
    assert "--port 4399" in command  # the configured port survives


def test_a_crash_loop_is_throttled(tmp_path):
    assert _plist(tmp_path).get("ThrottleInterval", 0) >= 60


def test_the_static_path_still_covers_homebrew(tmp_path):
    assert "/opt/homebrew/bin" in _plist(tmp_path)["EnvironmentVariables"]["PATH"]


@pytest.mark.skipif(not (Path.home() / ".nvm" / "nvm.sh").exists(), reason="nvm is not installed on this machine")
def test_node_is_actually_found_from_the_jobs_stripped_environment(tmp_path):
    """The real check: the exact prefix, run the way launchd runs it (login zsh, minimal PATH, no nvm loaded)."""
    command = _plist(Path.home())["ProgramArguments"][2]
    prefix = command.split("cd ", 1)[0]
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh not available")
    result = subprocess.run(
        [zsh, "-lc", prefix + " command -v node"],
        capture_output=True,
        text=True,
        env={"HOME": str(Path.home()), "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
        timeout=60,
    )
    assert result.returncode == 0 and "node" in result.stdout, result.stderr
