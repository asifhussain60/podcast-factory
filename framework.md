# Podcast Factory Ecosystem Framework

**Version:** 4.0 (repo-split — renamed from `Journal` on 2026-05-22)
**Last updated:** 2026-05-22

This document governs the **`podcast-factory`** repo: the multi-phase podcast pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series, the Azure stack that powers OCR / translation / speech, and the agents/skills that support podcast authoring. Memoir + site work moved to the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of the 2026-05-22 split. The Anthropic API proxy (`server/`) and the Cloudflare deploy scaffold were retired the same day — see §"Retired" below. The previous cross-machine coordination model (operator files, machine-id detection, per-machine book branches) was retired 2026-05-23 — see §"Single-machine model" below.

---

## Content tree

Post-2026-05-23 restructure (one flat repo, content container with drafts + published children):

```
podcast-factory/
├── content/                                        ← CONTENT CONTAINER
│   ├── drafts/                                     ← WORKSHOP (was: _workspace/books/ + per-branch content/podcast/library/books/)
│   │   └── <slug>/                                 ← per-book in-progress state
│   │       ├── _system/
│   │       │   ├── orchestrator-state.json
│   │       │   ├── challenger-report.md
│   │       │   ├── series-plan.md
│   │       │   └── …
│   │       ├── chapter-contracts/
│   │       ├── chapters/                           ← TTS-safe source per chapter
│   │       ├── episodes/
│   │       ├── transcripts/
│   │       ├── m4a/                                ← rendered audio (when present)
│   │       ├── slide-decks/                        ← internal slide artifacts
│   │       └── meta.yml                            ← book-level state + provenance
│   │
│   └── published/                                  ← PUBLISHED CATALOG (was: library/, read-only by convention)
│       ├── _meta/catalog.md                        ← auto-generated cross-book index
│       ├── archetypes/                             ← cross-book reference (e.g., islamic-scholastic-text.md)
│       ├── books/<slug>/                           ← shipped per-book outputs
│       │   ├── index.md                            ← book metadata
│       │   ├── transcript/                         ← polished NotebookLM SOURCE per chapter
│       │   └── podcasts/                           ← episode bundles organized by series
│       └── {articles,documents,interviews,lectures,letters}/
│
└── _workspace/                                     ← operational docs only (NO books/ here anymore)
    ├── plan/                                       ← response template + design plans + proposals
    ├── setup/                                      ← azure-stack.md + machine bootstrap docs
    ├── orchestrator-logs/
    ├── runbooks/                                   ← incl. repo-split.md historical reference
    └── _archive/, audit/, chats/, proposals/
└── content/
    ├── _shared/arabic/                   ← independent copy of cross-utility data (journal has its own)
    └── podcast/
        ├── _README.md
        └── .skill/                       ← handbook + _learning substrate
            ├── ROADMAP.md
            ├── handbook/                 ← book-agnostic skill refs + templates
            └── _learning/                ← cross-book pattern learning substrate
```

Promotion from workspace → library is one-way and explicit via `scripts/podcast/ship_to_library.py`; manual edits to `content/published/` are CI-checked.

---

## Agents

| Agent | Location | Role |
|---|---|---|
| `podcast-operator` | `.github/agents/podcast-operator.agent.md` | Unified "where am I, what's next?" entry-point across machines |
| `podcast-orchestrator` | `.github/agents/podcast-orchestrator.agent.md` | Autonomous book-to-NotebookLM pipeline driver |
| `podcast-challenger` | `.github/agents/podcast-challenger.agent.md` | Semantic-quality review (convergence loop ≤3 iterations before any bundle ships) |
| `podcast-extract` | `.github/agents/podcast-extract.agent.md` | Single-chapter → NotebookLM bundle fast path |
| `podcast-trainer` | `.github/agents/podcast-trainer.agent.md` | Cross-book pattern learner; refines podcast-challenger + handbook with regression gates |
| `repo-surgeon` | `.github/agents/repo-surgeon.agent.md` | Holistic architecture audit, orphan cleanup, root hygiene |
| `refine-prompt` | `.github/agents/refine-prompt.agent.md` | Refines a raw request into one compact instruction-paragraph for Claude Opus 4.7 / Claude Code |
| `reconcile` | `.github/agents/reconcile.agent.md` | Reconciliation utility |
| `CORTEX` | `.github/agents/CORTEX.agent.md` | Skill BASELINE framework |
| `operating-contract` | `.github/agents/operating-contract.md` | Externalized operating contract |

---

## The podcast skill: `podcast`

