"""What 0book-illustrate carries from an earlier run, and what it must redo.

Lives beside `_book_illustrate` rather than in it because that module sits at its
DR-005 grandfathered ceiling (695 lines) — the same reason `_tool_cost` lives
beside `_cost_ledger`.

A section whose classification or rendering raised used to be swallowed with one
stderr line and dropped from the manifest, so the manifest listed successes only.
The "already complete" check then asked whether every LISTED diagram was on disk —
true of an all-successes list, and true (`all([])`) of an empty one — and declared
the phase finished. The missing diagram was never drawn again without `--force`,
which re-buys every diagram in the book to recover one.

Now a failed section is RECORDED in the manifest as `{"section", "failed"}`, a
manifest carrying one is unfinished, an empty manifest is unfinished, and the next
run redraws only what is missing: every entry whose SVG is on disk is carried
forward untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def failed_entry(section: str, exc: BaseException, *, report=sys.stderr.write) -> dict[str, Any]:
    """The manifest record of a section that raised — its name and why — reported as it is made."""
    reason = f"{type(exc).__name__}: {exc}"
    report(f"  [illustrate] section {section[:50]!r} failed ({reason}), recorded for the next run\n")
    return {"section": section, "failed": reason}


def resume_state(manifest_path: Path, diagram_dir: Path) -> tuple[list[dict[str, Any]], bool]:
    """(entries whose diagram is on disk, whether the manifest is finished).

    Finished means the manifest names at least one diagram, every entry has its
    SVG on disk, and none is a failure record. An unreadable manifest carries
    nothing forward and is not finished.
    """
    try:
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return [], False
    if not isinstance(prior, list):
        return [], False
    done = [
        e
        for e in prior
        if isinstance(e, dict) and e.get("svg_path") and (diagram_dir / Path(e["svg_path"]).name).exists()
    ]
    return done, bool(prior) and len(done) == len(prior)
