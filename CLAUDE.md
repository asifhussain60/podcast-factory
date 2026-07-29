# podcast-factory repo — session orientation

You're in the **`podcast-factory`** repo (renamed from `Journal` on
2026-05-22 as part of the repo split (see `docs/runbooks/` for migration history). This file is auto-loaded by Claude Code on
every session in this directory; treat it as your standing brief.

## What this repo contains

- **Podcast pipeline** (`scripts/podcast/`, `content/<Bucket>/<slug>/` for all per-book state, `skills-staging/podcast/`) — multi-phase Claude+Azure pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series. Phases 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring → trainer → ship.
- **Content container** (`content/`) — type-first layout (2026-06-04): every item lives at `content/<Bucket>/<slug>/` where `<Bucket>` is one of `Islamic/`, `Technical/`, `Fiction/`, `Guides/`. **`draft` vs `published` is now a status field** (`status` in `_system/orchestrator-state.json`, mirrored to `publication.status` in `meta.yml`), **not a folder** — the prior `content/drafts/` and `content/published/books/` split was retired. A book is created with `status=draft` and flipped to `status=published` in place by `scripts/podcast/publish_to_library.py` (via the `podcast-publisher` agent); nothing is copied between trees. The bucket a slug belongs to is derived from its content profile via `bucket_for_profile()` in [scripts/podcast/_rules.py](scripts/podcast/_rules.py); the path resolver is [scripts/podcast/_paths.py](scripts/podcast/_paths.py) (TS mirror [plan-dashboard/src/lib/content-paths.ts](plan-dashboard/src/lib/content-paths.ts)), which scans buckets first and falls back to the legacy `drafts/`/`published/` layout so a partial migration never breaks readers. The **Podcast Factory Astro Site** (directory `plan-dashboard/` — see the naming rule below) reads content through that resolver and filters by `status`. (`content/published/` still holds cross-book `archetypes/` + `_meta/` only — no per-book folders.)

The memoir engine (Asif IS Babu), the static `journal` site, the Anthropic API proxy (`server/`), and the Cloudflare deploy scaffold all moved to (or were retired from) the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of 2026-05-22. See §"Disconnected from journal" below.

## Machine-agnostic — single-machine model

Post-2026-05-23: this app is **machine-agnostic**. Most work is done by Anthropic + Azure remotely, so there's no cost difference between hosts. Production releases go `develop` → `main` (requires Asif's explicit approval; never auto-promoted).

The earlier cross-machine coordination model (operator files at `_workspace/plan/operators/`, `~/.machine-id` detection, `book-queue.md` mutex, coordination-protocol §15) was retired 2026-05-23. If you encounter references to operator files or "the peer machine" anywhere, treat them as stale documentation pending cleanup.

## Branch policy — one branch per piece of content, grouped by content bucket (locked 2026-06-07, supersedes the 2026-06-04 bare-slug model)

Every new piece of content is processed on its own branch off `develop`. The branch is created at intake time and merged back to `develop` ONLY after the publish step completes. This isolates in-flight work from `develop`, preserves a clean per-content ledger, and lets multiple books be in flight without cross-contamination.

**Branch naming** is `<Bucket>/<full-slug>` — the branch is grouped under its content **bucket** (the same top-level category folder the content lives in: `Islamic`, `Technical`, `Fiction`, `Guides`). The bucket is derived from the content's `content_profile`, NOT its legacy `category` tag (a `books`-category item can be Islamic OR Fiction):

| Bucket | Branch | Example |
|---|---|---|
| Islamic | `Islamic/<slug>` | `Islamic/kitab-al-riyad`, `Islamic/ayyuhal-walad` |
| Fiction | `Fiction/<slug>` | `Fiction/journey-to-the-west-vol-1` |
| Technical | `Technical/<slug>` | `Technical/claude-code-training` |
| Guides | `Guides/<slug>` | `Guides/healthequity` |

Source of truth: [scripts/podcast/_branching.py](scripts/podcast/_branching.py) — every script that computes a branch name imports `branch_name(category, slug, *, profile=None, bucket=None)` from there, which returns `<Bucket>/<slug>`. The bucket is resolved by `_paths.resolve_bucket` — the SAME resolver the content-folder layout uses — so a branch's bucket can never drift from the folder bucket. Prefer passing `profile=` (the book's `content_profile`); `category` alone falls back to a coarse map defaulting to Islamic. **History:** type prefixes (`book/`, `lecture/`…) were retired 2026-06-04 → bare slug 2026-06-04 → bucket grouping 2026-06-07 (this policy). `branch_prefix()` was removed 2026-07-16 — it had been unreferenced except by its own tests since the 2026-06-04 retirement. Never hardcode a branch name anywhere.

