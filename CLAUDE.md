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
# Pre-F33-second / pre-F37 minimal probe:
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/drafts/<book>/_system/orchestrator-state.json

# Post-2026-05-25 wave full probe (recommended — surfaces graceful-degrade + timing + cost):
jq '{
    phase, phase_status, last_completed_phase, last_error,
    completed_slugs: .phases."per-chapter".completed_slugs,
    failed_slugs:    .phases."per-chapter".failed_slugs,
    chapter_timings: .phases."per-chapter".chapter_timings,
    audit_outcomes:  .phases."0g".audit_outcomes
}' content/drafts/<book>/_system/orchestrator-state.json
```

`phase=finalize, phase_status=halted` means "ready for publish review" — run [scripts/podcast/cross_book_dashboard.py](scripts/podcast/cross_book_dashboard.py) for the fleet view, then `python3 scripts/podcast/publish_to_library.py <slug>` (Tier 2 — always ask) when satisfied.

## Standing operator rules (mirror of AI memory)

These are recoverable on disk so a fresh Claude session without memory state can pick them up. The AI memory at `~/.claude/projects/-Users-asifhussain-PROJECTS-podcast-factory/memory/feedback_*.md` is the authoritative copy; this section is the durable backup.

- **Heartbeat re-arm is MANDATORY (Tier 0).** After any orchestrator `--resume`, `--retry-phase`, or restart — and on session start if any book is in-flight — re-arm a 270s ScheduleWakeup heartbeat. Never wait for user instruction. Per `feedback_loop_rearm_mandatory.md`.
- **Watchdog active liveness.** Every heartbeat tick MUST verify parent PID alive + subprocesses progressing (mtime/size growth + per-PID elapsed); kill early on hang/stall to avoid wasting LLM spend. Per `feedback_watchdog_active_liveness.md`.
- **Heartbeat card format.** Structured card per tick: book title, metrics table (progress/cost/phase/last-ledger-entry/systemic-loop/watchdog-fixes), Orchestrator + Watchdog status lines with PIDs, chapter list with ✅/🔄/⏳ icons, EST timestamps, top + bottom dividers. Per `feedback_heartbeat_format.md`.
- **Post-merge holistic audit.** Every merge into `develop` triggers a `podcast-auditor` agent regression sweep before the next merge/push. For multi-merge chains in one session, audit ONCE at end of chain. Per `feedback_post_merge_audit.md`. **Docs-sweep sub-rule (2026-05-25):** any merge touching `_rules.py` (new R-* constants) OR `orchestrate_book.py` (new state fields) MUST also touch `SKILL.md` + `framework.md` + `podcast-challenger.md` Category catalog as part of the same merge.
- **Autonomous recommendation execution.** When Asif accepts a recommended option, chain through follow-up recommendations to completion without re-asking AskUserQuestion. Stop only for genuine blockers, Tier-2 destructive actions, or end-of-chain final-state report. Per `feedback_autonomous_recommendation_execution.md`.
- **AskUserQuestion format.** Every AskUserQuestion lead with `(Recommended)` option A + brief reasoning in the question text; remaining options descend by value/scope so Asif can authorize the biggest high-value chunk first. Never enumerate as equals. Per `feedback_ask_user_question_format.md`.
- **Systemic-fixes-from-chapter-archetype.** When the first per-chapter challenger run surfaces P0s from templates/regex/data (not chapter content), HALT and fix at root before letting the loop burn cost on remaining chapters with the same findings. Detection signal: ≥3 challenger + ≥2 fixer passes on the same P0 IDs. Per `feedback_systemic_fixes_from_chapter_archetype.md`.
- **NotebookLM upload table format.** Whenever giving Asif instructions to begin NotebookLM generation, ALWAYS include a per-episode table with EP / Title / Format / NotebookLM Format setting / Length setting columns. Per `feedback_notebooklm_instructions_format.md`.
- **Next-block batch rule + holistic selection (LOCKED 2026-05-26).** When B/C/D are complementary follow-ups that compose without regression risk, Option A IS "Do all of the below in sequence — B then C then D" with one why-batching line. Before writing the Next block, score every candidate against four lenses: project health, architectural fit, extensibility/scalability, regression/brittleness risk — and REMOVE (not demote) any option that could destabilize what's already working. Per `feedback_response_format.md` + `feedback_recommendation_best_first.md`. Global spec at `~/.claude/response-template.md`.
- **Plan-dashboard snapshots stay live (Tier 0, LOCKED 2026-05-26).** Any edit to `_workspace/plan/architecture.md`, `_workspace/plan/refactor/plan.md`, `_workspace/plan/refactor/plan.yaml`, or `_workspace/plan/debt/pipeline-debt.md` MUST be followed — in the same response, before commit — by `cd plan-dashboard && npm run snapshot` to regenerate the three snapshot JSONs the SPA reads. Stale snapshots are a contract violation. A `PostToolUse` hook in `.claude/settings.json` matching Edit/Write/MultiEdit on those four paths runs the regen as a safety net, but Claude must NOT rely on it — invoke it explicitly. Per `feedback_plan_dashboard_snapshots_live.md`.

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
- Running `/steward <scope>` — the four-pass strategic coordinator that composes existing agents and emits prioritized findings cited to `reference/steward-source-corpus.md`. Read-only protocol. Spec at [project-steward.agent.md](.github/agents/project-steward.agent.md). Executing a specific steward recommendation inherits that recommendation's own tier; **editing the source corpus itself is Tier 2.**
- `git restore` of auto-generated artifacts under `content/drafts/<slug>/_system/` when the artifact is reproducible by re-running its generator script
- `security find-generic-password -s <name>` for existence checks (no `-w`)
- **Re-arming the `/loop` heartbeat monitor** after any orchestrator resume or retry-phase action — this is MANDATORY and automatic, never requires user instruction. Use `ScheduleWakeup` at 270s with the standard monitoring prompt (see [Heartbeat card format](~/.claude/projects/-Users-asifhussain-PROJECTS-podcast-factory/memory/feedback_heartbeat_format.md)). Do NOT wait for Asif to ask. If a session resumes and a book is in-flight (orchestrator alive OR `phase_status=running/failed`), re-arm immediately.

**Tier 1 — Do, then surface in the At-a-glance.**
- Commit to `develop`
- Push `develop` to `origin`
- `--retry-phase <phase>` on a book (recovery from stale `phase_status="running"` per the known orchestrator-resume bug)
- Phase advancement via `--resume <slug>` on an in-progress book
- Regenerating auto-generated state files (`chapter-set-report.md`, `challenger-report.md`, mangle-map, etc.)
- Opening a DRAFT PR from a feature branch to `develop`
- Orchestrator's automatic `book/<slug>` → `develop` merge after the `publish` phase completes successfully — this is in-pipeline and not a separate gate
- Running `validate_ship_ready.py <slug>` (read-only G1-G7 gate runner — never writes files)
- The `/loop` heartbeat re-arms automatically (Tier 0 above) — no separate Tier 1 action needed

**Tier 2 — Always ask. One-line ask + single-sentence Next.**
- First-time orchestrator launch on a new book: `python3 scripts/podcast/orchestrate_book.py <pdf>` (multi-hour LLM-spend gate). The orchestrator auto-spawns the watchdog on every subsequent `--resume`; no manual watchdog launch needed. The `/loop` heartbeat re-arms automatically (Tier 0) — no separate step required.
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
