"""_book_decisions.py — the forks the pipeline settles on the author's behalf.

Some choices a book run makes are not defects and not preferences. They are real
forks the source underdetermines: an unvowelled `قد علمت` that reads equally as
"I knew" and "you knew"; two defensible English renderings of one Arabic term;
whether the source's own opening stands as a chapter or as an appendix. The
pipeline has exactly three things it can do with one, and two of them are wrong:

  ask       — stops a multi-hour autonomous run to pose a question the author
              cannot answer without the scan open. This is what was happening.
  guess     — picks silently, and the book acquires a choice nobody can trace,
              which for a published translation is the worse failure of the two.
  decide    — applies the stated default, RECORDS what it chose, what it passed
              over, and the evidence it had, and lets the author overrule it
              later by editing one field.

This module is the third. It is deliberately not a findings ledger: a finding is
something wrong, a decision is something settled. They are reviewed differently
and they must not share a list, or the real defects drown.

WHY `resolve` AND NOT JUST `record`
-----------------------------------
A ledger that only records is decorative — the author reads it, disagrees, and
has no way to make the disagreement stick through the next compose. So producers
call ``resolve``, which returns the author's ``override`` when one is present and
the pipeline's default otherwise, and records the outcome either way. Editing
``override`` in the sidecar and re-running is the whole override protocol; there
is no second mechanism to keep in sync.

Same durability contract as ``_book_edits`` and ``_book_bridges``: the record
lives in ``_system/book-decisions.json``, survives every recompose, and is keyed
so replaying is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SIDECAR_NAME = "book-decisions.json"
SCHEMA = "book.decisions/v1"


def sidecar_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / SIDECAR_NAME


def load_decisions(book_dir: Path) -> dict[str, Any]:
    path = sidecar_path(book_dir)
    if not path.exists():
        return {"schema": SCHEMA, "decisions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # A corrupt sidecar must never take a good run down with it. The run
        # re-decides from its defaults, which is exactly what an absent file does.
        return {"schema": SCHEMA, "decisions": []}
    if not isinstance(data, dict) or not isinstance(data.get("decisions"), list):
        return {"schema": SCHEMA, "decisions": []}
    return data


def _write(book_dir: Path, data: dict[str, Any]) -> Path:
    path = sidecar_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["schema"] = SCHEMA
    data["decisions"] = sorted(data["decisions"], key=lambda d: (d.get("phase", ""), d.get("key", "")))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def resolve(
    book_dir: Path,
    *,
    key: str,
    default: str,
    alternatives: list[str] | None = None,
    why: str = "",
    evidence: str = "",
    phase: str = "",
) -> str:
    """Settle one fork and return what the book should use.

    Returns the author's ``override`` if the sidecar carries one for ``key``,
    otherwise ``default``. Either way the entry is (re)written with the current
    reasoning, so the ledger always describes the run that actually happened
    rather than the first run that ever happened.

    ``key`` is a stable slug (``chapter-07-qad-alimtu-person``), never a line
    number — the whole point is that it survives a recompose that moves the text.
    """
    data = load_decisions(book_dir)
    existing = next((d for d in data["decisions"] if d.get("key") == key), None)
    override = (existing or {}).get("override") or ""
    chosen = override or default
    entry = {
        "key": key,
        "phase": phase,
        "chose": chosen,
        "default": default,
        "alternatives": list(alternatives or []),
        "why": why,
        "evidence": evidence,
        "override": override,
        "source": "author override" if override else "pipeline default",
    }
    data["decisions"] = [d for d in data["decisions"] if d.get("key") != key] + [entry]
    _write(Path(book_dir), data)
    return chosen


def open_decisions(book_dir: Path) -> list[dict[str, Any]]:
    """Entries the author has not yet ruled on — i.e. still the pipeline's call."""
    return [d for d in load_decisions(book_dir)["decisions"] if not d.get("override")]


def render_decisions(book_dir: Path, *, limit: int = 0) -> str:
    """Plain-English block for the finalize halt. Empty string when there are none.

    Deliberately prose and not a table: each entry needs its evidence line to be
    readable, and a table cell is where a reason goes to die.
    """
    decisions = load_decisions(book_dir)["decisions"]
    if not decisions:
        return ""
    shown = decisions[:limit] if limit else decisions
    lines = [
        f"The edition made {len(decisions)} call{'s' if len(decisions) != 1 else ''} the source "
        "does not settle. Each stands unless you say otherwise — set `override` on the entry in "
        "_system/book-decisions.json and re-run the phase named beside it.",
        "",
    ]
    for d in shown:
        mark = "ruled by you" if d.get("override") else "pipeline default"
        lines.append(f"- {d.get('key')} [{mark}] — chose: {d.get('chose')}")
        if d.get("alternatives"):
            lines.append(f"    passed over: {', '.join(d['alternatives'])}")
        if d.get("why"):
            lines.append(f"    why: {d['why']}")
        if d.get("evidence"):
            lines.append(f"    evidence: {d['evidence']}")
    if limit and len(decisions) > limit:
        lines.append(f"- … and {len(decisions) - limit} more in _system/{SIDECAR_NAME}")
    return "\n".join(lines)
