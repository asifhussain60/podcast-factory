# podcast-factory repo — session orientation

You're in the **`podcast-factory`** repo (renamed from `Journal` on
2026-05-22 as part of the repo split (see `docs/runbooks/` for migration history). This file is auto-loaded by Claude Code on
every session in this directory; treat it as your standing brief.

## What this repo contains

- **Podcast pipeline** (`scripts/podcast/`, `content/drafts/<slug>/` for per-book in-progress state, `content/published/books/<slug>/` for shipped catalog, `skills-staging/podcast/`) — multi-phase Claude+Azure pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series. Phases 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring → trainer → ship.
- **Content container** (`content/`) — single tree holding both `content/drafts/` (workshop, where the pipeline reads + writes) and `content/published/` (audience-facing catalog, populated exclusively by `scripts/podcast/publish_to_library.py` invoked via the `podcast-publisher` agent). The 2026-05-23 restructure flattened the prior multi-worktree container, consolidated all in-flight books into `content/drafts/`, and renamed the old `library/` to `content/published/`. The **Podcast Factory Astro Site** (directory `plan-dashboard/` — see the naming rule below) reads from `content/drafts/`; the future audience-facing catalog surface will read from `content/published/`.

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
| `asbaaq` | `asbaaq/` | `asbaaq/short-course-01` |
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
- **[docs/setup/azure-stack.md](docs/setup/azure-stack.md)** — Azure resources, keychain layout, recreate-from-scratch guide.
- **[docs/setup/bootstrap.md](docs/setup/bootstrap.md)** — blank-machine bootstrap for this repo.
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
- **Thorough over superficial (LOCKED 2026-05-27).** When presenting options or making recommendations, always recommend the most thorough and architecturally complete approach as option A. Reducing scope to lower regression risk is never a justification for a partial or symptom-level fix when a root-level fix is available. If a more comprehensive approach solves the root problem and a narrower approach only patches a symptom, the comprehensive approach is the recommendation — always. Per user direction 2026-05-27.
- **Plan-tracking discipline, NOT an execution gate (LOCKED 2026-05-31, supersedes prior "Plan-first execution gate").** When you ship a new step (a wave/slice marker, a new pipeline phase, a new feature surface), update `plan.yaml` + `plan.md` in the same commit and regenerate snapshots. For small bug fixes, refactors, and verification work that fits inside an existing plan entry, just do the work and note it in the commit + session log — no plan entry needed first. The plan tracks what shipped, not what's about to ship. Per user direction 2026-05-31.
- **Plan-dashboard snapshots stay live (Tier 0, LOCKED 2026-05-26).** Any edit to `_workspace/plan/architecture.md`, `_workspace/plan/refactor/plan.md`, `_workspace/plan/refactor/plan.yaml`, or `_workspace/plan/debt/pipeline-debt.md` MUST be followed — in the same response, before commit — by `cd plan-dashboard && npm run snapshot` to regenerate the three snapshot JSONs the SPA reads. Stale snapshots are a contract violation. A `PostToolUse` hook in `.claude/settings.json` matching Edit/Write/MultiEdit on those four paths runs the regen as a safety net, but Claude must NOT rely on it — invoke it explicitly. Per `feedback_plan_dashboard_snapshots_live.md`.
- **Canonical app name (LOCKED 2026-05-29).** The repo's single Astro web app is the **Podcast Factory Astro Site**. Its directory is `plan-dashboard/` — keep that token verbatim in all paths, imports, and commands (`cd plan-dashboard && npm run dev` / `npm run snapshot`). In prose/chat/docs, always call it "the Podcast Factory Astro Site", never "plan-dashboard app" and never "podcast-reader". **There is NO separate `podcast-reader` app** — the reader is a section inside this site (`plan-dashboard/src/components/reader/`, `plan-dashboard/src/lib/reader/`). Per `project_podcast_reader.md` (memory: `astro-site-naming`).
- **Cortex HTML-view standard — implicit, never bypass (LOCKED 2026-05-29).** ANY work that builds or edits an HTML view, page, or diagram, or otherwise touches the Podcast Factory Astro Site, MUST follow the **Cortex HTML View Quality Standard** without being told. Load the `html-view-quality` skill (`skills-staging/html-view-quality/SKILL.md`), apply its rules (external CSS/JS only, no inline styling/scripts; Theme-Adapter Pattern B onto existing `--c-*` tokens — never change the colour theme; vertical-only uncapped diagrams; Mermaid build→inline SVG), and gate the result through the `html-view-challenger` agent before calling it done. A `UserPromptSubmit` hook auto-injects this reminder on relevant prompts (belt-and-suspenders, not a substitute for following it). Conflict rule: blend both standards; content + SVG lean Cortex; delivery mechanics follow the styling DoD. Per-view redesigns are discussed with Asif one page at a time before changing anything. **Hardened 2026-05-29 (WC7):** the canonical standard now lives at `docs/standards/html-view-quality.md` (full text) with a one-screen MUST card at `docs/standards/html-view-quality-digest.md` (the in-context reference — read the full standard only for a rule's exact wording); rule text lives in ONE place (skill + challenger cite by `REQ-NNN`, never re-copy it). Enforcement is now **deterministic, not advisory**: `npm run lint:views` (config `plan-dashboard/html-view-lint.config.json`) runs the §11 mechanical checks and is wired into the pre-commit hook + `prebuild` — a MUST violation on a view page cannot be committed. A `SessionStart` hook (`.claude/hooks/site-work-status.sh`) injects current site-work state from `_workspace/plan/site-work-status.md` into every new conversation (update that file at the end of any site-work session). Per `feedback_cortex_html_view_standard.md`.

- **LLM-agnostic operating model (LOCKED 2026-05-31, supersedes the 2026-05-30 two-agent lane lock).** This repo is **driver-agnostic**. Any LLM (Claude Code, GitHub Copilot, Claude Cowork, future tools) operates under the same rules — there is **no directory ownership boundary**. Whichever agent is at the keyboard can edit any file in the repo. The anti-regression contract is quality-gate-based, not directory-based: (1) after editing `architecture.md`, `refactor/plan.{md,yaml}`, or `debt/pipeline-debt.md` — run `cd plan-dashboard && npm run snapshot` in the same response, stage the JSONs alongside the edit; (2) before any commit touching an Astro page or view component — run `cd plan-dashboard && npm run lint:views` (errors block, warnings advisory); (3) keep TS↔Python mirror files (`content-paths.ts`↔`_paths.py`, `peq-scores.ts`↔`_quality.py`+`challenger_scoring.py`) in sync in the same commit when either side changes; (4) `git pull --rebase` before starting and before pushing; (5) the `_system/` JSON schema (in `editorial.ts` + `stage-review.ts`) can be evolved by either side, but both sides update atomically in the same commit with a one-line schema-bump note in the commit message. Async memory across sessions and agents lives in `_workspace/plan/copilot-handoff.md` — append a dated session log entry before ending any session. The `.github/copilot-instructions.md` file is the mirror of these rules for Copilot. Per user direction 2026-05-31.

## Disconnected from `journal` (2026-05-22 split)

- **Memoir + site moved to the sibling [journal](https://github.com/asifhussain60/journal) repo**: `content/babu-memoir/`, `site/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` — all moved, none remain here.
- **Anthropic API proxy `server/` RETIRED**: the journal app no longer needs it; not migrated to journal either.
- **Cloudflare deploy scaffold RETIRED**: `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md` — all deleted; not migrated.
- **Duplicated general-utility items** (`clean-commit`, `cowork-brief`, `repo-surgeon`, `tell-me`, `usage-auditor` skills + CORTEX/refine-prompt/reconcile/operating-contract agents + `content/_shared/arabic/` + `docs/reference/`): these stay here as INDEPENDENT copies; the journal repo has its own independent copies that evolve separately.

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
- Running `/steward <scope>` — the four-pass strategic coordinator that composes existing agents and emits prioritized findings cited to `docs/reference/steward-source-corpus.md`. Read-only protocol. Spec at [project-steward.agent.md](.github/agents/project-steward.agent.md). Executing a specific steward recommendation inherits that recommendation's own tier; **editing the source corpus itself is Tier 2.**
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
- `publish_to_library.py <slug>` — copying the finalized book from `content/drafts/` to `content/published/books/` (the audience-facing catalog). The orchestrator's new `finalize` phase halts BEFORE publish so Asif can review the clean version in the Podcast Factory Astro Site (the reader section) and run post-pipeline analyses (A/B transcription, etc.); resuming the orchestrator after that human review is what authorizes publish.
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
