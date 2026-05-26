# Copilot instructions for the `podcast-factory` repo

GitHub Copilot auto-loads this file as project-wide guidance. When Asif asks
you (in Copilot Chat in VSCode) about this repo, follow this orientation.

## What this repo is

- A **podcast-authoring pipeline** driving scholarly Arabic books through Claude + Azure → NotebookLM Audio Overview episodes (under `scripts/podcast/`, `content/drafts/<slug>/` for in-progress state, `content/published/books/<slug>/` for shipped catalog post-Phase-9.5)
- The **Azure stack** that powers OCR / translation / speech (under `infra/azure/`, `infra/launchd/`)
- **Cross-machine operator coordination** between Mac Studio + Mac Air (under `_workspace/plan/operators/`)
- A handful of general-utility skills + agents (duplicated from the sibling `journal` repo as of the 2026-05-22 split)

The memoir, the static journal site, and the Anthropic API proxy moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo on 2026-05-22 — don't reach into those paths from here.

## What this repo is NOT

- **Memoir engine** — moved to journal. `content/babu-memoir/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*` are NOT here.
- **Journal site** — moved to journal. `site/`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` are NOT here.
- **Anthropic API proxy** — `server/` retired 2026-05-22. Not here, not in journal.
- **Cloudflare deploy** — `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/` retired 2026-05-22.

## Machine-agnostic — single-machine model (2026-05-23)

The repo runs on any machine with `python3`, `git`, and the Azure credentials installed. Most work is done by Anthropic + Azure remotely — no host-machine specialness. The earlier two-machine model (operator files, `~/.machine-id` routing, per-machine book branches, book-queue mutex) was retired 2026-05-23.

- **Per-content branches off `develop` (locked 2026-05-24).** Every new piece of content runs on its own typed branch (`book/<slug>`, `doc/<slug>`, `lecture/<slug>`, `article/<slug>`, `letter/<slug>`, `interview/<slug>`, or `draft/<slug>` fallback). Source of truth for the prefix is [scripts/podcast/_branching.py](scripts/podcast/_branching.py). Branches merge to `develop` only after the `podcast-publisher` agent completes the move to `content/published/`. Slugs are full kebab-case, never abbreviated.
- Production releases: `develop` → `main` (requires Asif's explicit approval; never auto-promoted).
- Feature branches off `develop` are optional throwaways for risky changes that aren't content-pipeline work.

## When Asif asks you for help

**For pipeline / orchestration questions:** point him at running the session-starter, OR if he's already running it, work from its output:

```bash
bash scripts/start-session.sh
```

That script syncs origin/develop and lists in-flight books + the most common next-action commands.

**For code suggestions in `scripts/podcast/**`:** this is the pipeline framework. Test changes against `pytest scripts/podcast/tests/` before committing. Atomic commits to `develop` directly; force-push prohibited.

**For book content** (`content/drafts/<slug>/` for in-progress; `content/published/books/<slug>/` for shipped): publishing flows one-way via `scripts/podcast/publish_to_library.py <slug>`. Never edit `content/published/` by hand — it's the publishing-agent's output.

## Response format

Asif uses a **4-part At-a-glance-first template** across both tools (Copilot + Claude Code). Canonical reference: `_workspace/plan/response-template.md`. Multi-path Next blocks default to `A. (Recommended) Do all of the below in order (B → C → D)` with sub-paths.

Severity emojis: 🟢 ship-ready / 🟡 needs decision / 🔴 blocked / ⚠ caution.

## Conventions

- **No emojis in code or commits** unless invited; **DO use status emojis** in chat responses.
- **Markdown links for files + commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.
- **No force-push to `main` or `develop`.**
- **Honor `git status` cleanliness before merges.**
- **Don't re-create retired surfaces** (`server/`, `wrangler.toml`, `infra/cloudflare/`, etc.) without explicit user authorization.
