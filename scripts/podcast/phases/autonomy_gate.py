"""phases/autonomy_gate.py — the gates an autonomous run may clear for itself.

A stop in this pipeline is one of four things, and only two of them are a run's
to clear:

  approval   the series plan. A human said yes by re-invoking --resume, which
             carried no information beyond "yes" -- it could not, because the
             gate fires before there is a book to look at.
  spend+read the audio-render H1 gate. It reads as a spend gate and is not only
             one: re-invoking --resume there means BOTH "I approve the credits"
             AND "I have read this book". No level clears it today, because a run
             that cleared it would be buying ElevenLabs audio for a book nobody
             had read. The registry keeps the switch so a later level can.
  physical   the NotebookLM audio drop. Someone has to open NotebookLM and put
             files in a folder. No level clears this, because no level can.
  authority  the publish flip. Draft to public is irreversible and Tier 2, and
             its standing permission belongs in CLAUDE.md where a human wrote it,
             not in a config field a book can set for itself.

The clearable ones are cleared HERE, in one place, and each writes a decision
ledger entry naming what it approved. That is the whole difference between an
autonomous run and an unattended one: the finalize halt hands back a book plus a
list of what was decided along the way, instead of the run having stopped
to ask a question the author could not usefully answer yet.

Returns False when the level does not clear the gate, and the caller then halts
exactly as it always did. No caller changes behaviour for a `manual` book.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from _autonomy import autonomy_clears
from _pipeline_flags import autonomy


def _clear(
    book_dir: Path,
    *,
    gate: str,
    key: str,
    chose: str,
    why: str,
    evidence: str,
    phase: str,
    log: Callable[[str], None],
) -> bool:
    level = autonomy(book_dir)
    if not autonomy_clears(level, gate):
        return False
    try:
        from _book_decisions import resolve

        resolve(
            book_dir,
            key=key,
            default=chose,
            alternatives=["halt and wait for --resume"],
            why=why,
            evidence=evidence,
            phase=phase,
        )
    except Exception:
        # An unwritable ledger must not silently convert an autonomous run into a
        # stopped one, nor an autonomous run into an unrecorded one. It logs and
        # proceeds: the run is still disclosed in the phase log, which is where a
        # reader would look next.
        log(f"    autonomy: {key} cleared but NOT recorded — decision ledger unwritable")
    log(f"    autonomy [{level}]: {gate} cleared by the run — see the decision ledger at the finalize halt")
    return True


def clear_series_plan_gate(book_dir: Path, plan_path: Path, *, log: Callable[[str], None]) -> bool:
    """Approve the 0f series plan on the author's behalf, if the level allows."""
    return _clear(
        book_dir,
        gate="series_plan",
        key="phase-0f-series-plan-approval",
        chose="approved as written by the run",
        why=(
            "The 0f gate asks for approval of a chapter list and length tier before any chapter "
            "exists to judge it against, so the answer carried no information a human could supply "
            "at that moment. The plan is reviewable at the finalize halt alongside the book it "
            "produced, which is where an informed answer is actually possible."
        ),
        evidence=str(plan_path),
        phase="0f",
        log=log,
    )


def clear_audio_render_gate(book_dir: Path, *, projected_usd: float | None = None, log: Callable[[str], None]) -> bool:
    """Clear the H1 audio-render halt, if some level ever allows it.

    No level does today — see ``AUTONOMY_LEVELS``. Kept wired so that granting it
    is a one-word change in the registry rather than a new code path written under
    time pressure, and so the gate reads the same way as the one above.
    """
    return _clear(
        book_dir,
        gate="audio_render",
        key="audio-render-gate",
        chose="rendered without halting for review and spend approval",
        why=(
            "The level in force declares this gate clearable. Note that clearing it means audio "
            "was rendered before any human read the book."
        ),
        evidence=f"projected ${projected_usd:.2f}" if projected_usd else "projection unavailable",
        phase="audio-render",
        log=log,
    )