**Lifecycle**:
1. `intake_book.py` creates the `<Bucket>/<slug>` branch from `develop`, routes the book to `content/<Bucket>/<slug>/` via `content_dir()`, and stamps `status=draft`.
2. Pipeline phases (0a → 0f → per-chapter → authoring → publish) all run on that branch.
3. `publish_to_library.py` (via the `podcast-publisher` agent) flips `status` → `published` in place (in `orchestrator-state.json` + `meta.yml`) after gates G1–G5+G7 pass. Nothing is copied; G6 (target wipe-safety) is obsolete and dropped from the flow.
4. The orchestrator merges `<Bucket>/<slug>` → `develop` with `--no-ff` after publish completes.
5. `develop` → `main` for production releases requires Asif's explicit approval (unchanged).

## Run this on session start

```bash
bash scripts/start-session.sh
```

The script does: `git fetch --all --prune`, switches to `develop` if needed, fast-forwards from `origin/develop`, surfaces a one-liner summary of books in flight, and lists the most common next-action commands. Exit codes:
- `0` = ready
- `1` = pre-flight failed (working tree dirty, or not in a git repo)

## Read these once, or when conventions feel stale

- **`~/.claude/response-template.md`** — the canonical response format, loaded into every session by the global CLAUDE.md. H2 main title, H3 sections that carry the gist, blockquote callouts, tables for tabular data only, and an alphabetized `### Next:` block with the recommended option first. **No custom section labels** like "Deviation from plan", "Verification", "Coord doc", "What changed". No `**TL;DR:**` opener, no `## Project Status` block. (Two repo-local copies were linked here until 2026-07-20; neither had existed for some time, and the global file superseded both — the 4-part template they described was itself retired on 2026-05-26.)
- **[docs/setup/azure-stack.md](docs/setup/azure-stack.md)** — Azure resources, keychain layout, recreate-from-scratch guide.
- **[docs/setup/bootstrap.md](docs/setup/bootstrap.md)** — blank-machine bootstrap for this repo.
- **[framework.md](framework.md)** — pipeline framework spec.

## Authoritative truth

The orchestrator's state file is the source of truth for any book's pipeline state:

```bash
# Pre-F33-second / pre-F37 minimal probe (the glob matches whichever bucket the slug lives in):
jq '{phase, phase_status, last_completed_phase, last_error, status}' \
    content/*/<slug>/_system/orchestrator-state.json

# Post-2026-05-25 wave full probe (recommended — surfaces graceful-degrade + timing + cost):
jq '{
    phase, phase_status, last_completed_phase, last_error, status,
    completed_slugs: .phases."per-chapter".completed_slugs,
    failed_slugs:    .phases."per-chapter".failed_slugs,
    chapter_timings: .phases."per-chapter".chapter_timings,
    audit_outcomes:  .phases."0g".audit_outcomes
}' content/*/<slug>/_system/orchestrator-state.json
```

`phase=finalize, phase_status=halted` means "ready for publish review" — run [scripts/podcast/cross_book_dashboard.py](scripts/podcast/cross_book_dashboard.py) for the fleet view, then `python3 scripts/podcast/publish_to_library.py <slug>` (Tier 2 — always ask) when satisfied.

## Standing operator rules (mirror of AI memory)

These are recoverable on disk so a fresh Claude session without memory state can pick them up. The AI memory at `~/.claude/projects/-Users-asifhussain-PROJECTS-podcast-factory/memory/feedback_*.md` is the authoritative copy; this section is the durable backup.

