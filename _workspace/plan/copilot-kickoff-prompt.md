# Copilot kickoff prompt (copy-paste into GitHub Copilot Chat, agent mode)

Paste everything in the fenced block below into Copilot Chat (agent mode) in VS Code, on the
`book/ayyuhal-walad` branch. It is self-contained but points Copilot at the durable briefs so it
stays in sync across sessions.

```text
You are GitHub Copilot working in the `podcast-factory` repo, in PARALLEL with Claude Code. We
split the work by directory to avoid collisions. Before doing anything, read these two files
end-to-end:
  1. .github/copilot-instructions.md   (§"Two-agent model — YOU (Copilot) + Claude Code")
  2. _workspace/plan/copilot-handoff.md (current Wave-8 state + your work-package + session log)

YOUR LANE: you own `plan-dashboard/**` (the Astro site — React/TSX, TipTap, CSS, the editorial
cockpit, the intake page). You may READ anything under `content/drafts/books/<slug>/` and
`content/knowledge-base/knowledge.db`. You must NOT edit: anything in `scripts/podcast/**`, any
prompt, `_rules.py`, `_doctrinal.py`, the `infra/claude-agents/*.md` specs, `docs/standards/*.md`,
the plan files (`_workspace/plan/refactor/plan.{yaml,md}`), or the snapshot JSONs
(`plan-dashboard/src/data/*-snapshot.json`). Those are Claude's. If you believe one is wrong,
write it in the handoff session log instead of editing it.

ANTI-REGRESSION RULES (non-negotiable):
- Run `cd plan-dashboard && npm run lint:views` before EVERY commit that touches a view, and
  `npm run build` before you call a package done. There is no git pre-commit hook in this clone
  and Claude's hooks do not fire for you, so these gates are manual and on you.
- Follow the Cortex HTML View Quality Standard for all site work: external CSS only (no inline
  `style=` or `<style>`), use the existing `--c-*` theme tokens, never change the colour theme.
  Card: `docs/standards/html-view-quality-digest.md`.
- The `_system/` JSON files (`editorial/book.json`, `editorial/<chapter>.json`,
  `review/<chapter>.json`) are the API between the site and the Python pipeline; Claude owns the
  schema. Consume the shapes in `plan-dashboard/src/lib/reader/editorial.ts` and `stage-review.ts`
  — never invent or fork a schema. If a card needs a new field, note it in the handoff log.
- `git pull --rebase origin book/ayyuhal-walad` before you start and before you push. Commit
  small and often, scoped to `plan-dashboard/**`, conventional-commit subjects
  (`feat(wave8/6b): …`). NEVER do Tier-2 actions: orchestrator runs, publish, develop→main PRs,
  force-push, branch deletion — those are Asif's.

YOUR WORK-PACKAGE (build in this order; full detail in copilot-handoff.md §YOUR WORK-PACKAGE):

PACKAGE 1 — Slice 6b "New Content" intake page (entirely in plan-dashboard/):
  - src/pages/intake.astro — the page (mirror studio.astro's structure).
  - src/components/intake/NewContentForm.tsx — slug + category (books|articles|documents|
    lectures|interviews|letters|asbaaq) + title + source-hint fields.
  - src/components/intake/EditorialDefaults.tsx — REUSE the existing <EditorialCards> at book
    scope; do not re-implement the cards.
  - src/pages/api/intake/create.ts — POST {slug, category, title, sourceHint}; validate slug
    against /^[a-z0-9]+(?:-[a-z0-9]+)*$/; create content/drafts/books/<slug>/_system/ and write
    meta.json ({slug, category, title, created_at}) + an empty editorial/book.json. MUST NOT
    launch the pipeline — it only scaffolds the workshop folder.
  - src/styles/intake.css — external, --c-* tokens, Cortex rules.
  Acceptance: /intake renders form + book-scope cockpit; valid slug creates the _system files
  and shows the path; invalid slug rejected client+server; lint:views + build clean.

PACKAGE 2 — Slice 5b enhancement layer (polish EditorialCards.tsx; keep its JSON schema):
  - npm i @dnd-kit/core @dnd-kit/sortable cmdk (commit package.json + lockfile).
  - Drag-reorder the kind:'list' cards (Key Focus, Forbidden Terms, Required Elements) with
    @dnd-kit/sortable, replacing the up/down buttons. Array order IS priority; keep the
    {items: string[]} value shape unchanged.
  - cmdk corpus search on Key Focus: add a READ-ONLY route
    src/pages/api/studio/corpus-search.ts (GET ?q=) that runs a LIKE query over the `atoms` table
    (type='doctrine') in content/knowledge-base/knowledge.db and returns {id, snippet}[];
    selecting a hit appends its text to the Key Focus list.
  Acceptance: reorder persists via the existing /api/studio/editorial POST; search returns ≥1 hit
  for "knowledge"; no change to editorial.ts CardValue; lint:views + build clean.

When both packages are green: run /session-handoff (append what changed / next / blocked to the
handoff session log) and stop. Then tell Asif you're done so Claude can wire the Python contract
side. Start with Package 1.
```
