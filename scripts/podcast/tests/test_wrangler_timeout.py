"""A wrangler call that never answers must fail, not hang.

Every `npx wrangler` invocation was an unbounded `subprocess.run` against a
network service. A stalled connection meant a pipeline phase that neither
finished nor failed — the one outcome the watchdog cannot act on, because a
process still alive and a process making progress look identical from outside.

Two things are pinned here: the shared helper stops a hung command inside its
deadline and reports it as a `WranglerTimeout`, and no call site opts out of the
helper. The second is a source scan on purpose — a new wrangler call added later
would otherwise reintroduce the defect with nothing to say so.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import _wrangler  # noqa: E402

#: The files the audit found holding untimed wrangler calls.
CALL_SITE_FILES = (
    "publish_to_listener.py",
    "upload_listener_media.py",
    "audio_parity.py",
    "r2_orphans.py",
    "sync_listener_work_groups.py",
    "_production_publish.py",
)


def _sleeping_wrangler(tmp_path: Path) -> Path:
    """A stand-in for `npx` that accepts any wrangler arguments and never answers."""
    stub = tmp_path / "npx"
    stub.write_text("#!/bin/sh\nsleep 60\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def test_a_wrangler_that_never_answers_is_stopped_at_its_deadline(tmp_path):
    stub = _sleeping_wrangler(tmp_path)

    started = time.monotonic()
    with pytest.raises(_wrangler.WranglerTimeout) as caught:
        _wrangler.run([str(stub), "wrangler", "d1", "execute"], timeout=1.0)
    elapsed = time.monotonic() - started

    assert elapsed < 20, f"the call ran {elapsed:.1f}s past a 1s deadline"
    assert "did not answer" in str(caught.value)
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)


def test_a_timeout_reaches_the_handlers_the_call_sites_already_have(tmp_path):
    """The call sites catch `RuntimeError` or `subprocess.SubprocessError` so one
    bad book does not strand the rest. A timeout must land in the same handler."""
    stub = _sleeping_wrangler(tmp_path)

    with pytest.raises(RuntimeError):
        _wrangler.run([str(stub)], timeout=0.5)
    with pytest.raises(subprocess.SubprocessError):
        _wrangler.run([str(stub)], timeout=0.5)


def test_the_default_deadline_is_resolved_when_the_call_is_made(tmp_path, monkeypatch):
    """Not bound into the signature's defaults, where nothing could change it."""
    stub = _sleeping_wrangler(tmp_path)
    monkeypatch.setattr(_wrangler, "DEFAULT_TIMEOUT", 0.5)

    started = time.monotonic()
    with pytest.raises(_wrangler.WranglerTimeout):
        _wrangler.run([str(stub)])
    assert time.monotonic() - started < 20


def test_a_command_that_answers_comes_back_normally(tmp_path):
    done = tmp_path / "npx"
    done.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    done.chmod(0o755)

    out = _wrangler.run([str(done), "wrangler", "whoami"])
    assert out.returncode == 0
    assert out.stdout.strip() == "ok"


@pytest.mark.parametrize("name", CALL_SITE_FILES)
def test_no_wrangler_call_bypasses_the_helper(name):
    """A bare `subprocess.run([... "wrangler" ...])` is the defect itself."""
    source = (SCRIPTS / name).read_text(encoding="utf-8")
    bare = re.findall(
        r"subprocess\.run\(\s*\[[^]]*?\"wrangler\"[^]]*?\]",
        source,
        re.DOTALL,
    )
    assert bare == [], f"{name} still calls wrangler without the shared deadline"


class TheComposerPublishStreamIsBoundedToo:
    """`publish_to_production.run` cannot use `_wrangler.run` — it streams output
    to a progress panel a person is watching, and `_wrangler.run` captures. It is
    still a wrangler call, so the wrapper's claim that EVERY invocation is bounded
    has to hold here too, or the claim is worse than no claim.
    """

    def test_a_silent_child_is_killed_at_the_deadline(self) -> None:
        import publish_to_production as P

        start = time.monotonic()
        with pytest.raises(_wrangler.WranglerTimeout):
            P.run([sys.executable, "-c", "import time; time.sleep(30)"], _Silent(), timeout=1.0)
        assert time.monotonic() - start < 10, "the deadline did not end it"

    def test_a_child_that_finishes_is_untouched(self) -> None:
        import publish_to_production as P

        assert P.run([sys.executable, "-c", "print('hi')"], _Silent(), timeout=30) == 0


class _Silent:
    def log(self, line: str) -> None:  # pragma: no cover - a sink
        pass
