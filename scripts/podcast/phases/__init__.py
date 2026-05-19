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
from . import (
    p1_1, p1_2,
    p4_1, p4_2, p4_3, p4_4, p4_7, p4_8,
    p5_4, p6_1, p6_2,
    p11_1,
    dor_halts,
)

# Phase registry — ordered within each wave per declared dependencies.
# Each list entry is the module exporting PHASE_ID / is_done / execute.
REGISTRY: dict[int, list] = {
    1: [
        # ── Foundation (deliverables auto-marked when their files validate) ──
        # Verify-only runners go FIRST so all shippable acceptance rows mark
        # on every tick BEFORE the loop halts at any DoR-blocked phase.
        p5_4,    # phase-id constants module — zero deps
        p1_1,    # boundary check
        p1_2,    # proposal writer + manual library handoff doc
        p4_1,    # abjad-numerals shared file
        p4_2,    # numeric/symbolic disambiguation handbook
        p4_3,    # SKILL.md pre-read extension
        p4_4,    # pre-refined-source-mode handbook extension
        p4_7,    # M&D Ch-02 scaffolding (Numeric Disambiguation + checklist §J)
        p4_8,    # intelligence_sources for P4 deliverables
        p6_1,    # cost-ledger writer
        p6_2,    # cost-ledger summary CLI

        # ── Halt-with-DoR (the autonomous loop CAN'T safely auto-execute these;
        # each runner surfaces blockers/assumptions/ambiguities + operator-action
        # on every tick until the deliverable lands; then auto-marks) ───────
        dor_halts.p2_1,   # tiny-book fixture (operator authors content)
        dor_halts.p2_2,   # sunny-day E2E (needs Azure mocks)
        dor_halts.p2_3,   # rainy-day E2E
        dor_halts.p2_4,   # CI workflow podcast-e2e.yml
        dor_halts.p2_5,   # learning-loop E2E + CI gate
        dor_halts.p2_6,   # refinement determinism (one-time live golden author)
        dor_halts.p4_4b,  # Loop N regression fixture (waits on P4.5)
        dor_halts.p4_5,   # challenger Loop N spec (agent-file edits)
        dor_halts.p4_6,   # Phase 07 numeric scan (invasive _authoring.py)
        dor_halts.p5_3,   # kitab-al-riyad resume — explicit Azure spend approval gate
        dor_halts.p6_3,   # soft/hard cost caps (waits on P7 heartbeat)
        dor_halts.p6_4,   # trainer cost-ledger hook (agent-file edit)
    ],
    2: [],
    3: [],
    4: [
        p11_1,   # multi-mac decision doc (already shipped; auto-marks)
    ],
    5: [],
}


def wave_phases(wave_n: int) -> list:
    return REGISTRY.get(wave_n, [])


__all__ = ["PhaseResult", "REGISTRY", "wave_phases"]
