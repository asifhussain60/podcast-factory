# Copilot instructions for the `podcast-factory` repo

GitHub Copilot auto-loads this file as project-wide guidance. Read it at the start of every Copilot Chat session. The companion deep brief is at [_workspace/plan/copilot-handoff.md](../_workspace/plan/copilot-handoff.md) — open and read it before touching anything; it carries the live execution state and the session log Copilot must append to before ending each session.

---

## Two-agent model — YOU (Copilot) + Claude Code, in parallel (LOCKED 2026-05-30)

This repo is worked by two agents at once. The split is **by directory** — stay in your lane and we never collide. (A regression audit on 2026-05-30 confirmed the boundary is safe *only if these rules hold*.)

**You (Copilot) own `plan-dashboard/**`** — the Astro site: React/TSX, TipTap, CSS, the editorial cockpit, the New-Content intake page, the editor enhancement layer. `npm run dev` is your inner loop.

**Claude owns everything else** — `scripts/podcast/**` (the Python pipeline), all prompts, `_rules.py`/`_doctrinal.py`, the `infra/claude-agents/*.md` specs, `docs/standards/*.md`, the plan (`_workspace/plan/refactor/plan.{yaml,md}`), and the three `plan-dashboard/src/data/*-snapshot.json` files.

**Hard rules (the anti-regression contract):**
1. **Do NOT edit Python, prompts, `_rules.py`, agent specs, the plan, or the snapshot JSONs.** They carry doctrinal + convergence-loop context you don't have, and the snapshot-regen hook does not fire for you — a plan edit by you leaves snapshots stale (a contract violation). If you think one is wrong, write it in your session log.
2. **Run `npm run lint:views` before any commit that touches a view** — there is no git pre-commit hook in this clone and Claude's hooks (Cortex reminder, ui-reviewer, snapshot-regen) do NOT fire for you, so the gate is manual and on you.
3. **The `_system/` JSON files are the editor↔pipeline API; Claude owns their schema.** Consume `editorial.ts` / `stage-review.ts` shapes — never fork a schema. Need a new field? Note it in the session log for Claude.
4. **TS↔Python mirror files are a shared seam** — `src/lib/content-paths.ts`↔`_paths.py`, `peq-scores.ts`↔`_quality.py`+`challenger_scoring.py`. If you touch a mirror, say so in the log; never let it diverge from its Python source.
5. **`git pull --rebase` before you start and before you push** — Claude commits pipeline work in parallel on the same branch.

Coordination is async through `_workspace/plan/copilot-handoff.md`: Claude writes your tickets there; you read at session start and append a session log at the end. Claude's mirror of these rules is in `CLAUDE.md` (the "Two-agent operating model" standing rule).

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
- Execution gate: no pipeline work, code change, or new feature executes without (1) a corresponding entry added to plan.md + plan.yaml, (2) `npm run snapshot` run to regenerate plan-dashboard views, and (3) Asif's explicit approval. This gate is non-negotiable regardless of authorization tier.

Severity emojis when they add signal: 🟢 / 🟡 / 🔴 / ⚠. Optional, not mandatory.

---

## Authorization tiers

Default discipline: "ask before each shared-state action." Three tiers govern relaxations:

**Tier 0 — Just do it.**
- File reads anywhere in this repo or the sibling `journal` repo
- `git status`, `git diff`, `git log`, `gh pr view/list`
- Dry-run inspection (`--dry-run`, `jq` over state files)
- Spawning research-only investigation
- Re-arming the heartbeat monitor after orchestrator resume/retry

**Tier 1 — Do, then surface.**
- Commit to `develop`
- Push `develop` to `origin`
- `--retry-phase <phase>` on a book
- Regenerating auto-generated state files
- Plan-dashboard snapshot regen (mandatory side-effect of any canonical-plan-file edit)

**Tier 2 — Always ask. One-line ask + single-sentence Next.**
- First-time orchestrator launch on a new book (multi-hour LLM spend)
- `publish_to_library.py <slug>` — copying from drafts to published
- Opening / merging a `develop` → `main` PR
- Force-push (any branch)
- Deleting branches or tracked files
- `--no-verify`, `--amend`, `git reset --hard`, `git clean -f`
- Recreating retired surfaces (`server/`, `wrangler.toml`, `infra/cloudflare/`)
- Reaching into the sibling `journal` repo

If Asif says "just do it" for a Tier 2 action, that one-shot authorizes that one action. It does NOT promote the action to Tier 1 for future sessions.

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
