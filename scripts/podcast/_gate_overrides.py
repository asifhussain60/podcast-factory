"""_gate_overrides.py — book-level human override lookup, shared by the gate
validators.

Extracted from `validate_ship_ready.py` (2026-08-17) when `validate_book_ready.py`
needed the identical check for B3 book-arabic-coverage: a second consumer of the
same logic is the point past which duplication should stop, not the point at
which it's copy-pasted again.
"""

from __future__ import annotations

import json
from pathlib import Path


def gate_override(workspace: Path, gate: str) -> dict | None:
    """Return a matching book-level human override for `gate`, if one is
    recorded in orchestrator-state.json's top-level `human_overrides` list.

    Requires `gate` + `reason` + `decided_by` to all be present — an override
    is never inferred, only explicitly recorded and attributed. Distinct from
    G7's per-chapter override (phases.per-chapter.human_override): this is for
    gates whose finding is book-wide, not attributable to one chapter.
    """
    state_path = workspace / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text())
    except Exception:
        return None
    for override in state.get("human_overrides") or []:
        if (
            isinstance(override, dict)
            and override.get("gate") == gate
            and override.get("reason")
            and override.get("decided_by")
        ):
            return override
    return None
