"""Per-phase runners for the autonomous wave-execution loop.

Each phase exports two callables: `is_done(repo_root)` and `execute(repo_root)`.
The wave dispatcher in `run_wave.py` iterates the REGISTRY in declared
order, calling `is_done` to check idempotency, then `execute` if not done.

Adding a new phase:
  1. Drop scripts/podcast/phases/p<n>_<m>.py with PHASE_ID, DESCRIPTION,
     is_done(), execute() per `phases/_base.py`.
  2. Append it to REGISTRY in this file under its owning wave.
  3. Land its scripts/podcast/<deliverable> + tests in the same commit.
  4. Add acceptance-criteria.md rows if not already present.

The wave dispatcher's autonomous loop is fully deterministic given the
state of (a) the filesystem, (b) acceptance-criteria.md row checkboxes.
"""
from __future__ import annotations

from typing import Callable

from ._base import PhaseResult
from . import p1_1, p5_4

# Phase registry — ordered within each wave per declared dependencies.
# Each list entry is the module exporting PHASE_ID / is_done / execute.
REGISTRY: dict[int, list] = {
    1: [
        p5_4,   # phase-id constants module — zero deps, ships first as foundation
        p1_1,   # boundary check — depends only on the constants module's existence
        # P1.2, P1.3, P2.x, P3.x (already done), P4.x, P5.1 (shipped), P5.2 (shipped),
        # P5.3, P6.x land in subsequent commits via the same registry pattern.
    ],
    2: [],
    3: [],
    4: [],
    5: [],
}


def wave_phases(wave_n: int) -> list:
    return REGISTRY.get(wave_n, [])


__all__ = ["PhaseResult", "REGISTRY", "wave_phases"]
