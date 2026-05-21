# Journal repo — session orientation

You're in the Journal repo. This file is auto-loaded by Claude Code on every
session in this directory; treat it as your standing brief.

## What this repo contains

- **Podcast pipeline** (`scripts/podcast/`, `content/podcast/library/books/`, `skills-staging/podcast/`) — multi-phase Claude+Azure pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series. Phases 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring → trainer → ship.
- **Babu memoir** (`content/babu-memoir/`, `skills-staging/journal/`) — Asif's memoir authoring engine. Asif IS Babu (the memoir's protagonist).
- **Trip skills** (`skills-staging/trips/`) — travel-planning skills.
- **Public-facing site** (`site/`) — Babu's journal site rendered to `site/`.

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

- **`_workspace/plan/response-conventions.md`** — BLUF response format (TL;DR / Status emoji / Body with per-issue blocks OR tables / Your next step). **No custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed" — those fragment cross-machine scannability.
- **`_workspace/plan/operators/index.md`** — cross-machine dashboard (Air ↔ Studio side-by-side + queue with cost/time estimates per book).
- **`_workspace/plan/book-queue.md`** — pull-on-demand work queue with claim + completion protocols (git-push-rejection mutex).
- **`_workspace/plan/operators/coordination-protocol.md`** — write/push/branch/quota/concurrency discipline. Wins over per-machine files in conflict.
- **`_workspace/plan/operators/<your-machine-id>.md`** — your machine's operator file (current_branch, current_book, next_action, status_tag).
- **`_workspace/plan/operators/setup/`** — recreate-from-scratch documentation: per-machine config ([setup/machines.md](_workspace/plan/operators/setup/machines.md)), Azure stack ([setup/azure-stack.md](_workspace/plan/operators/setup/azure-stack.md)), blank-Mac bootstrap ([setup/recreate-from-scratch.md](_workspace/plan/operators/setup/recreate-from-scratch.md)), runtime-compatibility matrix ([setup/runtime-compatibility.md](_workspace/plan/operators/setup/runtime-compatibility.md) — Claude Code canonical; Cowork verified unsuitable). Index at [setup/README.md](_workspace/plan/operators/setup/README.md).
- **`.github/agents/operator-sync.agent.md`** — cross-machine sync diff agent. Invoke `claude --agent operator-sync` (discovery only) or add `--execute-safe` for known-safe auto-ops. Replaces bespoke sync-prompt crafting for routine "are we in sync?" checks.

## Authoritative truth

When operator files disagree with the orchestrator's state file, the state
file wins:

```bash
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/<book>/_system/orchestrator-state.json
```

Operator-file frontmatter is a snapshot for human eyes; `state.json` is the truth for any decision.

## What to do for a typical user request

Step 1: Run `start-session.sh`. Read its output.
Step 2: If the user is asking about pipeline work, the script's `next_action` is your starting point.
Step 3: If the user is asking about cross-machine state, read `index.md` (don't trust without confirming via state.json).
Step 4: Respond in BLUF format. No custom section labels.

## Conventions baseline (the few that aren't already in response-conventions.md)

- **Asif IS Babu** (relevant for memoir work; not relevant for podcast work).
- **Auto-mode authorization** lets you act on small mechanical steps without asking; **halt-and-surface** for anything destructive, shared-state, or LLM-spending beyond the auto-mode envelope.
- **No emojis in code or commits** unless explicitly invited; **DO use status emojis (🟢 / 🟡 / 🔴 / ⚠)** in responses per response-conventions.md.
- **Markdown links for files and commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/Journal/commit/abc1234)`.

## Do NOT

- Cross-write a peer's operator file (except via the formalized WRITE EXCEPTION in coord-protocol §15)
- Push to the peer's book branch
- Run any orchestrator command (`scripts/podcast/orchestrate_book.py`) without checking your machine's assignment first
- Force-push to `main` or `develop`
- Bypass `git status` cleanliness before merges
