# Plan Conventions

Cross-cutting conventions that don't belong in any one phase block but bind the whole plan together. Each section is load-bearing — if you're a future Claude session reading this for the first time, honor these literally unless the operator overrides in conversation.

## Machine routing — branch is the assignment

When the operator asks **"what's next"** / **"execute next"** / **"where am I"** on any machine, the assistant:

1. Reads the current git branch via `git branch --show-current`.
2. If the branch is `book/<slug>`, reads `content/podcast/library/**/<slug>/_system/orchestrator-state.json` for that book's current phase + status.
3. If the branch is `feat/*` or `develop` or `main`, treats it as plan/pipeline-source work and recommends the next acceptance-criteria row to ship or the next phase to launch.
4. Recommends a single concrete next action (a command to run, a decision to make, or a file to read).
5. On operator confirmation, executes it.

The git branch IS the machine assignment. The state file IS the position within that book's pipeline. No per-machine config files (`hostname` matching is brittle); no separate runbook (duplicates what git + state files already encode).

If the operator has multiple machines and wants different books on each, the workflow is just:
- Mac A: `git checkout book/<slug-A>` → KaR-style work
- Mac B: `git checkout book/<slug-B>` → Asaas-style work
- Both push to `origin/book/<slug-X>` on their own schedule
- Plan / pipeline-source work happens on `feat/podcast-w1-foundation` via worktree on either Mac

The pipeline doesn't enforce one-machine-per-book today (P12 in W4 ships the formal mutation API + worker pool); manual coordination via branch checkout is the convention until then.

## Operator-invocable shorthand

The operator can use any of these phrasings; they all trigger the same convention:

- `what's next`
- `execute next`
- `where am I`
- `next action`
- `/next`

The assistant should NOT ask clarifying questions about what to do — it should read state and recommend. The operator can redirect if the recommendation is wrong.
