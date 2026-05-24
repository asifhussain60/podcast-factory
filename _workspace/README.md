# `_workspace/` — tracked workspace for plans + runbooks + setup

The repo's tracked planning + procedures zone. Everything in here is meta — plan documents, response conventions, bootstrap runbooks, archived material. No runtime code, no book content. Runtime code lives under [`scripts/`](../scripts/); book content lives under [`content/`](../content/).

## Layout

| Path | Purpose |
|---|---|
| [`plan/`](plan/) | Canonical pipeline plan (YAML + acceptance criteria + research notes) and the canonical [response-template.md](plan/response-template.md) + [response-conventions.md](plan/response-conventions.md) governing every Claude session in this repo. |
| [`setup/`](setup/) | One-time setup: [bootstrap.md](setup/bootstrap.md) for new Macs; [azure-stack.md](setup/azure-stack.md) for the full Azure resource reference. |
| [`runbooks/`](runbooks/) | Procedures used at intervals — e.g. [claude-code-bootstrap-prompt.md](runbooks/claude-code-bootstrap-prompt.md) to audit a fresh session's capabilities. |
| [`chats/`](chats/) | Persistent prompts and chat artifacts (cowork briefs, repro instructions). |
| `_archive/` | Historical material kept for context. Read-only. |

## What was here pre-2026-05-23 and is now gone

The earlier multi-machine coordination model lived under `_workspace/plan/operators/`:

- Operator files (`<machine-slug>.md` per Mac)
- A coordination protocol document
- A book-queue mutex with claim/completion protocols
- A `start-session.sh` rooted in `_workspace/plan/operators/`

All retired on 2026-05-23 when the repo became single-machine and machine-agnostic. The session-starter moved to [`scripts/start-session.sh`](../scripts/start-session.sh); there is no operator file to author, no machine identity to set, no queue to claim from. If you see references to any of those in older docs, treat them as historical and follow [CLAUDE.md](../CLAUDE.md) and [framework.md](../framework.md) instead.

## Branch propagation

This directory propagates across branches via the standard merge flow (`book/<slug>` → `develop` → `main`). All `_workspace/` content is editable on any branch; merges back to develop via the normal `--no-ff` flow.

- [`plan/podcast-plan.yaml`](plan/podcast-plan.yaml) — canonical on whichever branch most recently edited it; check the file's most-recent commit before editing.
- [`plan/response-conventions.md`](plan/response-conventions.md) + [`plan/response-template.md`](plan/response-template.md) — Asif edits the canonical version; every machine pulls from `develop`.
- [`runbooks/`](runbooks/) — propagates everywhere; rarely changes.
- `_archive/` — propagates everywhere; never changes.
- [`chats/`](chats/) — propagates everywhere; archived prompts.

## What "no root-level sprawl" means here

- `_workspace/` itself contains only `README.md` and a small set of subdirectories — no loose files at this level.
- Each subdirectory has its own `README.md` orienting its contents.
