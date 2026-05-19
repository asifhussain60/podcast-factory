"""Shared helper for `halt-with-DoR` phase runners.

A halt-with-DoR runner DOES NOT auto-execute. It exists to:
  1. Verify whether the deliverable is already present (if so → mark + done).
  2. Otherwise emit a precise human-action prompt naming the blockers,
     assumptions, and ambiguities — then halt at exit code 3.

This lets the autonomous loop SAFELY process phases that need either:
  • Azure spend (P5.3 kitab-al-riyad resume)
  • Operator-authored content (P4.7 Master & Disciple Ch-02 scaffolding)
  • Mocked-external test scaffolding (P2.x E2E harness)
  • Agent-spec edits (P4.5 challenger Loop N, P6.4 trainer hook)

The runner is fully deterministic given the filesystem state. It never
calls Azure, never calls `claude -p`, never edits files outside the
acceptance checklist.

All halt-with-DoR runners follow the same shape:
    PHASE_ID:       str
    DESCRIPTION:    str
    DOR:            DoR             # the verbose breakdown
    DETECT_FILES:   tuple[Path,...] # files whose existence indicates the phase has been
                                    # hand-shipped by the operator (out-of-band)
    DETECT_MARKERS: tuple[str,...]  # substrings ALL of which must appear in the detect
                                    # files for is_done() to be true

If the operator hand-ships the deliverable, is_done() returns True, the
runner marks acceptance, and the autonomous loop moves on. Until that
happens, every tick prints the DoR breakdown so the gap is always visible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ._base import PhaseResult


@dataclass(frozen=True)
class DoR:
    """Definition-of-Ready breakdown for a halt-with-DoR phase."""
    blockers: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    operator_action: str = ""

    def render(self, phase_id: str, description: str) -> str:
        lines = [f"{phase_id} — {description}", ""]
        if self.blockers:
            lines.append("BLOCKERS:")
            for b in self.blockers:
                lines.append(f"  • {b}")
            lines.append("")
        if self.assumptions:
            lines.append("ASSUMPTIONS:")
            for a in self.assumptions:
                lines.append(f"  • {a}")
            lines.append("")
        if self.ambiguities:
            lines.append("AMBIGUITIES (resolve before ship):")
            for a in self.ambiguities:
                lines.append(f"  • {a}")
            lines.append("")
        if self.operator_action:
            lines.append("OPERATOR ACTION TO UNBLOCK:")
            for ln in self.operator_action.splitlines():
                lines.append(f"  {ln}")
        return "\n".join(lines)


def is_done(detect_files: tuple[Path, ...], detect_markers: tuple[str, ...]) -> bool:
    """Conservative detector: every file in `detect_files` exists AND contains
    every marker in `detect_markers`. Either side can be empty (degrades to
    'always halted')."""
    if not detect_files:
        return False
    for f in detect_files:
        if not f.exists():
            return False
        if detect_markers:
            text = f.read_text()
            if not all(m in text for m in detect_markers):
                return False
    return True


def build_halted_result(
    phase_id: str,
    description: str,
    dor: DoR,
    detect_files: tuple[Path, ...],
) -> PhaseResult:
    return PhaseResult(
        phase_id=phase_id,
        status="halted",
        message=dor.render(phase_id, description),
        evidence_paths=[str(f) for f in detect_files],
    )
