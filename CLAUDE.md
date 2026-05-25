# podcast-factory repo — session orientation

You're in the **`podcast-factory`** repo (renamed from `Journal` on
2026-05-22 as part of the repo split — see [_workspace/runbooks/repo-split.md](_workspace/runbooks/repo-split.md)
for full migration history). This file is auto-loaded by Claude Code on
every session in this directory; treat it as your standing brief.

## What this repo contains

- **Podcast pipeline** (`scripts/podcast/`, `content/drafts/<slug>/` for per-book in-progress state, `content/published/books/<slug>/` for shipped catalog, `skills-staging/podcast/`) — multi-phase Claude+Azure pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series. Phases 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring → trainer → ship.
- **Content container** (`content/`) — single tree holding both `content/drafts/` (workshop, where the pipeline reads + writes) and `content/published/` (audience-facing catalog, populated exclusively by `scripts/podcast/publish_to_library.py` invoked via the `podcast-publisher` agent). The 2026-05-23 restructure flattened the prior multi-worktree container, consolidated all in-flight books into `content/drafts/`, and renamed the old `library/` to `content/published/`. The `podcast-reader/` Astro app reads from `content/drafts/`; the future `podcast-viewer/` will read from `content/published/`.

The memoir engine (Asif IS Babu), the static `journal` site, the Anthropic API proxy (`server/`), and the Cloudflare deploy scaffold all moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of 2026-05-22. See §"Disconnected from journal" below.

## Machine-agnostic — single-machine model

Post-2026-05-23: this app is **machine-agnostic**. Most work is done by Anthropic + Azure remotely, so there's no cost difference between hosts. Production releases go `develop` → `main` (requires Asif's explicit approval; never auto-promoted).

The earlier cross-machine coordination model (operator files at `_workspace/plan/operators/`, `~/.machine-id` detection, `book-queue.md` mutex, coordination-protocol §15) was retired 2026-05-23. If you encounter references to operator files or "the peer machine" anywhere, treat them as stale documentation pending cleanup.

## Branch policy — content branches per piece of content (locked 2026-05-24)

Every new piece of content is processed on its own typed branch off `develop`. The branch is created at intake time and merged back to `develop` ONLY after the publish step completes. This isolates in-flight work from `develop`, preserves a clean per-content ledger, and lets multiple books be in flight without cross-contamination.

**Branch naming** is category-typed, with the **full kebab-cased slug** always (never abbreviated):

| Category | Prefix | Example |
|---|---|---|
| `books` | `book/` | `book/kitab-al-riyad` |
| `documents` | `doc/` | `doc/fatimid-decree-922` |
| `lectures` | `lecture/` | `lecture/kunooz-al-hikmah-01` |
| `articles` | `article/` | `article/cross-tradition-method` |
| `letters` | `letter/` | `letter/ayyuhal-walad` |
| `interviews` | `interview/` | `interview/asif-with-amir` |
| (unknown / unset) | `draft/` | `draft/some-unclassified-thing` |

Source of truth for the prefix map: [scripts/podcast/_branching.py](scripts/podcast/_branching.py) — every script that computes a branch name imports `branch_name(category, slug)` from there. Never hardcode `book/<slug>` anywhere.

**Lifecycle**:
1. `intake_book.py` creates `<prefix>/<slug>` from `develop` and copies the PDF/source.
2. Pipeline phases (0a → 0f → per-chapter → authoring → publish) all run on that branch.
3. `publish_to_library.py` (via the `podcast-publisher` agent) moves `content/drafts/<slug>/` → `content/published/books/<slug>/` after gates G1–G7 pass.
4. The orchestrator merges `<prefix>/<slug>` → `develop` with `--no-ff` after publish completes.
5. `develop` → `main` for production releases requires Asif's explicit approval (unchanged).

## Run this on session start

```bash
bash scripts/start-session.sh
```

The script does: `git fetch --all --prune`, switches to `develop` if needed, fast-forwards from `origin/develop`, surfaces a one-liner summary of books in flight, and lists the most common next-action commands. Exit codes:
- `0` = ready
- `1` = pre-flight failed (working tree dirty, or not in a git repo)

## Read these once, or when conventions feel stale

- **[_workspace/plan/response-template.md](_workspace/plan/response-template.md)** — canonical 4-part response template (At a glance → body PROSE sections → Next with `A. (Recommended) Do all in sequence` default). **No custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed". No `**TL;DR:**` opener, no `## Project Status` block.
- **[_workspace/plan/response-conventions.md](_workspace/plan/response-conventions.md)** — full conventions doc with migration notes, deprecations, rationale.
- **[_workspace/setup/azure-stack.md](_workspace/setup/azure-stack.md)** — Azure resources, keychain layout, recreate-from-scratch guide.
- **[_workspace/setup/bootstrap.md](_workspace/setup/bootstrap.md)** — blank-machine bootstrap for this repo.
- **[framework.md](framework.md)** — pipeline framework spec.

## Authoritative truth

The orchestrator's state file is the source of truth for any book's pipeline state:

```bash
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/drafts/<book>/_system/orchestrator-state.json
```

## Disconnected from `journal` (2026-05-22 split)

