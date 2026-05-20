"""Shared types for phase runners.

A phase runner is a module exporting:
    PHASE_ID:       str           # e.g., "P1.1"
    DESCRIPTION:    str           # one-line human label
    is_done(root):  bool          # idempotency check; cheap; no side effects
    execute(root):  PhaseResult   # do the work; mark acceptance; return status

Status semantics:
    "done"     — work complete; acceptance rows are now [x]
    "halted"   — partial progress; human review needed (write evidence path)
    "error"    — execute raised; bubble up to dispatcher

The dispatcher (`run_wave.py`) is the only caller. It iterates the wave's
registry, calls `is_done` first (fast skip), then `execute` if needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Status = Literal["done", "halted", "error"]


@dataclass
class PhaseResult:
    phase_id: str
    status: Status
    message: str = ""
    rows_marked: list[str] = field(default_factory=list)
    rows_pending: list[str] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)

    def is_done(self) -> bool:
        return self.status == "done"

    def is_halted(self) -> bool:
        return self.status == "halted"


__all__ = ["PhaseResult", "Status"]
