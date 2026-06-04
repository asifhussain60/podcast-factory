# Agent instructions for the `podcast-factory` repo

This file is auto-loaded by GitHub Copilot Chat. The same instructions in `CLAUDE.md` apply to Claude Code / Claude Cowork / any other LLM driver. The companion live-state brief is at [_workspace/plan/copilot-handoff.md](../_workspace/plan/copilot-handoff.md) — open and read it before any substantive work; it carries the current execution state and the session log you must append to before ending the session.

---

## LLM-agnostic operating model (LOCKED 2026-05-31)

This repo is **driver-agnostic**. Any LLM framework (Copilot, Claude Code, Cowork, future tools) operates under the same rules. There is **no directory ownership boundary** between agents — whichever agent is running can edit any file in the repo, Python or TypeScript or YAML, subject only to the Tier-2 list below and the quality gates.

**Core anti-regression rules — applied by whoever is at the keyboard:**

1. **Edit any file you need to** — Python pipeline, plan files, agent specs, dashboard components, snapshots. The 2026-05-30 lane boundary is retired; the new contract is quality-gate-based, not directory-based.
2. **After any edit to `_workspace/plan/architecture.md`, `_workspace/plan/refactor/plan.{md,yaml}`, or `_workspace/plan/debt/pipeline-debt.md`** → run `cd plan-dashboard && npm run snapshot` in the same response, before commit. Stage the regenerated `plan-dashboard/src/data/*.json` alongside the plan edit. Stale snapshots are a contract violation.
3. **Before any commit that touches an Astro page or view component** → run `cd plan-dashboard && npm run lint:views`. Errors block the commit; warnings are advisory.
4. **TS↔Python mirror files** — `plan-dashboard/src/lib/content-paths.ts` ↔ `scripts/podcast/_paths.py`, and `peq-scores.ts` ↔ `_quality.py` + `challenger_scoring.py`. When you change one side, update the other in the same commit.
5. **`git pull --rebase` before starting work and before pushing** — other agents (or other sessions of the same agent) may have committed in parallel.
6. **The `_system/` JSON files are the editor↔pipeline API.** Schema lives in `plan-dashboard/src/types/editorial.ts` and `stage-review.ts`. Either side can evolve the schema; both sides must be updated atomically in the same commit, with a one-line schema-bump note in the commit message.

The session log at the bottom of [copilot-handoff.md](../_workspace/plan/copilot-handoff.md) is the **across-session, across-agent memory**. Append a dated entry at the end of every session noting what changed, what's next, what's blocked.

---

## What this repo is

- A **podcast-authoring pipeline** driving scholarly Arabic books through Claude + Azure → NotebookLM Audio Overview episodes. Live state lives under `scripts/podcast/`, in-progress books under `content/drafts/<slug>/`, shipped books under `content/published/books/<slug>/`.
- The **Azure stack** (OCR / translation / speech) under `infra/azure/`, `infra/launchd/`, `infra/llm-apis/`.
- A handful of general-utility skills + agents (duplicated from the sibling `journal` repo as of the 2026-05-22 split).

The memoir, the static journal site, and the Anthropic API proxy moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo on 2026-05-22 — never reach into those paths from here.

## What this repo is NOT

- Memoir engine — moved to journal. `content/babu-memoir/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*` are NOT here.
- Journal site — moved to journal.
- Anthropic API proxy — `server/` retired 2026-05-22.
- Cloudflare deploy — `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/` retired 2026-05-22.

## Machine model

Single-machine, machine-agnostic (since 2026-05-23). `develop` is the working branch. `develop` → `main` requires Asif's explicit approval via PR (GitHub ruleset enforces this). Content runs on typed branches (`book/<slug>`, `doc/<slug>`, etc. — see `scripts/podcast/_branching.py`).

---

## Canonical sources of truth

| File | Role |
|---|---|
| [_workspace/plan/architecture.md](../_workspace/plan/architecture.md) | Timeless design doc: 6-layer module structure, 3 storage tiers, archetype registry, agent ecosystem. 13 ADRs. |
| [_workspace/plan/refactor/plan.md](../_workspace/plan/refactor/plan.md) | Human-readable 22-step roadmap (Waves A–E). |
| [_workspace/plan/refactor/plan.yaml](../_workspace/plan/refactor/plan.yaml) | Machine-readable companion to plan.md. |
| [_workspace/plan/debt/pipeline-debt.md](../_workspace/plan/debt/pipeline-debt.md) | Live F-item operational backlog. |
| [_workspace/plan/copilot-handoff.md](../_workspace/plan/copilot-handoff.md) | Deep brief + session log. **Read first, append before ending.** |

**These four files are load-bearing.** Any edit to any one of them MUST be followed in the same response, before commit, by `cd plan-dashboard && npm run snapshot` (regenerates the three JSONs the SPA reads). Then `git add plan-dashboard/src/data/*.json` alongside the plan-file change. Stale snapshots are a contract violation.

---

## Response format (Asif's canonical 2026-05-26 template)

Every substantive reply uses this shape:

