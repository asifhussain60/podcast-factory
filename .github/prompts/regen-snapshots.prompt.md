---
mode: agent
description: Regenerate the three plan-dashboard snapshot JSONs against the current commit and stage them. Run after any edit to the four canonical plan files.
---

Run the snapshot regeneration step that keeps the plan-dashboard SPA in sync with repo truth.

## Steps

1. From the repo root, run:

   ```
   cd plan-dashboard && npm run snapshot
   ```

2. Confirm the script printed a `source_commit:` line and that it matches `git rev-parse --short HEAD`.

3. Check `git status` — you should see three modified files:
   - `plan-dashboard/src/data/architecture-snapshot.json`
   - `plan-dashboard/src/data/dashboard-snapshot.json`
   - `plan-dashboard/src/data/infrastructure-snapshot.json`

4. If the SSE dev server is running (`pgrep -f 'plan-dashboard.*node'`), also `touch plan-dashboard/.snapshot-version` so the dev server pushes a refresh.

5. Stage the three JSONs with `git add plan-dashboard/src/data/*.json`. Do NOT commit them alone — they should ride alongside the plan-file edit that triggered the regen.

## When to invoke this prompt

After ANY edit to:

- `_workspace/plan/architecture.md`
- `_workspace/plan/refactor/plan.md`
- `_workspace/plan/refactor/plan.yaml`
- `_workspace/plan/debt/pipeline-debt.md`

The standing rule in [copilot-instructions.md](../copilot-instructions.md) requires the regen happen in the same response, before commit. This prompt is the shortcut.

## Report shape

One short paragraph: "Snapshots regenerated at <timestamp>, source_commit <short-sha>. Three JSONs staged. <Optional: SSE sentinel touched / SSE server not running.>"

No Next block — this is a utility prompt, not a decision point.
