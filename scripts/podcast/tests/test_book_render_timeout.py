"""A stuck book render must end, and it must take its Chromium tree with it.

`build_book_pdf` shelled out to the Playwright renderer with no timeout, so a
Chromium that never returned held the phase open forever. Worse, the child was in
the pipeline's own process group: killing the parent left the browser and its
helpers running, and five abandoned profile directories in temp were the evidence
that this had already happened.

The render is now bounded, the child starts its own session, and a render that
passes the bound has its whole group killed before the failure is raised. Both
halves are asserted here — a test that only checked the raise would pass with the
browser still running.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from _authoring._core import AuthoringError  # noqa: E402
from build_book_pdf import RENDER_TIMEOUT, _run_renderer  # noqa: E402


def _hanging_renderer(tmp_path: Path) -> tuple[list[str], Path]:
    """A stand-in that spawns a grandchild and then never returns.

    The grandchild stands for the Chromium helper processes: it is what proves
    the whole group was killed rather than just the command that was launched.
    """
    pidfile = tmp_path / "grandchild.pid"
    script = tmp_path / "render-stub.sh"
    script.write_text(
        f"#!/bin/sh\nsleep 300 &\necho $! > {pidfile}\nwait\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return [str(script)], pidfile


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_the_default_render_bound_is_fifteen_minutes():
    assert RENDER_TIMEOUT == 900


def test_a_render_that_never_returns_fails_inside_its_bound(tmp_path):
    argv, _ = _hanging_renderer(tmp_path)

    started = time.monotonic()
    with pytest.raises(AuthoringError) as caught:
        _run_renderer(argv, cwd=tmp_path, timeout=1.0)
    elapsed = time.monotonic() - started

    assert elapsed < 30, f"the render ran {elapsed:.1f}s past a 1s bound"
    assert caught.value.phase == "0book-render"
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)


def test_the_timeout_is_transient_so_the_watchdog_may_retry_it(tmp_path):
    """No `manual_fallback`: a hung browser is a thing to try again, not a thing
    for a person to go and fix by hand."""
    argv, _ = _hanging_renderer(tmp_path)
    with pytest.raises(AuthoringError) as caught:
        _run_renderer(argv, cwd=tmp_path, timeout=1.0)
    assert caught.value.manual_fallback == ""


def test_nothing_of_the_render_survives_the_timeout(tmp_path):
    argv, pidfile = _hanging_renderer(tmp_path)

    with pytest.raises(AuthoringError):
        _run_renderer(argv, cwd=tmp_path, timeout=1.0)

    assert pidfile.exists(), "the stub never got far enough to spawn its grandchild"
    grandchild = int(pidfile.read_text().strip())

    for _ in range(50):
        if not _alive(grandchild):
            break
        time.sleep(0.1)
    else:
        os.kill(grandchild, signal.SIGKILL)
        pytest.fail(f"pid {grandchild} outlived the render that started it")


def test_a_render_that_finishes_comes_back_normally(tmp_path):
    script = tmp_path / "quick.sh"
    script.write_text("#!/bin/sh\necho rendered\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)

    proc = _run_renderer([str(script)], cwd=tmp_path)
    assert proc.returncode == 0
    assert "rendered" in proc.stdout


def test_a_failing_render_is_returned_rather_than_raised(tmp_path):
    """The caller reads `returncode` to tell a missing Chromium (3) from any
    other failure, so a non-zero exit must still come back as a result."""
    script = tmp_path / "boom.sh"
    script.write_text("#!/bin/sh\necho nope >&2\nexit 3\n", encoding="utf-8")
    script.chmod(0o755)

    proc = _run_renderer([str(script)], cwd=tmp_path)
    assert proc.returncode == 3
    assert "nope" in proc.stderr
