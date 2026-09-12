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

An audiobook (content/Audiobook/<slug>/) runs through this SAME lane — same
pipeline_mode, same phase names (sessions-apparatus, sessions-read-along, ...)
— because it is built by the same scripts/podcast/sessions/*.py tooling. It
diverges at exactly one place: a recorded lecture is naturally cut into
topic-sized chapter-contracts, but a narrated novel is one continuous reading
with no topic boundaries to contract, so it never has a chapter-contracts/
directory. Its finished chapter set is recorded instead in the schema-versioned
`_system/audiobook-chapters.json` (episode number, audio file, timestamps).
Before this file recognised that manifest, G1 saw zero chapter-contracts and
refused to publish every audiobook outright — see White Nights, the case that
surfaced it (2026-09-12).

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


def _audiobook_chapter_count(workspace: Path) -> int | None:
    """The chapter count from `_system/audiobook-chapters.json`, or None if
    the file is absent, unparseable, or carries no chapters. An audiobook has
    no chapter-contracts (see module docstring), so this is its equivalent
    proof of a finished chapter set. Unusable is treated the same as absent —
    G1 falls through to its normal "nothing to publish" failure rather than
    reporting a count that was never real.
    """
    manifest_path = workspace / "_system" / "audiobook-chapters.json"
    if not manifest_path.is_file():
        return None
    try:
        chapters = json.loads(manifest_path.read_text(encoding="utf-8")).get("chapters")
    except (OSError, ValueError):
        return None
    return len(chapters) if isinstance(chapters, list) and chapters else None


def gate_g1_sessions_structure(workspace: Path, *, fail, ok) -> tuple[bool, int]:
    """The Sessions lane's own proof of real, finished structure: a composed
    book/book.md, a finished chapter set — chapter-contracts/*.yml for a
    lecture, or `_system/audiobook-chapters.json` for an audiobook (see
    `_audiobook_chapter_count`) — and at least one recorded episode under
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
    audiobook_count = None if contracts else _audiobook_chapter_count(workspace)
    if not contracts and audiobook_count is None:
        fail(
            "G1",
            f"no chapter-contracts/*.yml and no usable _system/audiobook-chapters.json under {workspace}",
        )
        return False, 0

    audio = sorted(p for p in audio_dir.glob("*") if p.is_file()) if audio_dir.is_dir() else []
    if not audio:
        fail("G1", f"no m4a/Episodes/* audio under {workspace}")
        return False, 0

    if contracts:
        ok("G1", f"sessions lane: book.md + {len(contracts)} chapter-contract(s) + {len(audio)} episode audio file(s)")
        return True, len(contracts)
    ok(
        "G1",
        f"sessions lane (audiobook): book.md + {audiobook_count} chapter(s) via "
        f"audiobook-chapters.json + {len(audio)} episode audio file(s)",
    )
    return True, audiobook_count


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
