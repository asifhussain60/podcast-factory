# infra/claude-agents/

Canonical agent specifications for the podcast-factory repo.

**One canonical spec per agent. This directory is the single source of truth.**

The `.github/agents/` directory contains thin discovery stubs (≤15 lines each) that
point here. Claude Code and Copilot load these stubs for agent discovery; all
substantive procedure, authority files, and tier authorization live in this directory.

---

## Agent registry (18 agents)

| Agent | Purpose |
|---|---|
| `html-view-challenger` | Conformance validator for HTML views against the Cortex quality standard |
| `podcast-auditor` | Repo-level health audit — surfaces drift, regressions, and gaps |
| `podcast-blueprint` | Content-aware episode-structure planner (genre classification → episode plan) |
| `podcast-challenger` | Semantic quality validator for chapters and framings; convergence loop |
| `podcast-extract` | Single-chapter → NotebookLM bundle path orchestrator |
| `podcast-librarian` | Knowledge-extraction agent (Quran + hadith atoms → canonical library) |
| `podcast-orchestrator` | Autonomous book-to-NotebookLM pipeline driver |
| `podcast-planner` | Guardian + Builder for plan audits and roadmap step execution |
| `podcast-publisher` | Publish-gate enforcer — moves drafts to published after G1–G7 pass |
| `podcast-trainer` | Cross-book pattern learner; proposes regression-gated spec refinements |
| `postprod-review` | Post-production audio audit from Turboscribe transcripts |
| `project-steward` | Strategic health advisor; composes other agents; corpus-cited recommendations |
| `reconcile` | Code-first doc reconciliation — fixes code gaps before updating architecture views |
| `refine-prompt` | Refines raw requests into compact instruction paragraphs for Claude |
| `repo-surgeon` | Holistic repo auditor — 5-pass sweep (structure, code, architecture, brittleness, plan conformance) |
| `slide-deck-challenger` | Visual quality validator for slide-deck bundles |
| `vacuum` | Post-production filesystem cleanup and file normalization |

---

## DR-014 — Stub pattern

**Decision**: Agent canonical spec lives in `infra/claude-agents/`. `.github/agents/`
stubs register the agent for GitHub Actions and Copilot routing and point here.

**Stub format** (≤15 lines):

```markdown
---
name: <agent-name>
description: "<description matching the infra spec>"
---

This file is a discovery stub. Full specification at [infra/claude-agents/<name>.md](../../infra/claude-agents/<name>.md).
```

**Rationale**: Eliminates spec drift from duplicate full specs, reduces maintenance
surface, and makes the install script (`scripts/install-claude-skills.sh`) the single
installation path.

---

## Operating contract

The behavioral floor every agent enforces lives at
[reference/operating-contract.md](../../reference/operating-contract.md).
Agents read this file at invocation time; they never inline its full text.

---

## Installation

```bash
bash scripts/install-claude-skills.sh
```

The script reads from this directory and installs/updates the agent definitions into
`.claude/agents/<name>.md` at runtime. `.claude/` is gitignored (per-machine state);
this directory is the durable tracked source. Never edit `.claude/agents/` directly —
the next install will overwrite it.
