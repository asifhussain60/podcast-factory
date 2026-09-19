"""_finalize_failure.py — what a failed finalize gate tells the watchdog.

`watch_orchestrator.sh` halts instead of retrying exactly when the failed phase recorded a
`manual_fallback` (see `_needs_human_fix`). The G1-G7 gates are deterministic checks over the
book on disk: a gate that fails on this input fails identically on the next launch, so a
finalize failure is always a job for a person. Without a fallback the watchdog retried G13
and G14 up to 20 times each on isaf-al-talib.
"""

from __future__ import annotations

import re

_FAIL_LINE = re.compile(r"^FAIL\s+\[(?P<gate>[^\]]+)\]\s*(?P<msg>.*)$")
_MAX_LINES = 6
_MAX_LINE_CHARS = 200


def finalize_fallback(slug: str, validator_stdout: str) -> str:
    """Human-readable fix instructions; never empty (an empty fallback reads as 'retry')."""
    failing = []
    for raw in validator_stdout.splitlines():
        m = _FAIL_LINE.match(raw.strip())
        if m:
            failing.append(f"[{m['gate']}] {m['msg']}"[:_MAX_LINE_CHARS])
    if failing:
        shown = failing[:_MAX_LINES]
        more = f" (+{len(failing) - len(shown)} more)" if len(failing) > len(shown) else ""
        what = "Failing ship gate(s): " + "; ".join(shown) + more + "."
    else:
        what = "The ship-gate validator failed without naming a gate — run it directly to see why."
    return (
        f"{what} Fix the cause, then: python3 scripts/podcast/orchestrate_book.py --resume {slug}"
        f" (or validate first: python3 scripts/podcast/validate_ship_ready.py {slug})"
    )