- **Heartbeat re-arm is MANDATORY (Tier 0).** After any orchestrator `--resume`, `--retry-phase`, or restart — and on session start if any book is in-flight — re-arm a 270s ScheduleWakeup heartbeat. Never wait for user instruction. Per `feedback_loop_rearm_mandatory.md`.
- **Watchdog active liveness.** Every heartbeat tick MUST verify parent PID alive + subprocesses progressing (mtime/size growth + per-PID elapsed); kill early on hang/stall to avoid wasting LLM spend. Per `feedback_watchdog_active_liveness.md`.
- **Heartbeat card format (APPROVED 2026-07-19, supersedes the hand-assembled template).** Every heartbeat status update renders the framed fixed-width card from [scripts/podcast/book_status_card.py](scripts/podcast/book_status_card.py) verbatim, inside a fenced block so the frame aligns — never re-rendered as a markdown table and never hand-assembled. Book title in Proper Case from `meta.yml`, plain-English step names (ids only in `--json`), EST 12-hour timestamps, real money only. Fix the generator, not the tick. **The heartbeat ENDS when the work is done**: driver gone with the deliverable present, `phase==done`, or a terminal failure → post a final card and delete the schedule. Per `feedback_heartbeat_format.md`.
- **Post-merge holistic audit.** Every merge into `develop` triggers a `repo-surgeon --scope podcast` regression sweep before the next merge/push (formerly invoked as `podcast-auditor` — deprecated 2026-06-02; Pass 2b in `skills-staging/repo-surgeon/SKILL.md` is the canonical probe catalog). For multi-merge chains in one session, audit ONCE at end of chain. Per `feedback_post_merge_audit.md`. **Docs-sweep sub-rule (2026-05-25):** any merge touching `_rules.py` (new R-* constants) OR `orchestrate_book.py` (new state fields) MUST also touch `SKILL.md` + `framework.md` + `podcast-challenger.md` Category catalog as part of the same merge.
- **Autonomous recommendation execution.** When Asif accepts a recommended option, chain through follow-up recommendations to completion without re-asking AskUserQuestion. Stop only for genuine blockers, Tier-2 destructive actions, or end-of-chain final-state report. Per `feedback_autonomous_recommendation_execution.md`.
- **AskUserQuestion format.** Lead with a CONCRETE "Picture this…" plain-language scenario BEFORE the options — walk through a specific worked example of what happens, in words a non-technical reader follows on first read (LOCKED 2026-06-03; an abstract phrasing that draws "I don't understand the question" is a failure of this rule — re-ask with a worked example, not a reworded abstraction). Then `(Recommended)` option A + brief reasoning in the question text; remaining options descend by value/scope so Asif can authorize the biggest high-value chunk first; each option describes what he'll SEE/EXPERIENCE, not an implementation label. Never enumerate as equals. Per `feedback_ask_user_question_format.md`.
- **Systemic-fixes-from-chapter-archetype.** When the first per-chapter challenger run surfaces P0s from templates/regex/data (not chapter content), HALT and fix at root before letting the loop burn cost on remaining chapters with the same findings. Detection signal: ≥3 challenger + ≥2 fixer passes on the same P0 IDs. Per `feedback_systemic_fixes_from_chapter_archetype.md`.
- **NotebookLM upload table format (LOCKED 2026-06-07, supersedes the EP/Title/Format/NLM/Length columns).** Whenever the pipeline (or you) are ready to upload chapters/episodes to NotebookLM, ALWAYS present a markdown table with EXACTLY these four columns: **`| Chapters | Episodes | Deep dive or debate | Length |`** — Chapters = "N. <chapter title>", Episodes = "EP## — <episode title>", Deep dive or debate = the NotebookLM conversation style, Length = **default `Long`**. **The Chapters and Episodes cells are ALWAYS clickable markdown links** — Chapters → the chapter SOURCE file (the upload), Episodes → the episode FRAMING file (the Customize paste). The format is centralized in [scripts/podcast/_notebooklm_table.py](scripts/podcast/_notebooklm_table.py) (`render_upload_table`, `DEFAULT_LENGTH="Long"`); every emitter (`chapter_driver` finalize halt, `assemble_bundle`, probe bundle) renders through it so the format cannot drift. Change the format THERE, not per-caller. Per `feedback_notebooklm_instructions_format.md`.
- **Next-block batch rule + holistic selection (LOCKED 2026-05-26).** When B/C/D are complementary follow-ups that compose without regression risk, Option A IS "Do all of the below in sequence — B then C then D" with one why-batching line. Before writing the Next block, score every candidate against four lenses: project health, architectural fit, extensibility/scalability, regression/brittleness risk — and REMOVE (not demote) any option that could destabilize what's already working. Per `feedback_response_format.md` + `feedback_recommendation_best_first.md`. Global spec at `~/.claude/response-template.md`.
- **Thorough over superficial (LOCKED 2026-05-27).** When presenting options or making recommendations, always recommend the most thorough and architecturally complete approach as option A. Reducing scope to lower regression risk is never a justification for a partial or symptom-level fix when a root-level fix is available. If a more comprehensive approach solves the root problem and a narrower approach only patches a symptom, the comprehensive approach is the recommendation — always. Per user direction 2026-05-27.
- **Plan-tracking discipline, NOT an execution gate (LOCKED 2026-05-31, supersedes prior "Plan-first execution gate").** When you ship a new step (a wave/slice marker, a new pipeline phase, a new feature surface), update `plan.yaml` + `plan.md` in the same commit and regenerate snapshots. For small bug fixes, refactors, and verification work that fits inside an existing plan entry, just do the work and note it in the commit + session log — no plan entry needed first. The plan tracks what shipped, not what's about to ship. Per user direction 2026-05-31.
- **Plan-dashboard snapshots stay live (Tier 0, LOCKED 2026-05-26).** Any edit to `_workspace/plan/architecture.md`, `_workspace/plan/refactor/plan.md`, `_workspace/plan/refactor/plan.yaml`, or `_workspace/plan/debt/pipeline-debt.md` MUST be followed — in the same response, before commit — by running the snapshot regenerator to rebuild the three snapshot JSONs the SPA reads. Stale snapshots are a contract violation. **Primary command:** `cd plan-dashboard && npm run snapshot` (falls back to `python3 plan-dashboard/scripts/regenerate-snapshots.py` automatically on Node failure; the Python path needs only PyYAML). **Machine-policy correction (2026-07-18):** this is Asif's personal machine — there is NO org policy blocking the npm registry; `npm install` is allowed whenever needed. Per `feedback_plan_dashboard_snapshots_live.md`.
- **Canonical app name (LOCKED 2026-05-29).** The repo's single Astro web app is the **Podcast Factory Astro Site**. Its directory is `plan-dashboard/` — keep that token verbatim in all paths, imports, and commands (`cd plan-dashboard && npm run dev` for the dev server; `python3 plan-dashboard/scripts/regenerate-snapshots.py` for snapshots). In prose/chat/docs, always call it "the Podcast Factory Astro Site", never "plan-dashboard app" and never "podcast-reader". **There is NO separate `podcast-reader` app** — the reader is a section inside this site (`plan-dashboard/src/components/reader/`, `plan-dashboard/src/lib/reader/`). Per `project_podcast_reader.md` (memory: `astro-site-naming`).
- **Cortex HTML-view standard — implicit, never bypass (LOCKED 2026-05-29).** ANY work that builds or edits an HTML view, page, or diagram, or otherwise touches the Podcast Factory Astro Site, MUST follow the **Cortex HTML View Quality Standard** without being told. Load the `html-view-quality` skill (`skills-staging/html-view-quality/SKILL.md`), apply its rules (external CSS/JS only, no inline styling/scripts; Theme-Adapter Pattern B onto existing `--c-*` tokens — never change the colour theme; vertical-only uncapped diagrams; Mermaid build→inline SVG), and gate the result through the `html-view-challenger` agent before calling it done. A `UserPromptSubmit` hook auto-injects this reminder on relevant prompts (belt-and-suspenders, not a substitute for following it). Conflict rule: blend both standards; content + SVG lean Cortex; delivery mechanics follow the styling DoD. Per-view redesigns are discussed with Asif one page at a time before changing anything. **Hardened 2026-05-29 (WC7):** the canonical standard now lives at `docs/standards/html-view-quality.md` (full text) with a one-screen MUST card at `docs/standards/html-view-quality-digest.md` (the in-context reference — read the full standard only for a rule's exact wording); rule text lives in ONE place (skill + challenger cite by `REQ-NNN`, never re-copy it). Enforcement is now **deterministic, not advisory**: `npm run lint:views` (config `plan-dashboard/html-view-lint.config.json`) runs the §11 mechanical checks and is wired into the pre-commit hook + `prebuild` — a MUST violation on a view page cannot be committed. A `SessionStart` hook (`.claude/hooks/site-work-status.sh`) injects current site-work state from `_workspace/plan/site-work-status.md` into every new conversation (update that file at the end of any site-work session). Per `feedback_cortex_html_view_standard.md`.

- **Arabic provenance resolves against the CANONICAL MUSHAF first (LOCKED 2026-07-20).** `content/knowledge-base/mirror.db` is tracked in git (~30 MB) and carries all 6,236 ayat as vowelled Uthmani text in `fts_quran`. [scripts/podcast/_mushaf.py](scripts/podcast/_mushaf.py) `is_quranic()` is the discriminator; the Arabic audit's resolution ladder is now **canonical-mushaf → ocr → knowledge-base → honorific → unverified**, canonical first because a scan can carry an OCR error and the mushaf cannot. This is what makes fabricated-vowelling detection possible at all: canonical Quran is LEGITIMATELY vowelled whatever the scan does, and without a way to recognise it every review list came back dominated by verses. `_narrative.ocr_vowelling_findings` uses it to list NON-Quranic runs vowelled beyond the scan — **advisory only, surfaced as `vowelling_review` in `_system/book-arabic-audit.json`, never a gate**, because a wrong revert costs real authored text. Degrades silently when the mirror is absent (everything reads non-Quranic, i.e. more conservative, never falsely passing).

- **The Book Composer is the SINGULAR path for chapter modifications destined for the PDF (LOCKED 2026-07-20).** Any change to a chapter's prose that should appear in `book/book.pdf` goes through the Book Composer at `/studio/<slug>/compose` — not by hand-editing `book/book.md`, not through the `chapters/*.txt` routes (`denoise`, `replace`, `save-stage` — those serve the NotebookLM/podcast lane and never reach the PDF), and not by patching the compose cache under `book/_chunks/`. The Composer's save writes BOTH `book/book.md` (what it previews) and the durable sidecar `_system/composer-edits.json`, which [scripts/podcast/_book_edits.py](scripts/podcast/_book_edits.py) replays as the FINAL text step of `compose_book_v2` — so a Composer edit now survives a re-compose, which is the only thing that makes "singular" true. **Stronger since 2026-07-21: a chapter carrying a Composer edit is NOT REGENERATED at all.** The base compose, the fluency pass, the augment pass and the re-voice pass all consult `_book_edits.edited_chapter_keys` and pass that chapter through untouched, so no model is asked to rewrite prose the replay would only discard — the failure that cost a full nine-chapter re-translation to keep one chapter. `--force` re-composes regardless and warns that it will overwrite human chapters; the replay then restores them and reports each as a conflict. Replay is idempotent and anchored by chapter heading, and an edit whose heading no longer exists is reported as **orphaned**, never guessed into place. Conflict detection reads ONE number produced by ONE computation: the pipeline stamps each chapter's composed fingerprint into `_system/composer-base.json` at replay time and the Composer quotes that value back as the edit's `base_fingerprint` — it does not hash anything itself. (It used to, against the LIVE `book.md`, which carries the introduction and the comprehension bridges while the replay compares the composed body from before either is injected, so CONFLICT fired permanently and every one reported was noise.) The remaining unpinned mirror in the Composer path was `anchor_key`/`anchorKey`, and it is pinned by shared fixtures at `plan-dashboard/scripts/lib/anchor-key.fixtures.json`; a divergence there silently orphans every saved edit. **As of 2026-07-29 all four TS↔Python mirrors are fixture-pinned** — see clause (3) below for the others.

- **Narrative frame is a SOURCE property, enforced on every prose route (LOCKED 2026-07-20).** WHO NARRATES a book is declared per book as `narrative_frame` in `_system/series-config.yaml` (`transmitted_report` | `external_narrator` | `first_person_author` | `participant_narrator` — registry `NARRATIVE_FRAMES` + resolver `narrative_frame_for` in [scripts/podcast/_rules.py](scripts/podcast/_rules.py), read via [scripts/podcast/_pipeline_flags.py](scripts/podcast/_pipeline_flags.py)). It is deliberately INDEPENDENT of `book_voice` and `deliverable_mode`: a text that opens as an anonymous transmitted report stays third-person whether it ships as a translation edition or an augmented companion. Never infer the frame from the route or from the prose in front of you — read how the SOURCE opens. Every prose-rewriting phase (`0book-compose`, `0book-voice`, `0book-fluency`) BOTH instructs and enforces it through the shared [scripts/podcast/_narrative.py](scripts/podcast/_narrative.py) — grammatical person, speech-tag integrity (a tag may not be added/removed/re-pointed), Arabic-script retention (transliteration goes BESIDE the script, never in place of it), enumeration survival — and `book-challenger` closes with these as **Pass 3, the final gate**: no chapter is approved until BK-N1–BK-N7 clear. Change a rule in `_narrative.py`, never per-route. Per `feedback_narrative_frame_enforcement.md`. **Docs-sweep sub-rule applies:** any change here also touches `framework.md` + `skills-staging/podcast/SKILL.md` + the `book-challenger` spec — and the spec is edited in ONE place, `infra/claude-agents/book-challenger.md`, which is canonical. The other three copies (`.github/agents/*.agent.md`, the gitignored per-machine `.claude/agents/*.md`, and `.codex/agents/*.toml`) are GENERATED: run `scripts/podcast/sync-agent-wrappers.sh` and stage what it writes; `--check` fails on drift. Never hand-edit a generated copy — that is how `.codex/agents/book-challenger.toml` fell a whole generation behind while claiming to be a mirror (fixed 2026-07-20).

- **Arabic script is ALWAYS vowelled (LOCKED 2026-07-29, reverses the 2026-07-21 propose-and-review contract).** Asif does not read Arabic: an unvowelled run is not "unverified" to him, it is unreadable, so any rule whose effect is to keep tashkeel off the page makes the edition worse for the person it is printed for. [scripts/podcast/vowel_book.py](scripts/podcast/vowel_book.py) runs at compose time (step `5a-vowelling`, after the inline-Arabic overlay and before the audits) and marks every bare non-Qur'anic Arabic run; the Composer's **Diacritics** button does the same for one selection on demand. A Qur'anic run is never model-vowelled: `_mushaf.is_quranic` recognises it and `_mushaf.mushaf_vocalisation` sets it from the canonical mushaf in `content/knowledge-base/mirror.db`, so the marks are the verse's own. That text is UTHMANI — the letters change too (`رَجِعُونَ` for `راجعون`), which is the ONE place in this repo where an Uthmani substitution is right rather than a defect, and it finally agrees with the edition already setting mushaf-resolved runs in the KFGQPC Uthmanic face. A verse that does not align word for word is left exactly as the book prints it. **What was NOT relaxed** is the marks-only rule: a vowelling must come back with a byte-identical consonantal skeleton or it is refused and recorded in `_system/book-vowelling.json`. The gate is [scripts/podcast/_vowelling.py](scripts/podcast/_vowelling.py) `rejection_reason`, a FOURTH fixture-pinned mirror pair with `plan-dashboard/scripts/lib/vowelling.mjs` (`vowelling.fixtures.json`). Deleted with the old rule: `_narrative.supplied_diacritics_findings`, `_narrative.ocr_vowelling_findings`, the audit's `vowelling_review` list, and `R-NO-SUPPLIED-DIACRITICS` (now `R-VOWELLING-MARKS-ONLY`); `book-challenger` BK-N5 is re-scoped from "supplied diacritics" to "vowelling integrity". Per `feedback_always_vowel_arabic.md`.

- **Runtime + visual-QA gate — the `site-health-sentinel` agent (LOCKED 2026-07-14).** `html-view-challenger` + `npm run lint:views` validate the site STATICALLY (source greps, Cortex REQ rules) — they never boot a browser, so a console error, a 5xx SSR route, a broken client island, a clipped editor, a broken mobile layout, or an off-theme colour ships past them. The **runtime peer** closes that gap and is a MANDATORY second gate before ANY change under `plan-dashboard/` is called done (exactly as `book-render-challenger` is the rendered-PDF peer of `book-challenger`). Two layers: (1) **deterministic, zero model spend** — `cd plan-dashboard && npm run smoke` (`scripts/site-health-smoke.mjs`) boots the dev server, visits every page route in headless chromium, and hard-fails on any console error / uncaught exception / failed request / 5xx; a `Stop` hook (`.claude/hooks/ui-reviewer-stop.sh`) runs it automatically at turn-end whenever `plan-dashboard/` changed and a dev server is already up on :4322. (2) **visual judgment** — invoke the `site-health-sentinel` agent to screenshot each surface at desktop (~1440px) + mobile (~390px) across its states (Read/Edit, compose place/wrap/resize, empty/loading, light/dark, focus) via `scripts/site-health-shots.mjs`, judge the pixels for real defects, fix the smallest in-pattern source change (reuse `--c-*` tokens + the view's existing CSS layer, never inline styles, never touch `content/`), re-run `lint:views` + `astro check` after any fix, and converge (≤5 iterations) then delete its throwaway `plan-dashboard/.visual-qa/` screenshots. Playwright + chromium are already installed (no `npm install`). Runs as a PAIR with `html-view-challenger`: static conformance AND runtime health.

- **LLM-agnostic operating model (LOCKED 2026-05-31, supersedes the 2026-05-30 two-agent lane lock).** This repo is **driver-agnostic**. Any LLM (Claude Code, GitHub Copilot, Claude Cowork, future tools) operates under the same rules — there is **no directory ownership boundary**. Whichever agent is at the keyboard can edit any file in the repo. The anti-regression contract is quality-gate-based, not directory-based: (1) after editing `architecture.md`, `refactor/plan.{md,yaml}`, or `debt/pipeline-debt.md` — run `cd plan-dashboard && npm run snapshot` in the same response, stage the JSONs alongside the edit; (2) before any commit touching an Astro page or view component — run `cd plan-dashboard && npm run lint:views` (errors block, warnings advisory); (3) keep TS↔Python mirror files in sync in the same commit when either side changes — all four pairs are now FIXTURE-PINNED, so a one-sided edit fails a test rather than drifting silently: `content-paths.ts`↔`_paths.py` (`content-paths.fixtures.json`), `peq-scores.ts`↔`_quality.py`+`_rules.py` (`peq-scores.fixtures.json`; the interest weight and patterns are owned by `_rules.py`, so the fixture anchors there, not to `_quality.py`), `anchor-key.mjs`↔`_book_edits.anchor_key` (`anchor-key.fixtures.json`), and `vowelling.mjs`↔`_vowelling.py` (`vowelling.fixtures.json`, added 2026-07-29 — a divergence there lets the Composer button and the compose-time pass admit different Arabic into `book.md`); (4) `git pull --rebase` before starting and before pushing; (5) the `_system/` JSON schema (in `editorial.ts` + `stage-review.ts`) can be evolved by either side, but both sides update atomically in the same commit with a one-line schema-bump note in the commit message. Async memory across sessions and agents lives in `_workspace/plan/copilot-handoff.md` — append a dated session log entry before ending any session. The `.github/copilot-instructions.md` file is the mirror of these rules for Copilot. Per user direction 2026-05-31.

## Disconnected from `journal` (2026-05-22 split)

- **Memoir + site moved to the sibling [journal](https://github.com/asifhussain60/journal) repo**: `content/babu-memoir/`, `site/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/` — all moved, none remain here.
- **Anthropic API proxy `server/` RETIRED**: the journal app no longer needs it; not migrated to journal either.
- **Cloudflare deploy scaffold RETIRED**: `wrangler.toml`, `site-worker.js`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md` — all deleted; not migrated. **NOTE (corrected 2026-06-19):** `infra/cloudflare/` was NOT deleted — it holds deployment reference docs for **Salty Lamps**, a SEPARATE personal project that is **not part of the podcast-factory pipeline** (companion: `infra/supabase/`). Both are non-pipeline reference only; leave them in place and never wire them into pipeline code.
- **Duplicated general-utility items** (`clean-commit`, `repo-surgeon` skills + CORTEX/refine-prompt/reconcile/operating-contract agents + `docs/reference/`): these stay here as INDEPENDENT copies; the journal repo has its own independent copies that evolve separately. (**Corrected 2026-07-27:** `content/_shared/arabic/` was listed here as staying, but it was RETIRED in the 2026-05-23 restructure and does not exist. Its rules are inlined in [scripts/podcast/_rules.py](scripts/podcast/_rules.py) and the framing prompt; the live pronunciation authority is the per-book `_system/glossary.yml`. The `_boundary_check.py` whitelist entry for `06-abjad-numerals.md` is retained deliberately — it is a defensive rule, test-pinned, and permits a write that can no longer happen.) (`cowork-brief`, `tell-me`, `usage-auditor` were removed 2026-06-02 — they were ADLC/journal-repo tools with no use in podcast-factory.)

## What to do for a typical user request

1. Run `bash scripts/start-session.sh`. Read its output.
2. If the user is asking about pipeline work, the listed next-action commands are your starting point.
3. If the user is asking about a specific book's state, read its `content/<Bucket>/<slug>/_system/orchestrator-state.json` via the `jq` command above (use the `content/*/<slug>/…` glob if you don't know the bucket).
4. Respond in the 4-part response template. No custom section labels.

## Video layer standing rules (LOCKED 2026-06-05)

**Category-driven video style** — read from `_system/series-config.yaml` (`video_style` field).
Never default to scenic for Islamic scholarly content; never invent a category.

| content_profile | video_style | What gets generated |
|---|---|---|
| `islamic_scholarly` | `teaching_hybrid` | Pillow text slides (title/verse/hadith/numbered_list/concept) over Imagen3 darkened backgrounds |
| fiction / narrative | `scenic` | Imagen3 atmospheric images only (original v1 approach) |
| technical | `technical` | Graphviz/Mermaid diagrams (deferred — falls back to scenic until built) |

**Teaching-hybrid pipeline** (LOCKED):
1. `generate_video_layer.py` reads `video_style` from `series-config.yaml`.
2. Gemini Flash generates a slide manifest (`video-prompts.json`) with `"mode": "teaching_hybrid"`, `"backgrounds"` (3–5 Imagen3 prompts), and `"slides"` (25–40 teaching slide defs).
3. Imagen3 generates background images (atmospheric, NOT full-detail scenic) into `video-images/`.
4. `render_slides.py` overlays Pillow text (title/verse/numbered_list/concept) on darkened backgrounds.
5. `stitch_video.py` reads the manifest's `slides` array and stitches with equal-duration timing.

**Stitching timing rule** (LOCKED): `stitch_video.py` always uses equal-duration splits (`actual_duration / n_slides`). Never scale unequal storyboard estimates — that caused the "last image for 8 minutes" bug. Keyword-based sync is deferred until VTT-format transcripts are available.

**Regeneration order** (LOCKED — follow this sequence exactly):
1. `rm -rf content/*/<slug>/episodes/EP*/video-images/` (delete old images)
2. `rm content/*/<slug>/episodes/EP*/video-prompts.json` (delete old manifests)
3. `python3 scripts/podcast/generate_video_layer.py <slug> --confirm` (generate new)
4. Regenerate audio in NotebookLM (upload updated framing, download new `.m4a`)
5. Drop new `.m4a` files into `content/*/<slug>/m4a/`
6. `python3 scripts/podcast/stitch_video.py <slug> --force` (stitch new images + audio)

**Pronunciation bug — permanent guard** (LOCKED 2026-06-05): `build_episode_txt.py` rejects any framing using `Pronounce "X" as "Y"` format (R-PRONUNCIATION-DOUBLE). The correct format is `- term: phonetic` with an explicit "say ONCE" anti-doubling instruction. See `_validators_framing.py::assert_framing_pronunciation_imperative`.

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
- `git restore` of auto-generated artifacts under `content/<Bucket>/<slug>/_system/` when the artifact is reproducible by re-running its generator script
- `security find-generic-password -s <name>` for existence checks (no `-w`)
- **Re-arming the `/loop` heartbeat monitor** after any orchestrator resume or retry-phase action — this is MANDATORY and automatic, never requires user instruction. Use `ScheduleWakeup` at 270s with the standard monitoring prompt (see [Heartbeat card format](~/.claude/projects/-Users-asifhussain-PROJECTS-podcast-factory/memory/feedback_heartbeat_format.md)). Do NOT wait for Asif to ask. If a session resumes and a book is in-flight (orchestrator alive OR `phase_status=running/failed`), re-arm immediately.

**Tier 1 — Do, then surface in the At-a-glance.**
- Commit to `develop`
- Push `develop` to `origin`
- `--retry-phase <phase>` on a book (recovery from stale `phase_status="running"` per the known orchestrator-resume bug)
- Phase advancement via `--resume <slug>` on an in-progress book
- Regenerating auto-generated state files (`chapter-set-report.md`, `challenger-report.md`, mangle-map, etc.)
- Opening a DRAFT PR from a feature branch to `develop`
- Orchestrator's automatic `<Bucket>/<slug>` → `develop` merge after the `publish` phase completes successfully — this is in-pipeline and not a separate gate
- Running `validate_ship_ready.py <slug>` (read-only G1-G7 gate runner — never writes files)
- The `/loop` heartbeat re-arms automatically (Tier 0 above) — no separate Tier 1 action needed

**Tier 2 — Always ask. One-line ask + single-sentence Next.**
- First-time orchestrator launch on a new book: `python3 scripts/podcast/orchestrate_book.py <pdf>` (multi-hour LLM-spend gate). The orchestrator auto-spawns the watchdog on every subsequent `--resume`; no manual watchdog launch needed. The `/loop` heartbeat re-arms automatically (Tier 0) — no separate step required.
- `publish_to_library.py <slug>` — flipping the finalized book's `status` from `draft` to `published` in place (in `orchestrator-state.json` + `meta.yml`); this is what makes it audience-facing in the Astro site, no files are copied. The orchestrator's new `finalize` phase halts BEFORE publish so Asif can review the clean version in the Podcast Factory Astro Site (the reader section) and run post-pipeline analyses (A/B transcription, etc.); resuming the orchestrator after that human review is what authorizes publish.
- Opening a `develop` → `main` PR, marking it ready, or merging it (production release gate — never auto-promoted)
- Force-push (any branch)
- Deleting branches
- `--no-verify`, `--amend`, `git reset --hard`, `git clean -f`, `rm` of tracked files
- Recreating retired surfaces (`server/`, `wrangler.toml`, `site-worker.js`, `docs/cloudflare/`)
- Reaching into the sibling `journal` repo's paths or scripts

Tier overrides: if the user says "just do it" for something in Tier 2, that one-shot authorizes that one action — it doesn't promote the action into Tier 1 for future sessions. If the user says "always" or "from now on" for a Tier 2 action, that's a request to edit this tier list and should be confirmed before the edit.

## Do NOT

- Run any orchestrator command (`scripts/podcast/orchestrate_book.py`) on a new PDF without explicit user authorization (multi-hour LLM-spend gate)
- Force-push to `main` or `develop`
- Bypass `git status` cleanliness before merges
- Re-create `server/`, `wrangler.toml`, `site-worker.js`, `docs/cloudflare/` without explicit user authorization — these were retired 2026-05-22 for a reason. (`infra/cloudflare/` is NOT a retired surface — it is non-pipeline Salty Lamps reference; see §"Disconnected from journal".)
- Reach into the sibling `journal` repo's paths or scripts — the repos are fully disconnected.
