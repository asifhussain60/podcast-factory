# Copilot instructions for the `podcast-factory` repo

GitHub Copilot auto-loads this file as project-wide guidance. When Asif asks
you (in Copilot Chat in VSCode) about this repo, follow this orientation.

## What this repo is

- A **podcast-authoring pipeline** driving scholarly Arabic books through Claude + Azure → NotebookLM Audio Overview episodes (under `scripts/podcast/`, `_workspace/books/<slug>/` for in-progress state, `library/books/<slug>/` for shipped catalog post-Phase-9.5)
- The **Azure stack** that powers OCR / translation / speech (under `infra/azure/`, `infra/launchd/`)
- **Cross-machine operator coordination** between Mac Studio + Mac Air (under `_workspace/plan/operators/`)
- A handful of general-utility skills + agents (duplicated from the sibling `journal` repo as of the 2026-05-22 split)

The memoir, the static journal site, and the Anthropic API proxy moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo on 2026-05-22 — don't reach into those paths from here.

## What this repo is NOT

- **Memoir engine** — moved to journal. `content/babu-memoir/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*` are NOT here.
- **Journal site** — moved to journal. `site/`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` are NOT here.
- **Anthropic API proxy** — `server/` retired 2026-05-22. Not here, not in journal.
- **Cloudflare deploy** — `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/` retired 2026-05-22.

## Cross-machine model

Two physical machines (Mac Studio + Mac Air) coordinate via:
- **ONE shared git repo, ONE working directory per machine**
- Books processed on `book/<slug>` branches; integration via `develop`
- Each machine carries `~/.machine-id` (`mac-studio-primary` or `macbook-air-secondary`)
- Per-machine operator files at `_workspace/plan/operators/<machine-id>.md`

The full discipline lives in `_workspace/plan/operators/coordination-protocol.md`.

## When Asif asks you for help

**For pipeline / orchestration / coord questions:** point him at running the session-starter, OR if he's already running it, work from its output:

```bash
bash _workspace/plan/operators/start-session.sh
```

That script tells you the current book, branch, phase, and next_action.

**For code suggestions in `scripts/podcast/**`:** this is shared framework. Changes here affect both machines; coordinate via `develop` merges. Reference `_workspace/plan/operators/coordination-protocol.md` §6 (shared-infra zones).

**For book content** (`_workspace/books/<slug>/` for in-progress; `library/books/<slug>/` for shipped): one book is owned by one machine at a time (see `_workspace/plan/book-queue.md` In-flight section). Don't touch a book that's not on your machine's branch.

## Response format

Asif uses a **4-part At-a-glance-first template** across both tools (Copilot + Claude Code). Canonical reference: `_workspace/plan/response-template.md`. Multi-path Next blocks default to `A. (Recommended) Do all of the below in order (B → C → D)` with sub-paths.

Severity emojis: 🟢 ship-ready / 🟡 needs decision / 🔴 blocked / ⚠ caution.

## Conventions

- **No emojis in code or commits** unless invited; **DO use status emojis** in chat responses.
- **Markdown links for files + commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.
- **No force-push to `main` or `develop`.**
- **Honor `git status` cleanliness before merges.**
- **Don't re-create retired surfaces** (`server/`, `wrangler.toml`, `infra/cloudflare/`, etc.) without explicit user authorization.
