---
mode: ask
description: Show where the podcast-factory refactor stands today — what's done, what's next, what's blocked. Cites the four canonical plan files.
---

Read the four canonical plan files and the session log, then produce a status report in Asif's response format:

1. `#file:../../_workspace/plan/refactor/plan.md` — roadmap shape
2. `#file:../../_workspace/plan/refactor/plan.yaml` — per-step status + Manual Review Index
3. `#file:../../_workspace/plan/debt/pipeline-debt.md` — open F-items
4. `#file:../../_workspace/plan/copilot-handoff.md` — session log + current focus
5. `#file:../../plan-dashboard/src/data/dashboard-snapshot.json` — latest snapshot of roadmap state

Then output:

```
## Where the refactor stands today

> **{One-line verdict — which wave we're in, whether we're moving or stuck.}**

### What's done

{Recent commits + which steps closed. Reference commits by short SHA + plain-English description, never by step ID like "A1" in the visible body.}

### What's next

{The single most-valuable concrete step. Quote the snapshot's `next_action` field if present.}

### What's blocked or deferred

{Manual Review Index entries with severity HIGH or DEFERRED, in plain English. Translate step IDs into outcome language.}

---

### Next: 👤 Asif

A. **(Recommended)** {action that advances the "what's next" item}.

B. {alternative — usually 'review the deeper plan' or 'pause and ship what's queued'}.
```

Do NOT make code changes in this prompt — it is read-only orientation. If Asif wants you to act, he will direct the next step.
