# Podcast Pipeline — Phased Plan

**Scope:** podcast agent + skill **ONLY**. Journal is out of scope and must remain fully separate.
**Plan version:** **v3** — sequential renumbering + 6-wave grouping + SDK migration cancelled + Numeric/Symbolic Disambiguation folded in as P4. Restructured 2026-05-19.

## Contents

| File | Purpose |
|---|---|
| [`podcast-plan.yaml`](./podcast-plan.yaml) | Canonical phased plan. Single source of truth. **v3:** 6 waves (W1–W6) · 20 phases (P1–P20) · `claude -p` (Claude Code) is the primary execution mechanism. |
| [`acceptance-criteria.md`](./acceptance-criteria.md) | **Master SHIP/DONE checklist.** Every measurable promise rendered as a checkbox; audited by `/repo-surgeon --plan-only` Pass 5. |
| [`view/index.html`](./view/index.html) | Rich HTML view with SVG architecture diagrams + wave structure + P4 protocol diagram. Open in browser. Modernized for v3: semantic landmarks, skip-link, prefers-color-scheme, fluid type. |
| [`numeric-symbolic-disambiguation-plan.md`](./numeric-symbolic-disambiguation-plan.md) | Design document for P4 (Numeric/Symbolic Disambiguation). Authoritative for the protocol; folded into the canonical YAML as P4.1–P4.8 in v3. |
| [`research/findings.md`](./research/findings.md) | Web-research citations, sample-book corpus, chunking rationale, system-check snapshot. |
| [`../primary-mac-activation.md`](../primary-mac-activation.md) | One-time runbook for bootstrapping a primary Mac (Azure provisioning). Referenced by Q1. |

## How to consume

1. **Read first:** `view/index.html` — visual overview, wave diagrams, phase timeline, P4 protocol flow.
2. **Execute from:** `podcast-plan.yaml` — exact tasks, acceptance criteria, dependencies, wave kickoff commands.
3. **Track ship-readiness:** `acceptance-criteria.md` — check off rows as you verify each acceptance condition.
4. **Reference:** `research/findings.md` + `numeric-symbolic-disambiguation-plan.md` — why each decision was made, with sources.

## Bounded scope (do NOT cross)

| In scope | Out of scope |
|---|---|
| `.github/agents/podcast-orchestrator.agent.md` | `.github/agents/journal-*.agent.md` |
| `.github/agents/podcast-trainer.agent.md` | `.github/agents/CORTEX.agent.md`, `reconcile.agent.md`, `repo-surgeon.agent.md` |
| `.github/agents/podcast-challenger.agent.md` *(P16 migration)* | `skills-staging/journal/**` |
| `.github/agents/podcast-extract.agent.md` *(P16 migration)* | `scripts/memoir/**`, `scripts/site/**` |
| `skills-staging/podcast/**` | `content/babu-memoir/**` |
| `scripts/podcast/**` | `content/_shared/**` *(see P4 exception below)* |
| `content/podcast/**` | `docs/architecture/journal-*.html`, `docs/architecture/index.html` |
| `docs/architecture/podcast-*.html` | |

**P4 exception:** A single whitelisted write — `content/_shared/arabic/06-abjad-numerals.md` — created once by P4 and READ-ONLY thereafter. Captured in `meta.scope_in_writes_to_shared_exception` and honored by `scripts/podcast/_boundary_check.py` (P1.1). No other writes to `content/_shared/**` are permitted from the podcast skill.

The podcast service, API, dashboards, and other capabilities described here **must not** depend on, import from, or modify any journal code path. Cross-cutting infrastructure (git hooks, .gitignore, virtualenv) is the only allowed shared surface. **P1 verifies the boundary; P16 wires the CI check.**

## Primary execution mechanism: Claude Code

**v3 directive:** `claude -p --permission-mode acceptEdits` (Claude Code in headless mode) is the canonical workhorse for every LLM call in `scripts/podcast/` — refinement, phonetics, chapter design, enrichment, framing, building, challenger, trainer. The wholesale Anthropic-Python-SDK migration formerly planned as v2 P3 is **cancelled**. The Anthropic Python SDK is reserved for narrow side-channel use: P6 cost-ledger token counting and P8 status-API helper calls. See principle `P-1` in the YAML for full rationale.

## System check snapshot (2026-05-19)

