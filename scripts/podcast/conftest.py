"""No test under scripts/podcast may spend a model call.

Two `compose_book_v2(force=True)` tests reached the real `claude -p` three times
each — six paid calls per run — and stayed green, because every authoring caller
wraps its shell-out in `except Exception` and logs "skipped (non-fatal)". A test
cannot see a call it never made, so the guard sits at the one place every such
call passes through: the `subprocess.run` that `_authoring._core._run_claude_p`
performs. It replaces that module's view of `subprocess` only, never the global
module, so tests that shell out to git or node are untouched.

It raises a BaseException on purpose. An AssertionError would be swallowed by
the same `except Exception` that hid the calls in the first place.

A test that has replaced the global `subprocess.run` with its own fake (the
`_run_claude_p` unit tests do, via `mock.patch("subprocess.run")`), or has
pointed `CLAUDE_CMD` at its own fake executable (the run-log tests do), is
handed through: it is exercising the shell-out's plumbing, not spending. Only
the genuine `subprocess.run` of the genuine command is refused.

Opt out for one test with `@pytest.mark.real_claude` — a deliberate, named
decision, never the default.

Lives here rather than in tests/ because that directory is a package named
`tests`, and under `--import-mode=importlib` its conftest would register under
the same module name as the repo-root `tests/conftest.py` and abort collection.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

_REAL_RUN = subprocess.run


class RealModelCall(BaseException):
    """A test tried to run the real `claude -p`."""


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "real_claude: this test may shell out to the real `claude -p`")


@pytest.fixture(autouse=True)
def no_real_claude(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    if request.node.get_closest_marker("real_claude"):
        yield
        return

    import _authoring._core as core

    real_cmd = core.CLAUDE_CMD  # read at setup, before the test body can point it at a fake
    attempts: list[list[str]] = []

    def blocked(argv, *args, **kwargs):
        if subprocess.run is not _REAL_RUN or str(argv[0]) != real_cmd:  # the test brought its own fake
            return subprocess.run(argv, *args, **kwargs)
        attempts.append([str(a) for a in argv])
        raise RealModelCall(f"test reached real claude -p: {' '.join(str(a) for a in argv[:3])} ...")

    monkeypatch.setattr(core, "subprocess", SimpleNamespace(run=blocked, TimeoutExpired=subprocess.TimeoutExpired))
    yield
    if attempts:  # only reachable if a caller caught BaseException; still not allowed
        pytest.fail(f"test reached real claude -p {len(attempts)} time(s) and swallowed the refusal")
