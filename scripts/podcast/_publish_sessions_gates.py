"""publish_to_library.py's G1/G5 gates, for a Sessions-lane book.

A Sessions-lane book (content/Sessions/<slug>/, pipeline_mode="sessions_lane"
in orchestrator-state.json) never produces chapters/*.txt or episodes/*.txt —
those are the orchestrator's NotebookLM upload-bundle artifacts, and the
Sessions lane (scripts/podcast/sessions/*.py) has no equivalent step that
writes them. G1 (structure), G2 (pairs), G3 (sequential numbering) and G4
(build-clean) are ALL specifically about that upload bundle, so forcing a
Sessions book through them the normal way isn't a stricter check — it's a
check of files that were never going to exist. G2-G4 simply don't apply and
are reported n/a by the caller; this module supplies the two that need a real
Sessions-lane equivalent: G1 (does this book actually have finished content
to publish) and G5 (has the lane's own pipeline actually finished).

Split out of publish_to_library.py rather than inlined there, the same seam
that produced _publish_downstream.py: this file was already at the DR-005
600-line cap, and Sessions-lane structure/state checks are a self-contained
question a caller can import rather than grow the gate list in place.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def is_sessions_lane(workspace: Path) -> bool:
    """True if this book's own state file declares the Sessions lane."""
    state_path = workspace / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        return False
    try:
        return json.loads(state_path.read_text()).get("pipeline_mode") == "sessions_lane"
    except (OSError, ValueError):
        return False


def gate_g1_sessions_structure(workspace: Path, *, fail, ok) -> tuple[bool, int]:
    """The Sessions lane's own proof of real, finished structure: a composed
    book/book.md, at least one chapter-contracts/*.yml (what the Listener
    ingests as episodes), and at least one recorded episode under
    m4a/Episodes/. Returns (passed, episode_count) — episode_count substitutes
    for G1's normal `len(episodes)` in the caller's catalog/log lines.
    """
    book_md = workspace / "book" / "book.md"
    contracts_dir = workspace / "chapter-contracts"
    audio_dir = workspace / "m4a" / "Episodes"

    if not book_md.is_file() or not book_md.read_text(encoding="utf-8").strip():
        fail("G1", f"missing or empty book/book.md under {workspace}")
        return False, 0
    contracts = sorted(contracts_dir.glob("*.yml")) if contracts_dir.is_dir() else []
    if not contracts:
        fail("G1", f"no chapter-contracts/*.yml under {workspace}")
        return False, 0
    audio = sorted(p for p in audio_dir.glob("*") if p.is_file()) if audio_dir.is_dir() else []
    if not audio:
        fail("G1", f"no m4a/Episodes/* audio under {workspace}")
        return False, 0

    ok("G1", f"sessions lane: book.md + {len(contracts)} chapter-contract(s) + {len(audio)} episode audio file(s)")
    return True, len(contracts)


def gate_g5_sessions_state(workspace: Path, force: bool, *, fail, ok) -> bool:
    """The Sessions lane's own state checkpoint: `phases.sessions-apparatus`
    must report completed — the lane's equivalent of the orchestrator's
    phase=done/finalize checkpoint, since a Sessions book's top-level `phase`
    is always one of the lane's own five phase names and never matches G5's
    normal done/per-chapter/finalize check.
    """
    if force:
        ok("G5", "--force: state checkpoint skipped")
        return True
    state_path = workspace / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        fail("G5", f"orchestrator-state.json not found at {state_path}")
        return False
    state = json.loads(state_path.read_text())
    apparatus_status = ((state.get("phases") or {}).get("sessions-apparatus") or {}).get("status")
    if apparatus_status == "completed":
        ok("G5", "state.json phases.sessions-apparatus=completed")
        return True
    fail(
        "G5",
        f"sessions-apparatus not completed (status={apparatus_status!r}). "
        "Run scripts/podcast/sessions/apparatus.py first, or use --force to bypass.",
    )
    return False