```
## {Topical title — plain English, no jargon}

> **{Verdict in one line.}** {1–2 sentences supporting.}

### {Subheading that itself tells the story}

{Prose, OR a table for tabular data, OR another blockquote.}

---

### Next: 👤 Asif

A. **(Recommended)** {action sentence}. {brief reason + expected outcome}

B. {alternative}. {brief}
```

Hard rules:

- **Plain English only.** No `_authoring.py`, no `PHASE_0D`, no `R-PHONETICS`, no `T2`, no `--retry-phase` in the chat body. Task IDs, file paths, and acronyms stay in YAML/MD ledgers.
- **Headings: H2 main, H3 sections.** Subheadings must carry the gist.
- **Blockquotes (`>`) for callouts**, bold lead-in sentence.
- NO GitHub `[!TIP]` / `[!NOTE]` alerts — they don't render in Copilot Chat either. Use plain `>`.
- NO fenced code blocks for prose. Tables for tabular data; alphabetized options for Next.
- One horizontal rule, between the topical section and Next.
- Recommended is always A. When B/C/D are complementary follow-ups that compose without regression risk, A is **"Do all of the below in sequence — B then C then D"** with one why-batching line.
- Holistic selection: score every option against (1) project health, (2) architectural fit, (3) extensibility, (4) regression risk. **Always recommend the most thorough and architecturally complete approach as option A — never recommend a scoped-down or superficial alternative as the default unless the user explicitly requests a smaller scope.** Reduced regression risk justifies removing an option that would destabilize working code; it never justifies downgrading a thorough root fix to a partial symptom patch. REMOVE (don't demote) any option that destabilizes what's working.

Severity emojis when they add signal: 🟢 / 🟡 / 🔴 / ⚠. Optional, not mandatory.

**Plan-tracking discipline (not an execution gate):** When you ship a new step (a wave/slice marker, a new pipeline phase, a new feature surface), update `plan.yaml` and `plan.md` in the same commit and regenerate snapshots. For small bug fixes, refactors, and verification work that fits inside an existing plan entry, just do the work and note it in the commit + session log — no plan entry needed first. The plan tracks what shipped, not what's about to ship.

---

## Authorization tiers

Default discipline: **bias to action on reversible work, ask only for genuinely destructive or expensive actions.**

**Tier 0 — Just do it (no announcement needed).**
- All file reads, `git status`/`diff`/`log`, dry-runs, `jq` inspection
- Code edits anywhere in the repo (Python, TypeScript, YAML, markdown, configs)
- Running tests (`unittest discover`, `npm run build`, `lint:views`)
- Editing plan files + regenerating snapshots (run `npm run snapshot` in the same response)
- Editing agent specs in `.github/agents/` or `infra/claude-agents/`
- Spawning research-only subagents

**Tier 1 — Do, then surface in the response.**
- Commit to `develop`
- Push `develop` to `origin`
- `--retry-phase <phase>` on a book (recovering from stale `phase_status`)
- Regenerating auto-generated state files (challenger reports, mangle maps, etc.)

**Tier 2 — Always ask. One-line ask + single-sentence recommendation.**
- First-time orchestrator launch on a new book (multi-hour LLM spend)
- `publish_to_library.py <slug>` — copying from drafts to the audience-facing catalog
- Opening / merging a `develop` → `main` PR (production release)
- Force-push (any branch)
- Deleting branches or tracked files
- `--no-verify`, `--amend`, `git reset --hard`, `git clean -f`
- Recreating retired surfaces (`server/`, `wrangler.toml`, `infra/cloudflare/`)
- Reaching into the sibling `journal` repo's paths or scripts

If the user says "just do it" for a Tier 2 action, that one-shot authorizes that one action. It does NOT promote the action to Tier 1 for future sessions.

---

## Hard prohibitions

- Never force-push to `main` or `develop`.
- Never bypass `git status` cleanliness before merges.
- Never re-create `server/`, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/` without explicit authorization.
- Never reach into the sibling `journal` repo's paths or scripts.
- Never run the orchestrator on a new PDF without explicit user authorization (multi-hour LLM-spend gate).
- Never write a `Version: X.Y` header or `*v[0-9]*.md` filename — DR-009 in architecture.md forbids version stamps; the git history is the version log.
- Never create a file in `scripts/podcast/` longer than 600 lines — DR-005.

---

## Reusable prompts (Copilot's slash-command equivalent)

Available under [.github/prompts/](prompts/) — invoke from Copilot Chat with `/<name>`:

- `/session-handoff` — append a session-log entry to `_workspace/plan/copilot-handoff.md` before ending the session.

---

## Session protocol

1. **At the start**: read [_workspace/plan/copilot-handoff.md](../_workspace/plan/copilot-handoff.md) end-to-end. The session log at the bottom is your memory.
2. **During**: every edit to the four canonical plan files → `npm run snapshot` → stage the JSONs alongside the edit.
3. **At the end** (or when Asif says "wrap up"): run `/session-handoff` — append a dated entry to the session log with what changed, what's next, what's blocked.

Copilot has no persistent memory across sessions. The handoff doc IS the memory. Treat appending to it as non-optional.
