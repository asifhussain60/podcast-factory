---
mode: agent
description: Pick the next concrete step from the refactor roadmap, scope it as a plan-block for Asif's approval, and (with approval) execute it end-to-end including snapshot regen.
---

You are continuing the podcast-factory pipeline refactor that started under Claude. Drive autonomously to completion of one concrete step, with halts ONLY at Tier-2 gates and at the end-of-step report.

## Pre-flight (read-only, Tier 0)

1. Read `#file:../../_workspace/plan/copilot-handoff.md` — current focus + session log + what previous session left.
2. Read `#file:../../_workspace/plan/refactor/plan.md` and `#file:../../_workspace/plan/refactor/plan.yaml` — identify the next unblocked step.
3. Read `#file:../../_workspace/plan/architecture.md` for the section relevant to the next step.
4. `git status` + `git log --oneline -10` to confirm the working tree is clean and you understand recent history.

## Step 1 — Propose

Output a single plan-block for Asif's approval, using the locked plan-block format:

```
### N. {single-sentence statement of work — plain English, no jargon}

> {2-4 sentences. Explain WHAT and WHY in language a non-technical reader understands. Name files only when essential; gloss the term immediately.}
>
> *Value gained:* {one-line outcome — what improves, what stops hurting, what becomes possible}
```

Then ask Asif: "Approve to proceed?" — wait for a yes.

## Step 2 — Execute (after approval)

- Make the edits. Respect the 600-line cap on `scripts/podcast/**` files.
- If your changes touch any of the four canonical plan files (architecture.md / refactor/plan.md / refactor/plan.yaml / debt/pipeline-debt.md), IMMEDIATELY after the edit run `cd plan-dashboard && npm run snapshot` and stage `plan-dashboard/src/data/*.json` alongside.
- Write or update tests if the step touches code.
- Commit with a clear message ending with:
  ```
  Co-Authored-By: GitHub Copilot <noreply@github.com>
  ```
- If the step touches multiple concerns, prefer ONE commit per logical concern.

## Step 3 — Append the session log

Append a dated entry to the bottom of `_workspace/plan/copilot-handoff.md`'s `## Session log` section with: date (YYYY-MM-DD HH:MM), step closed, commit SHA(s), what's next, anything blocked. Then commit the handoff doc update separately as `chore(handoff): session log entry for <step>`.

## Step 4 — End-of-step report

Use Asif's response format (H2 main / H3 sections / blockquote callouts / table for tabular content / one rule before Next). Cite commits by short SHA. Plain English in the visible body — no step IDs like "A2", no file paths like `scripts/podcast/_db.py` in chat (those go in the commit and handoff doc).

Then Next block: A. (Recommended) the next step in roadmap order; B. alternative if there's a fork; C. pause for review.

## Hard rules

- Tier 2 actions (publish, first orchestrator run on a new book, force-push, branch delete, develop→main PR) require Asif's explicit "yes" — never silent.
- Never overwrite `_workspace/plan/copilot-handoff.md` — only append to the session log section.
- Never modify `.claude/settings.json` (that's Claude's harness; the classifier blocks it from inside Claude too).
- Never edit files in `content/published/` by hand — that surface is publisher-agent-only.
- If you discover the next roadmap step depends on something not yet built, surface it as a question rather than building speculatively.
