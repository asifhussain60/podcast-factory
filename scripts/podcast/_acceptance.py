#!/usr/bin/env python3
"""Helper for reading and idempotently marking acceptance-criteria.md rows.

Used by the phase-runner harness (scripts/podcast/phases/) to surface
progress without human intervention. Every operation is idempotent:
re-marking an already-checked row is a no-op; re-reading produces stable
output.

The acceptance file format this helper targets:
    - [ ] **P1.4** ✅ first bullet of task P1.4
    - [x] **P1.4** ✅ second bullet (already done)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from _paths import REPO_ROOT

DEFAULT_ACCEPTANCE_FILE = REPO_ROOT / "_workspace" / "plan" / "operations" / "per-book-ship-checklist.md"

# Matches a row like:  - [ ] **P1.4** ✅ rest of line
ROW_RE = re.compile(r"^(- \[)([ x])(\] \*\*)(P\d+(?:\.\d+\w?)?)(\*\*[^\n]*)$", re.MULTILINE)


@dataclass(frozen=True)
class Row:
    line_no: int          # 1-indexed
    full_line: str
    task_id: str
    checked: bool
    text_after_id: str    # everything after `**P1.4**` including the ✅ prefix


def find_rows(text: str, task_id: str | None = None) -> list[Row]:
    """Return all rows in `text`, optionally filtered by task_id (e.g., 'P1.4')."""
    out: list[Row] = []
    for m in ROW_RE.finditer(text):
        rid = m.group(4)
        if task_id is not None and rid != task_id:
            continue
        line_no = text.count("\n", 0, m.start()) + 1
        full_line = text[m.start():m.end()]
        out.append(
            Row(
                line_no=line_no,
                full_line=full_line,
                task_id=rid,
                checked=(m.group(2) == "x"),
                text_after_id=m.group(5),
            )
        )
    return out


def count_checked(text: str, task_id: str) -> tuple[int, int]:
    """Return (checked_count, total_count) for the given task_id."""
    rows = find_rows(text, task_id=task_id)
    checked = sum(1 for r in rows if r.checked)
    return checked, len(rows)


def is_task_complete(text: str, task_id: str) -> bool:
    checked, total = count_checked(text, task_id)
    return total > 0 and checked == total


def mark_task_rows(
    text: str,
    task_id: str,
    *,
    text_contains: str | None = None,
) -> tuple[str, int]:
    """Mark every `- [ ]` row for `task_id` as `- [x]`.

    If `text_contains` is given, only marks rows whose post-id text contains
    that substring (used by phase runners to target specific bullets).

    Returns `(new_text, n_marked)`. Idempotent: rows already `[x]` are
    untouched and not counted.
    """
    marked = 0

    def _flip(m: re.Match) -> str:
        nonlocal marked
        rid = m.group(4)
        if rid != task_id:
            return m.group(0)
        if m.group(2) == "x":
            return m.group(0)  # already checked
        if text_contains is not None and text_contains not in m.group(5):
            return m.group(0)
        marked += 1
        return f"{m.group(1)}x{m.group(3)}{m.group(4)}{m.group(5)}"

    new_text = ROW_RE.sub(_flip, text)
    return new_text, marked


def mark_task_rows_in_file(
    task_id: str,
    *,
    text_contains: str | None = None,
    acceptance_file: Path = DEFAULT_ACCEPTANCE_FILE,
) -> int:
    """File-level idempotent mark. Returns number of rows newly marked.

    Atomic-ish: reads the file, mutates in memory, writes back. If 0 rows are
    newly marked, the file is NOT rewritten (preserves mtime for downstream
    `mtime`-based change detection).
    """
    text = acceptance_file.read_text()
    new_text, n_marked = mark_task_rows(text, task_id, text_contains=text_contains)
    if n_marked > 0:
        acceptance_file.write_text(new_text)
    return n_marked


def append_evidence(
    text: str,
    task_id: str,
    *,
    text_contains: str,
    evidence: str,
) -> str:
    """Append ` — <evidence>` to a single matching row IF the row doesn't
    already contain the evidence string. Used by phase runners to leave a
    breadcrumb of how the row was verified. Idempotent.

    Targets the FIRST matching row (most phases have one canonical evidence
    bullet they want to attach proof to).
    """
    if evidence in text:
        return text  # already present; idempotent no-op

    def _append(m: re.Match) -> str:
        rid = m.group(4)
        if rid != task_id or text_contains not in m.group(5):
            return m.group(0)
        if " — " in m.group(5) and evidence in m.group(5):
            return m.group(0)
        appended = m.group(5).rstrip() + f" — {evidence}"
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{appended}"

    # Replace only the first match
    return ROW_RE.sub(_append, text, count=1)
