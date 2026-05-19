# Podcast Pipeline — Phased Plan

**Scope:** podcast agent + skill **ONLY**. Journal is out of scope and must remain fully separate.

## Contents

| File | Purpose |
|---|---|
| [`podcast-plan.yaml`](./podcast-plan.yaml) | Canonical phased plan (P0 → P7). Single source of truth. |
| [`view/index.html`](./view/index.html) | Rich HTML view with SVG architecture diagrams. Open in browser. |
| [`research/findings.md`](./research/findings.md) | Web-research citations, sample-book corpus, dos & don'ts. |

## How to consume

1. **Read first:** `view/index.html` — visual overview, diagrams, phase timeline.
2. **Execute from:** `podcast-plan.yaml` — exact tasks, acceptance criteria, dependencies.
3. **Reference:** `research/findings.md` — why each decision was made, with sources.

## Bounded scope (do NOT cross)

| In scope | Out of scope |
|---|---|
| `.github/agents/podcast-orchestrator.agent.md` | `.github/agents/journal-*.agent.md` |
| `.github/agents/podcast-trainer.agent.md` | `.github/agents/CORTEX.agent.md`, `reconcile.agent.md`, `repo-surgeon.agent.md` |
| `skills-staging/podcast/**` | `skills-staging/journal/**` and every other sibling skill |
| `scripts/podcast/**` | `scripts/memoir/**`, `scripts/site/**` |
| `content/podcast/**` | `content/babu-memoir/**`, `content/_shared/**` |

The podcast service, API, dashboards, and SDK migration described here **must not** depend on, import from, or modify any journal code path. Cross-cutting infrastructure (git hooks, .gitignore, virtualenv) is the only allowed shared surface.

## Status

- **Current:** P0 not yet executed. `develop` is clean. Last orchestrator run on kitab-al-riyad killed mid-Phase-0b due to the `claude -p` permission-mode bug (root cause confirmed; fix is 2 lines).
- **Next:** Approve plan → execute P0 → smoke-test resume → begin P1.
