# Loop Intelligence

## Meta
- Iteration Count: 4
- Last Updated: 2026-05-27
- Current Wave: Loop Execution Protocol Iteration 4
- Current Status: corrected-completed

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
