# `_workspace/plan/operators/` — cross-machine coordination zone

The state, protocol, and per-machine resume files that let multiple Claude
sessions on multiple physical machines work the podcast pipeline
autonomously without stepping on each other.

## Files

| File                            | Writer                | Readers     | Purpose                                                                  |
|---------------------------------|-----------------------|-------------|--------------------------------------------------------------------------|
| `coordination-protocol.md`      | operator (Asif)       | all machines | The discipline — write rules, push rules, session-start sequence, branch policy, quota, known bugs, conventions. **Wins over per-machine files when in conflict.** |
| `assignments.md`                | operator + machines (on reassignment events only) | all machines | Who owns which book. Read from `origin/develop` for canonical truth.     |
| `mac-studio-primary.md`         | Mac Studio only       | all machines | Studio's identity, current book, resume action, peer pointer.            |
| `macbook-air-secondary.md`      | MacBook Air only      | all machines | Air's identity, current book, resume action, peer pointer.               |

## Read this in this order on session start

1. `coordination-protocol.md` §3 — session-start commands you run before anything else.
2. `assignments.md` (from `origin/develop`) — who owns what right now.
3. `<your-machine-id>.md` on the current branch — your specific resume action.
4. `content/podcast/library/books/<your-book>/_system/orchestrator-state.json` — authoritative phase + status.

The first three are reference; the fourth is truth. If they conflict, trust the state file and update your operator file.

## Adding a new machine

1. Pick a slug (`<role>-<location>`, e.g. `macbook-pro-asif-home`).
2. Place `~/.machine-id` containing that slug on the physical machine.
3. Add a new `<slug>.md` here using `mac-studio-primary.md` as the template.
4. Update `assignments.md` to declare the machine and assign it work (or leave it `IDLE`).
5. Commit on `feat/podcast-w1-foundation`; merge to `develop`; merge `develop` into every active book branch.

## Why this lives at `_workspace/plan/operators/` and not `_workspace/operators/`

Historical: the coordination protocol was authored when operator files sat
alongside the plan. Many cross-references already hardcode this path. The
*content* is cross-machine coordination, not plan content, but the *path* is
stable. Future move (to `_workspace/operators/`) would touch every reference
and is not worth the churn unless we promote `_workspace/plan/` itself.
