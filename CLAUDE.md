# podcast-factory repo — session orientation

You're in the **`podcast-factory`** repo (renamed from `Journal` on
2026-05-22 as part of the repo split — see [_workspace/runbooks/repo-split.md](_workspace/runbooks/repo-split.md)
for full migration history). This file is auto-loaded by Claude Code on
every session in this directory; treat it as your standing brief.

## What this repo contains

- **Podcast pipeline** (`scripts/podcast/`, `content/drafts/<slug>/` for per-book in-progress state, `content/published/books/<slug>/` for shipped catalog, `skills-staging/podcast/`) — multi-phase Claude+Azure pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series. Phases 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring → trainer → ship.
- **Content container** (`content/`) — single tree holding both `content/drafts/` (workshop, where the pipeline reads + writes) and `content/published/` (audience-facing catalog, populated exclusively by `scripts/podcast/ship_to_library.py`). The 2026-05-23 restructure flattened the prior `worktrees/` container, consolidated four books from book/* branches into `content/drafts/`, and renamed the old `library/` to `content/published/`. The `podcast-reader/` Astro app reads from `content/drafts/`; the future `podcast-viewer/` will read from `content/published/`.

The memoir engine (Asif IS Babu), the static `journal` site, the Anthropic API proxy (`server/`), and the Cloudflare deploy scaffold all moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of 2026-05-22. See §"Disconnected from journal" below.

## Cross-machine coordination — the model in 30 seconds

Two machines (Mac Studio + Mac Air) share **ONE git repo, ONE working
directory per machine**. Books are processed on `book/<slug>` branches; the
integration target is `develop`, which accumulates every shipped book +
framework upgrade. Production releases go `develop` → `main`.

Each machine has `~/.machine-id` containing either `mac-studio-primary` or
`macbook-air-secondary`. Per-machine operator files at
`_workspace/plan/operators/<machine-id>.md` carry that machine's current
state. **Each machine writes ONLY its own operator file** (rare WRITE
EXCEPTIONs documented per coord-protocol §15).

## Run this on session start, every time

```bash
bash _workspace/plan/operators/start-session.sh
```

The script identifies your machine via `~/.machine-id`, syncs develop,
switches to your assigned book branch, prints orchestrator state +
next_action. Exit codes:
- `0` = ready (act on the printed next_action)
- `1` = pre-flight failed (fix the cause shown and re-run)
- `2` = IDLE (no assigned book — claim from `_workspace/plan/book-queue.md` per the protocol there)

If `~/.machine-id` doesn't exist, the script tells you how to create it.

## Read these once per machine, or when conventions feel stale

- **`_workspace/plan/response-template.md`** — canonical 4-part response template (At a glance → body PROSE sections → Next with `A. (Recommended) Do all in sequence` default). **No custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed". No `**TL;DR:**` opener, no `## Project Status` block.
- **`_workspace/plan/response-conventions.md`** — full conventions doc with migration notes, deprecations, rationale.
- **`_workspace/plan/operators/index.md`** — cross-machine dashboard (Air ↔ Studio side-by-side + queue with cost/time estimates per book).
- **`_workspace/plan/book-queue.md`** — pull-on-demand work queue with claim + completion protocols (git-push-rejection mutex).
- **`_workspace/plan/operators/coordination-protocol.md`** — write/push/branch/quota/concurrency discipline. Wins over per-machine files in conflict.
- **`_workspace/plan/operators/<your-machine-id>.md`** — your machine's operator file (current_branch, current_book, next_action, status_tag).
- **`_workspace/plan/operators/setup/`** — recreate-from-scratch documentation: per-machine config ([setup/machines.md](_workspace/plan/operators/setup/machines.md)), Azure stack ([setup/azure-stack.md](_workspace/plan/operators/setup/azure-stack.md)), blank-Mac bootstrap ([setup/recreate-from-scratch.md](_workspace/plan/operators/setup/recreate-from-scratch.md)), runtime-compatibility matrix ([setup/runtime-compatibility.md](_workspace/plan/operators/setup/runtime-compatibility.md) — Claude Code canonical; Cowork verified unsuitable). Index at [setup/README.md](_workspace/plan/operators/setup/README.md).
- **`.github/agents/podcast-operator.agent.md`** — Asif's unified entry-point. Invoke `claude --agent podcast-operator` (or shorter `/podcast-operator` slash command in Claude Code chat, or shorter still `op` as a bash alias) from ANY machine, ANY branch, ANY worktree. Auto-detects machine, picks up where work was left off, surfaces drift across 6 dimensions, reads peer state from origin/develop, produces a quick recap + reminder in the 4-part At-a-glance template. Discovery-by-default; `--execute-safe` for known-safe auto-ops (fast-forward merges + frontmatter timestamp bumps). Distinct from `podcast-orchestrator` (autonomous pipeline driver). This is the "where am I, what's next?" agent.

## Authoritative truth

When operator files disagree with the orchestrator's state file, the state
file wins:

```bash
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/drafts/<book>/_system/orchestrator-state.json
```

Operator-file frontmatter is a snapshot for human eyes; `state.json` is the truth for any decision.

## Disconnected from `journal` (2026-05-22 split)

- **Memoir + site moved to the sibling [journal](https://github.com/asifhussain60/journal) repo**: `content/babu-memoir/`, `site/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` — all moved, none remain here.
- **Anthropic API proxy `server/` RETIRED**: the journal app no longer needs it; not migrated to journal either.
- **Cloudflare deploy scaffold RETIRED**: `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md` — all deleted; not migrated.
- **Duplicated general-utility items** (`clean-commit`, `cowork-brief`, `repo-surgeon`, `tell-me`, `usage-auditor` skills + CORTEX/refine-prompt/reconcile/operating-contract agents + `content/_shared/arabic/` + `reference/`): these stay here as INDEPENDENT copies; the journal repo has its own independent copies that evolve separately.

## What to do for a typical user request

Step 1: Run `start-session.sh`. Read its output.
Step 2: If the user is asking about pipeline work, the script's `next_action` is your starting point.
Step 3: If the user is asking about cross-machine state, read `index.md` (don't trust without confirming via state.json).
Step 4: Respond in the 4-part response template. No custom section labels.

## Conventions baseline

- **Auto-mode authorization** lets you act on small mechanical steps without asking; **halt-and-surface** for anything destructive, shared-state, or LLM-spending beyond the auto-mode envelope.
- **No emojis in code or commits** unless explicitly invited; **DO use status emojis (🟢 / 🟡 / 🔴 / ⚠)** in responses per response-template.
- **Markdown links for files and commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.

## Authorization tiers

The default discipline is "ask before each shared-state action." Below is
the standing relaxation — three tiers governing what you can do silently,
what you do then surface, and what always needs an explicit go-ahead.
When in doubt between tiers, pick the higher one. `## Do NOT` below
overrides this section in conflict.

**Tier 0 — Just do it (no per-action acknowledgement).**
- Reads of any file in this repo and the sibling `journal` repo
- `git status`, `git diff`, `git log`, `gh pr view`, `gh pr list`, `gh auth status`
- Importing pipeline scripts under `/usr/bin/python3` to verify they load
- Dry-run inspection (`--dry-run` flags, `jq` over `orchestrator-state.json`)
- Spawning research agents (Explore, Plan, general-purpose) for read-only investigation
- `git restore` of auto-generated artifacts under `content/drafts/<slug>/_system/` when the artifact is reproducible by re-running its generator script
- `security find-generic-password -s <name>` for existence checks (no `-w`)

**Tier 1 — Do, then surface in the At-a-glance.**
- Commit to my owned book branch (where "owned" = `current_branch` in `_workspace/plan/operators/<my-machine-id>.md` matches the target branch)
- Push to my owned book branch
- Queue-claim writes to `_workspace/plan/book-queue.md` following the claim protocol in `_workspace/plan/operators/coordination-protocol.md` §14
- `--retry-phase <phase>` on a book I own (recovery from stale `phase_status="running"` per the known orchestrator-resume bug)
- Phase advancement via `--resume <slug>` on an already-claimed, already-running book
- Regenerating auto-generated state files (`chapter-set-report.md`, `challenger-report.md`, mangle-map, etc.)
- Opening a DRAFT PR from my book branch to `develop`
- Writing my own operator file (`_workspace/plan/operators/<my-machine-id>.md`)
- `coord(<my-machine-id>): ...` style commits to `develop` for cross-machine state sync (matching the existing pattern at commits like `b9272ef`, `4e26c46`, `bd8020f`)

**Tier 2 — Always ask. One-line ask + single-sentence Next.**
- First-time orchestrator launch on a new book: `python3 scripts/podcast/orchestrate_book.py <slug>` (multi-hour LLM-spend gate)
- Marking a draft PR ready, or merging any PR into `develop` or `main`
- Force-push (any branch)
- Deleting branches
- Writing peer machine's operator file (e.g. `mac-studio-primary.md` from Air)
- `--no-verify`, `--amend`, `git reset --hard`, `git clean -f`, `rm` of tracked files
- Recreating retired surfaces (`server/`, `wrangler.toml`, `infra/cloudflare/`, `site-worker.js`)
- Reaching into the sibling `journal` repo's paths or scripts

Tier overrides: if the user says "just do it" for something in Tier 2,
that one-shot authorizes that one action — it doesn't promote the action
into Tier 1 for future sessions. If the user says "always" or "from now
on" for a Tier 2 action, that's a request to edit this tier list and
should be confirmed before the edit.

## Do NOT

- Cross-write a peer's operator file (except via the formalized WRITE EXCEPTION in coord-protocol §15)
- Push to the peer's book branch
- Run any orchestrator command (`scripts/podcast/orchestrate_book.py`) without checking your machine's assignment first
- Force-push to `main` or `develop`
- Bypass `git status` cleanliness before merges
- Re-create `server/`, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/` without explicit user authorization — these were retired 2026-05-22 for a reason.
- Reach into the sibling `journal` repo's paths or scripts — the repos are fully disconnected.