| Domain | Status |
|---|---|
| Azure CLI / subscription | ✅ logged in to `Journal AI — primary` |
| Azure resources | ✅ `journal-docintel`, `journal-translator`, `journal-speech` (all in `rg-journal-ai`/eastus) |
| Claude CLI / Python / Node | ✅ 2.1.144 / 3.14.4 / v24.15.0 |
| gh CLI | ⚠️ unauthenticated (non-blocking for plan work) |
| Git | ⚠️ on `book/master-disciple-notebooklm-scaffolding`; uncommitted plan changes (this v3 restructure + numeric plan) |
| Active orchestrator runs | ✅ none |
| `kitab-al-riyad` state | ✅ resumable (0a complete, 0b pending P5 fix, zero orphan chunks) |

Full diagnostic table in [`research/findings.md`](./research/findings.md) §8.

## Wave + phase summary (v3)

Each wave is one autonomous scheduled-task unit. Run via `scripts/podcast/run_wave.py <N>` (created in Wave 1).

| Wave | Phases | Effort | Blocks | Schedule intent |
|---|---|---|---|---|
| **W1 Foundation & Guardrails** | P1 (boundary), P2 (E2E), P3 (doc-fix), **P4 (numeric ★)**, P5 (perm-fix), P6 (cost-ledger) | 2–4 days parallel | W2 | Overnight; zero LLM cost |
| **W2 Observability** | P7 (heartbeat), P8 (status API + dashboard) | 4–6 days | W3, W4 | Daytime; trivial LLM cost |
| **W3 Corpus Validation** | P9 (7-book graduated runs), P10 (ETA model) | ~1 wk wall-clock | W4 | One book per scheduled invocation; cost-capped |
| **W4 Control Plane** | P11 (multi-Mac), P12 (mutation API), P13 (SQLite), P14 (destructive confirms) | ~1 wk | W5 | Single window; mutation surface live |
| **W5 Polish** | P15 (orchestrator phase rename), P16 (agent dedup + isolation CI) | 3–5 days | W6 | **HARD-GATED:** zero in-flight books |
| **W6 Deferred** | P17 PDF split · P18 parallel LLM · P19 trainer SQLite · P20 browser upload | per-phase | — | Trigger-gated, not time-scheduled |

★ = new in v3. Cancelled in v3: v2 P3.1–P3.6 (wholesale SDK migration), v2 P6.4 (SDK token-count parity), v2 P6.5 (SDK fallback retirement).

## Status

- **Current:** v3 restructure landed (this commit). W1 not yet executed.
- **Next:** Run W1 (P1 + P2 + P3-done + P4 + P5 + P6) → resume `book/kitab-al-riyad` post-P5 → kick off W2 once W1 acceptance rows pass.

## v3 restructure pass (2026-05-19)

Three structural changes:

1. **Sequential renumbering with wave grouping.** `P0a / P0b / P0c / P0 / P1..P7` → `P1..P20` across 6 named waves. Legacy IDs preserved in `meta.legacy_id_map` for one release. Each wave is an autonomous scheduled-task unit with a kickoff command and a DONE signal sourced from `acceptance-criteria.md`.
2. **Claude Code is the primary execution mechanism.** The v2 SDK migration is cancelled. `claude -p --permission-mode acceptEdits` becomes the long-term mechanism, not the band-aid.
3. **Numeric/Symbolic Disambiguation as P4 (Wave 1).** Folded in from `numeric-symbolic-disambiguation-plan.md`. Includes: canonical abjad-numerals shared file, disambiguation handbook, podcast-challenger Loop N, Phase-0d numeric-scan step, Master & Disciple Ch-02 worked example (8 ambiguities tracked: 4 RESOLVED, 4 NEEDS HUMAN REVIEW → open questions Q4–Q7).

## Legacy-file triage (carried from v2; 2026-05-19)

| File | Verdict | Action taken |
|---|---|---|
| `_workspace/chatgpt-podcast-skill-prompt.md` | SUPERSEDED — content absorbed into `skills-staging/podcast/SKILL.md` and this plan | **DELETED** |
| `_workspace/folder-cleanup-prompt.md` | SUPERSEDED — supplanted by current repo structure + W5 of this plan | **DELETED** |
| `_workspace/podcast-refactor-executive-summary.md` | SUPERSEDED — refactor now formalized as W1–W6 in `podcast-plan.yaml` | **DELETED** |
| `_workspace/podcast-orchestrator-large-books.md` | FOLDED — chunking rationale now `research/findings.md` §7 | **DELETED** after fold-in |
| `_workspace/primary-mac-activation.md` | STILL UNIQUE — one-time runbook for Azure bootstrap | **KEPT**, linked from this README |
| `_workspace/journal_podcast_processing_package/` | STALE SCAFFOLDING — pre-orchestrator source-chapter stubs | **MOVED** to `_workspace/_archive/` |
| `_workspace/.chats/vscode_claude_code_prompt_refinement.md` | SOURCE PROMPT — historical reference; content now in this plan | **KEPT** in `.chats/` |