**Purpose:** Convert scholarly Arabic books into NotebookLM Audio Overview podcast series.

**Owns:** `content/drafts/<slug>/` (orchestrator state + chapter contracts + chapters + episode drafts + transcripts), with promotion to `content/published/books/<slug>/` (shipped) via `ship_to_library.py`.

**Reads:** sources Asif provides + `content/podcast/.skill/handbook/` references + `content/_shared/arabic/` (read-only).

**Triggers:** `/podcast`, `/extract-chapter <ref>`, `claude --agent podcast-orchestrator`, `claude --agent podcast-operator`.

**Phases:** 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring (extract + framing + build → challenger convergence) → ship via `ship_to_library.py` → trainer.

---

## Single-machine model

The pipeline is **machine-agnostic**. Most work is done by Anthropic + Azure remotely (LLM calls, OCR, translation, speech), so the host machine carries no special-snowflake configuration. The repo runs the same way on any Mac with `python3`, `git`, and the Azure stack credentials (per [_workspace/setup/azure-stack.md](_workspace/setup/azure-stack.md)).

- **Per-content branches (locked 2026-05-24).** Every new piece of content (book, document, lecture, article, letter, interview, or generic draft) is processed on its own typed branch off `develop`. The branch name is `<prefix>/<full-slug>` where `<prefix>` derives from the content's `category` field via [scripts/podcast/_branching.py](scripts/podcast/_branching.py): `book/`, `doc/`, `lecture/`, `article/`, `letter/`, `interview/`, or `draft/` (fallback). Slugs are always full kebab-case (never abbreviated). Branches merge back to `develop` only after `podcast-publisher` ships the artifacts to `content/published/`.
- **No per-machine coordination.** The earlier two-machine model (operator files, `~/.machine-id` detection, book-queue mutex, coordination-protocol §15) was retired 2026-05-23. The cross-machine assignment layer is gone; content branches now serve only as isolation, not as work assignment.
- **`scripts/start-session.sh`** is the simplified session bootstrap — fetches origin, fast-forwards develop, surfaces in-flight content branches + next-action commands.

---

## Duplicated general-utility skills (also in sibling journal repo as independent copies)

| Skill | Purpose |
|---|---|
| `skills-staging/clean-commit/` | Pre-commit / commit-quality discipline |
| `skills-staging/cowork-brief/` | Refine raw request → compact instruction-paragraph |
| `skills-staging/repo-surgeon/` | Holistic architecture audit, orphan cleanup |
| `skills-staging/tell-me/` | Codebase tour / explainer skill |
| `skills-staging/usage-auditor/` | Token / API usage audit |

Each is an independent copy. Edits here do NOT cross-propagate to the sibling journal repo.

---

## Retired 2026-05-22

- **Anthropic API proxy** (`server/`) — Node/Express proxy bound to 127.0.0.1:3001. The journal app no longer needs the Anthropic API; this surface is gone from both repos. Not migrated to journal.
- **Cloudflare deploy scaffold** — `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`. Same reason: no Workers-served journal site any more.
- **Docs related to the retired stack** — `docs/anthropic-api-setup.md`, `docs/proxy-setup.md`.
- **External orphan** — the `journal` and `journal-dev` Cloudflare Workers on Cloudflare itself remain orphaned external state; Asif may delete via the Cloudflare dashboard when convenient.

---

## What lives in the sibling `journal` repo (NOT here)

- `content/babu-memoir/` (the memoir)
- `site/` (static React display of memoir chapters; local-only post-2026-05-22)
- `scripts/memoir/` + `scripts/site/`
- `skills-staging/journal/`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/`
- `.github/agents/journal-orchestrator.agent.md`, `.github/agents/journal-challenger.agent.md`
- `infra/claude-agents/journal-challenger.md`

---

## Azure-on-disk layout reminder

Azure resources retain the original `journal-*` naming convention (resource group `rg-journal-ai`, all `journal-*` cognitive services, storage, Key Vault). The `APP_NAME` field in `infra/azure/azure-config.env` was changed from `"journal"` to `"podcast-factory"` 2026-05-22 as a config-label change only; **no Azure-side rename was performed**, all resources keep their existing names indefinitely.

---

## Conventions

- **No emojis in code or commits** unless explicitly invited.
- **Status emojis (🟢 🟡 🔴 ⚠) in responses** per the 4-part response template (canonical at `_workspace/plan/response-template.md`).
- **Markdown links for files and commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.
- **Per-book ownership** — one book is owned by one machine at a time (see `_workspace/plan/book-queue.md`). Don't touch a book that's not on your machine's branch.
