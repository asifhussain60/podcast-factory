"""_phase_progress.py — which chapter is a long pass on, and how long is left.

isaf-al-talib, 2026-09-18: the polish and reconcile passes ran ~7.5 hours over 33 chapters with no
per-chapter progress line anywhere; the chapter number could only be recovered from the cost ledger's
step names, and the status card's ETA swung by hours because it extrapolated from phase percentages.

Each finished chapter is recorded in `_system/phase-progress.json`, and the estimate is the MEDIAN of the
most recent measured per-chapter times times the chapters left. Nothing is guessed: one measurement gives
no estimate, and a record that has stopped moving says how long ago it last did instead of posing as live.
Recording is an observer — it never raises into the pass it is watching.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

FILE = "phase-progress.json"
_RECENT = 8  # measured chapters the estimate looks at: recent pace, not the whole run's average
_STALE_AFTER_S = 600


def _path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / FILE


def load(book_dir: Path) -> dict[str, Any] | None:
    try:
        return json.loads(_path(book_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(book_dir: Path, data: dict[str, Any]) -> bool:
    path = _path(book_dir)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def begin_pass(book_dir: Path, name: str, total: int, *, now: Callable[[], float] = time.time) -> bool:
    """Start (or restart) tracking `name`. Replaces whatever pass was recorded before."""
    t = now()
    return _write(
        book_dir, {"pass": name, "total": total, "done": 0, "label": "", "started": t, "updated": t, "seconds": []}
    )


def item_done(book_dir: Path, name: str, done: int, label: str, *, now: Callable[[], float] = time.time) -> bool:
    """Record that `done` items are finished; the time since the previous event is one measurement."""
    data = load(book_dir)
    if not data or data.get("pass") != name:
        return False
    t = now()
    data["seconds"] = [*data.get("seconds", []), round(t - float(data["updated"]), 1)][-(_RECENT * 4) :]
    data.update(done=done, label=label, updated=t)
    return _write(book_dir, data)


def eta_seconds(entry: dict[str, Any] | None) -> float | None:
    """Median of the recent per-item times x items left; None until two items have been measured."""
    if not entry:
        return None
    seconds = entry.get("seconds", [])
    if len(seconds) < 2:
        return None
    left = max(int(entry["total"]) - int(entry["done"]), 0)
    return statistics.median(seconds[-_RECENT:]) * left


def _human(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def progress_line(book_dir: Path, *, now: Callable[[], float] = time.time) -> str | None:
    """`polish · chapter 12 of 33 · about 2h 10m left · The Pillar of Religion`, or None when nothing is recorded."""
    entry = load(book_dir)
    if not entry or not entry.get("done"):
        return None
    parts = [f"{entry['pass']} · {entry['done']} of {entry['total']}"]
    eta = eta_seconds(entry)
    if eta is not None:
        parts.append(f"about {_human(eta)} left")
    age = now() - float(entry["updated"])
    if age > _STALE_AFTER_S:
        parts.append(f"last one {_human(age)} ago")
    if entry.get("label"):
        parts.append(str(entry["label"])[:28])
    return " · ".join(parts)


def clear(book_dir: Path) -> None:
    _path(book_dir).unlink(missing_ok=True)
