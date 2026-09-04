"""_wrangler.py — every wrangler call is bounded, and a hang says so.

Every `npx wrangler` invocation in this repo was an unbounded `subprocess.run`.
Wrangler talks to Cloudflare over the network, so any of them could sit forever
on a stalled connection: a publish, an R2 upload, a read-back, the work-group
sync. Unattended, that is a pipeline phase that never returns and a watchdog with
nothing to notice — the run neither finishes nor fails.

So every wrangler call goes through `run` here, and every one has a deadline. A
call that passes it raises `WranglerTimeout`, which names the command and the
bound it broke. The class inherits from BOTH `RuntimeError` and
`subprocess.SubprocessError` deliberately: the existing call sites already catch
one or the other to keep going past a single bad book or file, and a timeout
should reach the same handler rather than escape as a new kind of crash.

`DEFAULT_TIMEOUT` is resolved at CALL time, not bound into the signature's
defaults. A module-level constant captured as a keyword default cannot be changed
afterwards — not by a test, not by a caller — which is exactly the trap
`_verbatim_correct` fell into with its worker count.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Enough for a book import or a D1 read-back, short enough that a stalled
#: connection is reported the same day it happens.
DEFAULT_TIMEOUT = 600.0

#: R2 object transfers move whole recordings — the largest is ~300 MB — so they
#: get their own, longer bound rather than sharing the one above.
TRANSFER_TIMEOUT = 1800.0


class WranglerTimeout(RuntimeError, subprocess.SubprocessError):
    """A wrangler call did not finish inside its deadline."""


def run(
    argv: list[str],
    *,
    cwd: "Path | str | None" = None,
    timeout: "float | None" = None,
    check: bool = False,
    env: "dict[str, str] | None" = None,
) -> "subprocess.CompletedProcess[str]":
    """Run one wrangler command with output captured and a deadline enforced."""
    limit = DEFAULT_TIMEOUT if timeout is None else timeout
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=env,
            timeout=limit,
        )
    except subprocess.TimeoutExpired as error:
        raise WranglerTimeout(
            f"wrangler did not answer within {limit:.0f}s and was stopped: "
            f"{' '.join(argv[:5])}. Cloudflare may be unreachable; re-run when it is."
        ) from error