- **Memoir + site moved to the sibling [journal](https://github.com/asifhussain60/journal) repo**: `content/babu-memoir/`, `site/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` — all moved, none remain here.
- **Anthropic API proxy `server/` RETIRED**: the journal app no longer needs it; not migrated to journal either.
- **Cloudflare deploy scaffold RETIRED**: `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md` — all deleted; not migrated.
- **Duplicated general-utility items** (`clean-commit`, `cowork-brief`, `repo-surgeon`, `tell-me`, `usage-auditor` skills + CORTEX/refine-prompt/reconcile/operating-contract agents + `content/_shared/arabic/` + `reference/`): these stay here as INDEPENDENT copies; the journal repo has its own independent copies that evolve separately.

## What to do for a typical user request

1. Run `bash scripts/start-session.sh`. Read its output.
2. If the user is asking about pipeline work, the listed next-action commands are your starting point.
3. If the user is asking about a specific book's state, read its `content/drafts/<slug>/_system/orchestrator-state.json` via the `jq` command above.
4. Respond in the 4-part response template. No custom section labels.

## Conventions baseline

- **Auto-mode authorization** lets you act on small mechanical steps without asking; **halt-and-surface** for anything destructive or LLM-spending beyond the auto-mode envelope.
- **No emojis in code or commits** unless explicitly invited; **DO use status emojis (🟢 / 🟡 / 🔴 / ⚠)** in responses per response-template.
- **Markdown links for files and commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.

## Authorization tiers

The default discipline is "ask before each shared-state action." Below is the standing relaxation — three tiers governing what you can do silently, what you do then surface, and what always needs an explicit go-ahead. When in doubt between tiers, pick the higher one. `## Do NOT` below overrides this section in conflict.

**Tier 0 — Just do it (no per-action acknowledgement).**
- Reads of any file in this repo and the sibling `journal` repo
- `git status`, `git diff`, `git log`, `gh pr view`, `gh pr list`, `gh auth status`
- Importing pipeline scripts under `/usr/bin/python3` to verify they load
- Dry-run inspection (`--dry-run` flags, `jq` over `orchestrator-state.json`)
- Spawning research agents (Explore, Plan, general-purpose) for read-only investigation
- `git restore` of auto-generated artifacts under `content/drafts/<slug>/_system/` when the artifact is reproducible by re-running its generator script
- `security find-generic-password -s <name>` for existence checks (no `-w`)

**Tier 1 — Do, then surface in the At-a-glance.**
- Commit to `develop`
- Push `develop` to `origin`
- `--retry-phase <phase>` on a book (recovery from stale `phase_status="running"` per the known orchestrator-resume bug)
- Phase advancement via `--resume <slug>` on an in-progress book
- Regenerating auto-generated state files (`chapter-set-report.md`, `challenger-report.md`, mangle-map, etc.)
- Opening a DRAFT PR from a feature branch to `develop`
- Orchestrator's automatic `book/<slug>` → `develop` merge after the `publish` phase completes successfully — this is in-pipeline and not a separate gate
- Running `validate_ship_ready.py <slug>` (read-only G1-G7 gate runner — never writes files)
- Launching `watch_orchestrator.sh <slug>` for any long-running book phase (self-healing; survives session close)
- Arming a `CronCreate` 5-minute heartbeat (in-session visibility) whenever `watch_orchestrator.sh` is launched

**Tier 2 — Always ask. One-line ask + single-sentence Next.**
- First-time orchestrator launch on a new book: `python3 scripts/podcast/orchestrate_book.py <pdf>` followed immediately by `bash scripts/podcast/watch_orchestrator.sh <slug>` + a `CronCreate` 5-min heartbeat (multi-hour LLM-spend gate; always launch via watchdog so the run self-heals)
- `publish_to_library.py <slug>` — copying the finalized book from `content/drafts/` to `content/published/books/` (the audience-facing catalog). The orchestrator's new `finalize` phase halts BEFORE publish so Asif can review the clean version in podcast-reader and run post-pipeline analyses (A/B transcription, etc.); resuming the orchestrator after that human review is what authorizes publish.
- Opening a `develop` → `main` PR, marking it ready, or merging it (production release gate — never auto-promoted)
- Force-push (any branch)
- Deleting branches
- `--no-verify`, `--amend`, `git reset --hard`, `git clean -f`, `rm` of tracked files
- Recreating retired surfaces (`server/`, `wrangler.toml`, `infra/cloudflare/`, `site-worker.js`)
- Reaching into the sibling `journal` repo's paths or scripts

Tier overrides: if the user says "just do it" for something in Tier 2, that one-shot authorizes that one action — it doesn't promote the action into Tier 1 for future sessions. If the user says "always" or "from now on" for a Tier 2 action, that's a request to edit this tier list and should be confirmed before the edit.

## Do NOT

- Run any orchestrator command (`scripts/podcast/orchestrate_book.py`) on a new PDF without explicit user authorization (multi-hour LLM-spend gate)
- Force-push to `main` or `develop`
- Bypass `git status` cleanliness before merges
- Re-create `server/`, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/` without explicit user authorization — these were retired 2026-05-22 for a reason.
- Reach into the sibling `journal` repo's paths or scripts — the repos are fully disconnected.
