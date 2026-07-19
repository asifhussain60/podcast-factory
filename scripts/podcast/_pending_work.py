"""_pending_work.py — the backlog a status card can show.

Work accumulates in conversation: a finding worth acting on, a refactor approved
but deferred, a standing step not yet run. Held only in a chat, it is invisible
the moment the session ends and unverifiable while it lasts — the reader has to
trust a recollection. This module gives that backlog a file, so the status card
can print it and anyone can read it without asking.

Deliberately small. An item is a line of plain English, a scope, and a state:
no owners, no priorities, no dates beyond when it was noticed. A backlog that
needs its own workflow stops being written to, and an unwritten backlog is worse
than none because it looks maintained.

Scope is either a book slug (work on one book) or ``pipeline`` (work on the
machinery). A card for a book shows that book's items plus the pipeline-wide
ones, since both stand between the book and being finished.

Pure: reads and writes one YAML file, no LLM, no network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SCOPE_PIPELINE = "pipeline"
STATUS_OPEN = "open"
STATUS_DOING = "doing"
STATUS_DONE = "done"
_OPEN_STATUSES = (STATUS_DOING, STATUS_OPEN)  # doing first — it is what is happening now

_BACKLOG = Path(__file__).resolve().parents[2] / "_workspace" / "plan" / "pending-work.yaml"


def backlog_path() -> Path:
    """The single backlog file. One per repo, not per book — most items span books."""
    return _BACKLOG


def read_items(path: Path | None = None) -> list[dict[str, Any]]:
    """Every item in the backlog. A missing or unreadable file is an empty backlog."""
    p = Path(path) if path else backlog_path()
    if not p.exists():
        return []
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else None
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def open_items(scope: str, path: Path | None = None) -> list[dict[str, Any]]:
    """Unfinished work for one scope plus the pipeline-wide items, in-progress first.

    Both belong on a book's card: a pipeline gap and a book gap equally stand
    between this book and being done.
    """
    wanted = {scope, SCOPE_PIPELINE}
    items = [
        i
        for i in read_items(path)
        if str(i.get("status", STATUS_OPEN)) in _OPEN_STATUSES and str(i.get("scope", SCOPE_PIPELINE)) in wanted
    ]
    return sorted(items, key=lambda i: _OPEN_STATUSES.index(str(i.get("status", STATUS_OPEN))))


def write_items(items: list[dict[str, Any]], path: Path | None = None) -> Path:
    """Replace the backlog. Callers read, edit, and write the whole list."""
    p = Path(path) if path else backlog_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "schema": "podcast.pending-work/v1",
        "items": items,
    }
    p.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


def resolve(item_id: str, path: Path | None = None) -> bool:
    """Mark one item done. Returns False when no such item exists."""
    items = read_items(path)
    for item in items:
        if str(item.get("id")) == item_id:
            item["status"] = STATUS_DONE
            write_items(items, path)
            return True
    return False


def main() -> int:  # pragma: no cover - thin CLI
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "done" and len(argv) == 2:
        return 0 if resolve(argv[1]) else 1
    scope = argv[0] if argv else SCOPE_PIPELINE
    for item in open_items(scope):
        print(f"[{item.get('status', STATUS_OPEN):5s}] {item.get('id', '?'):24s} {item.get('title', '')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
