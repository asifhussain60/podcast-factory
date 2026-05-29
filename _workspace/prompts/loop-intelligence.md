# Loop Intelligence

## Meta
- Iteration Count: 6
- Last Updated: 2026-05-28
- Current Wave: H3 — cross-wave autonomous execution chain driver
- Current Status: completed

## Pre-flight Checks
- [ ] Verify the exact wave objective is explicitly stated in one sentence before implementation.
- [ ] Verify prior-wave acceptance criteria are re-evaluated before new execution begins.
- [ ] Verify run-wave state targets are identified before edits.
- [ ] Verify all required outcome logs (SP/FP/IM + iteration line) are ready to be appended at run end.

## Default Behaviors
- Apply root-cause-first analysis for all issues before proposing fixes.
- Prefer smallest safe change that satisfies wave intent and acceptance criteria.
- Preserve existing conventions and avoid unrelated refactors.
- Log at least one concrete pattern on every run.
- Always refresh and validate the full intelligence ledger before execution so gate checks and iteration accounting cannot be skipped.

## Success Patterns
- SP-001 (recurrence: 3): Creating a canonical intelligence ledger before execution prevents skipped gate checks and guarantees every run has auditable state. Replicate by ensuring Meta + checks + pattern sections exist before any wave action.
- SP-002 (recurrence: 1): Updating run-wave state directly from the chat execution path after each run keeps operators aligned on wave status, intent result, and pattern tallies without UI coupling. Replicate by recording wave state and event outcomes in-run.
- SP-003 (recurrence: 1): Running deterministic prior-wave checks before telemetry updates catches stale dashboard state drift early and turns no-regression claims into evidence-backed assertions. Replicate by executing wave acceptance checks first, then writing loop telemetry.
- SP-004 (recurrence: 1): Separating the `authorize` step from the `run` step in any long-running autonomous driver enforces spend accountability without blocking automation — the operator authorizes once (writes a pre-authorization envelope with spend caps), then the executor enforces caps throughout the chain without re-prompting. Replicate whenever building a multi-step driver that must stop at human-review gates or budget limits.

## Failure Patterns
- None yet.

## Intent Misses
- None yet.

## Iteration Log
- Date | Wave | Outcome | Patterns discovered | Patterns promoted
- 2026-05-27 | Loop Execution Protocol Bootstrap | Completed | SP-001 | None
- 2026-05-27 | Loop Execution Protocol Iteration 2 | Completed | SP-002 | None
- 2026-05-27 | Loop Execution Protocol Iteration 3 | Completed | SP-001 | SP-001 -> Default Behaviors
- 2026-05-27 | Loop Execution Protocol Iteration 4 | Corrected-completed | SP-003 | None
- 2026-05-28 | H3 cross-wave chain driver | Completed | SP-004 | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-28 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-28 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-28 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-29 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-29 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-29 | W1 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Completed | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W2 | Halted | SP-004 (chain driver) | None
- 2026-05-29 | Chain W1–W3 | SpendCapHalt | SP-004 (chain driver) | None
- 2026-05-29 | W1 | P9Violated | SP-004 (chain driver) | None
- 2026-05-29 | W1 | Error | SP-004 (chain driver) | None
- 2026-05-29 | W1 | Completed | SP-004 (chain driver) | None
