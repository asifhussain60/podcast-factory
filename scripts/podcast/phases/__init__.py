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
from . import p1_1, p4_3, p4_4, p4_8, p5_4, p6_1, p6_2

# Phase registry — ordered within each wave per declared dependencies.
# Each list entry is the module exporting PHASE_ID / is_done / execute.
REGISTRY: dict[int, list] = {
    1: [
        p5_4,   # phase-id constants module — zero deps, ships first
        p1_1,   # boundary check — depends only on the constants module's existence
        p4_3,   # SKILL.md pre-read extension — pure verify
        p4_4,   # pre-refined-source-mode handbook extension — pure verify
        p4_8,   # intelligence_sources for P4 deliverables — pure verify
        p6_1,   # cost-ledger writer
        p6_2,   # cost-ledger summary CLI
        # Outstanding W1 phases not yet wired:
        #   P1.2 proposal writer + handoff doc
        #   P1.3 CI workflow wiring (depends on P8.8 in W2)
        #   P2.1/2.2/2.3/2.4/2.5/2.6 E2E test harness
        #   P4.1 abjad-numerals shared file (large content authoring)
        #   P4.2 numeric-symbolic-disambiguation handbook
        #   P4.4b Loop N regression fixture
        #   P4.5 challenger Loop N spec
        #   P4.6 Phase 07-chapter-design numeric scan
        #   P4.7 Master & Disciple Ch-02 scaffolding
        #   P5.3 kitab-al-riyad resume (requires explicit Azure spend approval)
        #   P6.3 soft/hard cost caps (requires P7 heartbeat for soft-warning path)
        #   P6.4 trainer cost-ledger hook
    ],
    2: [],
    3: [],
    4: [],
    5: [],
}


def wave_phases(wave_n: int) -> list:
    return REGISTRY.get(wave_n, [])


__all__ = ["PhaseResult", "REGISTRY", "wave_phases"]
