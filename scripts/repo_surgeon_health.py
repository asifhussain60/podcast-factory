"""repo_surgeon_health.py — checks for things that quietly rot: stuck books and an untriaged findings ledger.

Both are P2 by design. A halt can be a deliberate wait for a person and an old finding can still be true, so
neither may block a commit — but on 2026-09-19 eight books had sat in failed/halted/pending for up to three
months and ~740 top-severity findings had gone untriaged, and nothing anywhere said so. Their own module because
repo_surgeon_probe.py is at its DR-005 size ceiling.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

STUCK_AFTER_DAYS = 14
BACKLOG_AFTER_DAYS = 45
_NOT_STUCK_PHASE_STATUS = {"completed", "skipped", "done"}
_OPEN_RESOLUTIONS = {"flagged", "carried", None}


def _parse(value) -> float | None:
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _json_or_none(text: str):
    """Parsed JSON, or None when the text is not JSON — a half-written or garbled file is not a book's problem
    to report here, and it must not crash a check that runs on every commit."""
    try:
        return json.loads(text)
    except ValueError:
        return None


def _git_commit_time(root: Path, path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path)], cwd=root, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        return float(out) if out else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _last_activity(root: Path, state_path: Path, state: dict) -> float | None:
    """Latest phase timestamp in the state file, or its last commit. Never file mtime: a fresh checkout resets
    every mtime to 'now', which would make every book look active."""
    stamps = [
        t
        for block in (state.get("phases") or {}).values()
        if isinstance(block, dict)
        for t in (_parse(block.get("ts_started")), _parse(block.get("ts_completed")))
        if t is not None
    ]
    committed = _git_commit_time(root, state_path)
    if committed is not None:
        stamps.append(committed)
    return max(stamps) if stamps else None


def check_stuck_books(probe) -> None:
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    for state_path in sorted((probe.root / "content").glob("*/*/_system/orchestrator-state.json")):
        rel = state_path.relative_to(probe.root).as_posix()
        if rel.startswith("content/_") or "/_archive/" in rel:
            continue
        state = _json_or_none(state_path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(state, dict):
            continue
        if state.get("status") == "published" or state.get("phase") == "done":
            continue
        if state.get("phase_status") in _NOT_STUCK_PHASE_STATUS or not state.get("phase_status"):
            continue
        last = _last_activity(probe.root, state_path, state)
        if last is None or (now - last) / 86400 < STUCK_AFTER_DAYS:
            continue
        days = int((now - last) / 86400)
        slug = state_path.parents[1].name
        probe.add(
            "P2",
            "HL-STUCK",
            f"{slug} has been {state.get('phase_status')} at {state.get('phase')} for {days} days with no activity — "
            "resume it, or archive it, or record why it waits",
            rel,
            fingerprint=f"HL-STUCK:{slug}",
        )


def check_findings_backlog(probe) -> None:
    ledger = probe.root / "_learning" / "findings.jsonl"
    if not ledger.exists():
        return
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    old = 0
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        row = _json_or_none(line)
        if not isinstance(row, dict) or row.get("severity") != "P0" or row.get("resolution") not in _OPEN_RESOLUTIONS:
            continue
        ts = _parse(row.get("ts"))
        if ts is not None and (now - ts) / 86400 >= BACKLOG_AFTER_DAYS:
            old += 1
    if old:
        probe.add(
            "P2",
            "HL-BACKLOG",
            f"{old} P0 finding(s) have been open for over {BACKLOG_AFTER_DAYS} days — triage with: "
            "python3 scripts/findings_triage.py (dry run), then --apply",
            "_learning/findings.jsonl",
            fingerprint="HL-BACKLOG",
        )
