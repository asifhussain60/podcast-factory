# Podcast Pipeline — Phased Plan

**Scope:** podcast agent + skill **ONLY**. Journal is out of scope and must remain fully separate.
**Plan version:** v2 (refined 2026-05-19 via repo-surgeon evidence sweep)

## Contents

| File | Purpose |
|---|---|
| [`podcast-plan.yaml`](./podcast-plan.yaml) | Canonical phased plan (P0a, P0b, P0 → P7). Single source of truth. |
| [`view/index.html`](./view/index.html) | Rich HTML view with SVG architecture diagrams. Open in browser. |
| [`research/findings.md`](./research/findings.md) | Web-research citations, sample-book corpus, chunking rationale, system-check snapshot. |
| [`../primary-mac-activation.md`](../primary-mac-activation.md) | One-time runbook for bootstrapping a primary Mac (Azure provisioning). Referenced by Q1 open question. |

## How to consume

1. **Read first:** `view/index.html` — visual overview, diagrams, phase timeline.
2. **Execute from:** `podcast-plan.yaml` — exact tasks, acceptance criteria, dependencies.
3. **Reference:** `research/findings.md` — why each decision was made, with sources.

## Bounded scope (do NOT cross)

| In scope | Out of scope |
|---|---|
| `.github/agents/podcast-orchestrator.agent.md` | `.github/agents/journal-*.agent.md` |
| `.github/agents/podcast-trainer.agent.md` | `.github/agents/CORTEX.agent.md`, `reconcile.agent.md`, `repo-surgeon.agent.md` |
| `.github/agents/podcast-challenger.agent.md` *(P6.2 migration)* | `skills-staging/journal/**` |
| `.github/agents/podcast-extract.agent.md` *(P6.2 migration)* | `scripts/memoir/**`, `scripts/site/**` |
| `skills-staging/podcast/**` | `content/babu-memoir/**`, `content/_shared/**` |
| `scripts/podcast/**` | |
| `content/podcast/**` | |

The podcast service, API, dashboards, and SDK migration described here **must not** depend on, import from, or modify any journal code path. Cross-cutting infrastructure (git hooks, .gitignore, virtualenv) is the only allowed shared surface. **P0a wires this into CI.**

## System check snapshot (2026-05-19)

| Domain | Status |
|---|---|
| Azure CLI / subscription | ✅ logged in to `Journal AI — primary` |
| Azure resources | ✅ `journal-docintel`, `journal-translator`, `journal-speech` (all in `rg-journal-ai`/eastus) |
| Claude CLI / Python / Node | ✅ 2.1.144 / 3.14.4 / v24.15.0 |
| gh CLI | ⚠️ unauthenticated (non-blocking for plan work) |
| Git | ✅ clean on `develop`, synced to remote |
| Active orchestrator runs | ✅ none |
| `kitab-al-riyad` state | ✅ resumable (0a complete, 0b pending, zero orphan chunks) |

Full diagnostic table in [`research/findings.md`](./research/findings.md) §8.

## Phase summary (v2)

| Phase | Effort | Blocks | Status |
|---|---|---|---|
| **P0a** Journal/podcast boundary verification + CI lock-down | hours | — | not started |
| **P0b** E2E test harness (tiny-book fixture, sunny+rainy day) | 1–2d | P3 SDK migration | not started |
| **P0** Critical bug fix: `claude -p --permission-mode acceptEdits` | hours | P1, P3 | not started |
| **P1** Observability foundation: heartbeat + status CLI + wait-banner | 1–2d | P2, P5 | not started |
| **P2** Read-only Status API + browser dashboard | 3–4d | P3, P5 | not started |
| **P3** Anthropic SDK migration (replace `claude -p` shell-out) | 3–4d | P4 | not started |
| **P4** Sample corpus validation (graduated 30p → 865p) | ~1wk wall-clock | P5 | not started |
| **P5** Control plane: mutation API + worker pool + SQLite cache | 1–2wk | P6 | not started |
| **P6** Polish: phase rename (14-step) + agent dedup + isolation CI | 3–5d | — | not started |
| **P7** Deferred / speculative (PDF pre-split, parallel chapter LLM, trainer SQLite) | TBD | — | future |

## Status

- **Current:** P0a/P0b/P0 not yet executed. `develop` is clean. `kitab-al-riyad` halted cleanly mid-Phase-0b last session — root cause confirmed (claude -p permission mode), 2-line fix waiting in P0.
- **Next:** Approve refined plan → run P0a boundary check → execute P0 → smoke-test resume → begin P0b harness.

## Legacy-file triage (2026-05-19)

Performed during the refinement. Outcome:

| File | Verdict | Action taken |
|---|---|---|
| `_workspace/chatgpt-podcast-skill-prompt.md` | SUPERSEDED — content absorbed into `skills-staging/podcast/SKILL.md` and this plan | **DELETED** |
| `_workspace/folder-cleanup-prompt.md` | SUPERSEDED — supplanted by current repo structure + P6 of this plan | **DELETED** |
| `_workspace/podcast-refactor-executive-summary.md` | SUPERSEDED — refactor now formalized as P0a–P7 in `podcast-plan.yaml` | **DELETED** |
| `_workspace/podcast-orchestrator-large-books.md` | FOLDED — chunking rationale now `research/findings.md` §7 | **DELETED** after fold-in |
| `_workspace/primary-mac-activation.md` | STILL UNIQUE — one-time runbook for Azure bootstrap | **KEPT**, linked from this README |
| `_workspace/journal_podcast_processing_package/` | STALE SCAFFOLDING — pre-orchestrator source-chapter stubs | **MOVED** to `_workspace/_archive/` |
| `_workspace/.chats/vscode_claude_code_prompt_refinement.md` | SOURCE PROMPT — historical reference; content now in this plan | **KEPT** in `.chats/` |
