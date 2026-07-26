# infra/claude-agents/

Canonical agent specifications for the podcast-factory repo.

**One canonical spec per agent. This directory is the single source of truth.**

The `.github/agents/` directory carries a full byte-identical mirror of each spec
(`<name>.agent.md`) for Claude Code / Copilot discovery. The DR-014 thin-stub
pattern below was never rolled out — in practice both copies are full text. Any
edit to a spec MUST be applied to both files in the same commit so the trees
stay byte-identical (verify with `cmp`).

---

## Agent registry (23 agents)

Alphabetical. Each row has one canonical spec in this directory plus a byte-identical
`.github/agents/<name>.agent.md` mirror.

| Agent | Purpose |
|---|---|
| `book-challenger` | Semantic-fidelity challenger for the reading-edition PDF (augmented companion + articulated translation editions) |
| `book-publisher` | Physical delivery — copies a book's audio (m4a) + reading-edition PDF to a target folder (default: Google Drive) |
| `book-render-challenger` | Print-render challenger for the rendered reading-edition PDF (blank pages, split figures, watermark, page fill) |
| `docs-updater` | Regenerates the single architecture view at `docs/architecture/index.html` from current repo truth (idempotent) |
| `html-view-challenger` | Conformance validator for HTML views against the Cortex quality standard (STATIC, source-level) |
| `noise-auditor` | Cross-surface detector for authorial-apparatus noise (circulation/provenance/colophon) the denoise step never strips; identify-only |
| `podcast-blueprint` | Content-aware episode-structure planner (genre classification → episode plan) |
| `podcast-challenger` | Semantic quality validator for chapters and framings; convergence loop |
| `podcast-extract` | Single-chapter → NotebookLM bundle path orchestrator |
| `podcast-librarian` | Knowledge-extraction agent (Quran + hadith atoms → canonical library) |
| `podcast-orchestrator` | Autonomous book-to-NotebookLM pipeline driver |
| `podcast-planner` | Guardian + Builder for plan audits and roadmap step execution |
| `podcast-publisher` | Publish-gate enforcer — flips status draft→published in place after gates pass |
| `podcast-trainer` | Cross-book pattern learner; proposes regression-gated spec refinements |
| `postprod-review` | Post-production audio audit from downloaded m4a transcripts |
| `project-steward` | Strategic health advisor; composes other agents; corpus-cited recommendations |
| `reconcile` | Code-first doc reconciliation — fixes code gaps before updating architecture views |
| `refine-prompt` | Refines raw requests into compact instruction paragraphs for Claude |
| `repo-surgeon` | Holistic repo auditor — 5-pass sweep (structure, code, architecture, brittleness, plan conformance) |
| `site-health-sentinel` | Runtime + visual-QA gate for the Astro site — boots a browser, sweeps every route for console errors, screenshots at desktop/mobile across states, judges pixels for visual defects, fixes in-pattern; the runtime peer of `html-view-challenger` |
| `slide-deck-challenger` | Visual quality validator for slide-deck bundles |
| `vacuum` | Post-production filesystem cleanup and file normalization |

**Deprecated (no spec file):** `podcast-auditor` — retired 2026-06-02; use `repo-surgeon --scope podcast` instead.

---

## DR-014 — Stub pattern (NOT IMPLEMENTED — kept for the record)

**Decision**: Agent canonical spec lives in `infra/claude-agents/`. `.github/agents/`
stubs register the agent for GitHub Actions and Copilot routing and point here.
**Status 2026-06-09**: the stub rollout never happened; `.github/agents/` holds full
mirrored copies instead. Until/unless stubs are rolled out, treat the two trees as a
synchronized mirror (same-commit edits, byte-identical).

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
[docs/reference/operating-contract.md](../../docs/reference/operating-contract.md).
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
