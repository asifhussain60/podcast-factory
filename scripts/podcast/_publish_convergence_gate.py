"""publish_to_library.py's G7 gate — challenger convergence verdict.

Split out of publish_to_library.py purely to stay under the DR-005 600-line
cap (the same reason _publish_sessions_gates.py and _publish_downstream.py
exist as separate modules): G7 is self-contained (reads the book's own state
+ challenger report, no shared mutable state with the rest of the publisher)
and a caller can import it rather than grow publish_to_library.py in place.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Books may only be published if a real challenger convergence pass produced
# one of these verdicts. Anything else (including "unknown" or N/A reports)
# blocks publish unless --allow-mode-2 is passed.
ALLOWED_SHIP_VERDICTS = {"SHIP-READY", "SHIP-WITH-CAUTION"}

# Books whose state.json pipeline_mode is in this set never ran the
# orchestrator's convergence loop and require explicit --allow-mode-2.
# Added 2026-05-24: `pre_orchestrator_authored` (ayyuhal-walad, B-P0-04) —
# the book was authored before the orchestrator existed; verdict is
# `ship-with-caution` based on manual review, not a convergence pass.
# Added 2026-08-12: `sessions_lane` (see _publish_sessions_gates.py).
# Added 2026-08-15: `reading_edition_only` — a podcast-less book (reading
# edition + read-aloud narration only); see _publish_reading_edition_gates.py.
NON_CONVERGED_PIPELINE_MODES = {
    "non_orchestrated_mode_2",
    "pre_orchestrator_authored",
    "sessions_lane",
    "reading_edition_only",
}


def _chapter_timings_verdict(state: dict) -> tuple[bool, str] | None:
    """Aggregate per-chapter verdicts from orchestrator-state.json, if present.

    Returns None when the book's state predates `chapter_timings` (or it's
    empty) — the caller falls back to the single-report-file check unchanged.
    Otherwise every chapter must be a real SHIP-* verdict, OR carry a
    HUMAN-OVERRIDE verdict matched by an explicit, attributed override record
    on the per-chapter phase (never inferred — a HUMAN-OVERRIDE verdict with
    no matching record still fails). This is strictly more precise than the
    report-file check: it reflects every chapter, not whichever one the
    challenger happened to run against last.
    """
    per_chapter = state.get("phases", {}).get("per-chapter", {})
    chapter_timings = per_chapter.get("chapter_timings") or {}
    if not chapter_timings:
        return None

    raw_overrides = per_chapter.get("human_override") or []
    if isinstance(raw_overrides, dict):
        raw_overrides = [raw_overrides]
    overrides = {
        o["chapter"]: o
        for o in raw_overrides
        if isinstance(o, dict) and o.get("chapter") and o.get("reason") and o.get("decided_by")
    }

    unresolved = []
    overridden = []
    for chapter, timing in chapter_timings.items():
        verdict = str(timing.get("verdict", "")).upper()
        if verdict in ALLOWED_SHIP_VERDICTS:
            continue
        if verdict == "HUMAN-OVERRIDE" and chapter in overrides:
            overridden.append(chapter)
            continue
        unresolved.append(f"{chapter}: verdict={timing.get('verdict')!r} (no matching human_override)")

    if unresolved:
        return False, "; ".join(unresolved)
    msg = f"{len(chapter_timings)} chapter(s) via chapter_timings"
    if overridden:
        msg += f", {len(overridden)} human-overridden: {', '.join(sorted(overridden))}"
    return True, msg


def gate_g7_challenger_convergence(workspace: Path, allow_mode_2: bool, *, fail, ok, warn) -> bool:
    """Refuse to publish unless the book passed a real challenger convergence
    pass — or the operator explicitly opted in with --allow-mode-2.

    Closes the bypass that lets non-orchestrated books (pipeline_mode=
    non_orchestrated_mode_2) and challenger-N/A reports reach the audience
    without ever clearing the convergence gate. See _convergence.py for the
    sibling change that removes the silent FORCE-SHIP-CAUTION downgrade.
    """
    state_path = workspace / "_system" / "orchestrator-state.json"
    report_path = workspace / "_system" / "challenger-report.md"

    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text())
    pipeline_mode = state.get("pipeline_mode")
    convergence_skipped = pipeline_mode in NON_CONVERGED_PIPELINE_MODES

    if not convergence_skipped:
        per_chapter_result = _chapter_timings_verdict(state)
        if per_chapter_result is not None:
            passed, msg = per_chapter_result
            if passed:
                ok("G7", msg)
                return True
            if allow_mode_2:
                warn(f"G7 ⚠ MODE-2 SHIP: {msg}. --allow-mode-2 honored.")
                return True
            fail("G7", f"{msg}. Run challenger to convergence OR rerun with --allow-mode-2.")
            return False

    verdict = "unknown"
    if report_path.exists():
        # Tolerant of several real-world challenger-report shapes:
        #   **Verdict:** SHIP-WITH-CAUTION
        #   **Verdict: X**
        #   **Verdict (book-level):** SHIP-WITH-CAUTION   ← whole-book sweep
        # Strict canonical shape lives in _convergence.py::VERDICT_LINE_RE.
        verdict_re = re.compile(
            r"\*\*Verdict[^*]*?\*?\*?\s*:?\s*(SHIP-READY|SHIP-WITH-CAUTION|BLOCKED)",
            re.IGNORECASE,
        )
        for line in report_path.read_text().splitlines()[:20]:
            m = verdict_re.search(line)
            if m:
                verdict = m.group(1).strip().upper()
                break
    verdict_recognized = verdict in ALLOWED_SHIP_VERDICTS

    if convergence_skipped or not verdict_recognized:
        if allow_mode_2:
            warn(
                f"G7 ⚠ MODE-2 SHIP: challenger convergence not satisfied "
                f"(pipeline_mode={pipeline_mode!r}, verdict={verdict!r}). "
                f"--allow-mode-2 honored; downstream catalog will mark this "
                f"book as 'challenger_convergence: skipped_mode_2'."
            )
            return True
        reasons = []
        if convergence_skipped:
            reasons.append(f"pipeline_mode={pipeline_mode!r} skipped convergence loop")
        if not verdict_recognized:
            reasons.append(
                f"verdict={verdict!r} not in {sorted(ALLOWED_SHIP_VERDICTS)} "
                f"(challenger-report.md missing, malformed, or marked N/A)"
            )
        fail("G7", "; ".join(reasons) + ". Run challenger to convergence OR rerun with --allow-mode-2.")
        return False

    ok("G7", f"challenger verdict={verdict}, pipeline_mode={pipeline_mode!r}")
    return True
