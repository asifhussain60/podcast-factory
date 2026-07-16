# Podcast-Factory PDF Route Consolidation — Working Plan

## Status

Working branch: **`chore/pdf-route-consolidation-and-site-validation`**, cut from
`origin/develop` at `bc2b2cac` (fast-forwarded 2026-07-16, includes the new
Book Composer header/autosave work). `develop` itself is untouched — nothing
is committed yet on this branch, changes sit in the working tree pending
your review.

## Context

Asif asked for a holistic review of the podcast-factory pipeline: whether PDF
generation really has multiple routes, a recommendation to collapse to 2 main
routes (Podcast/NotebookLM, and PDF generation), and a dead-code scan. That
review is done (Findings 1-5 below, unchanged from the approved review). This
document now also tracks every pending follow-up as a phase, plus a new
requirement: full validation of the Podcast Factory Astro Site
(`plan-dashboard/`) bracketing the eventual v2 cutover, since recent
Studio/Book Composer work + the v2 knob system both live in that surface.

## Findings (unchanged from the approved review)

**Finding 1 — Podcast (NotebookLM) route:** already one clean pipeline via
`orchestrate_book.py` → `phases/*.py`. No consolidation needed.

**Finding 2 — PDF/book route: 4 code paths today.** At `phases/book_driver.py`'s
`0book-compose` step: (1) `book_pipeline_v2` flag (unified `compose_book_v2()`,
default OFF), (2) legacy translation edition, (3) legacy augmented companion,
(4) standalone `generate_translation_edition.py` (already admits v2
supersedes it), plus (5) `build_fiction_book_pdf.py` — a fifth, genuinely
separate, manual fiction-only script with zero orchestrator callers.

**Finding 3 — The unification is already built, tested, and held.**
`_workspace/plan/book-pipeline-cutover.md`: core work landed, acceptance
matrix green, highest-risk piece (fluency de-calque) validated on real
content. Held pending one full knob-matrix validation run + explicit approval.
**Recommendation stands: finish this held plan, don't redesign.**

**Finding 4 — Fiction path:** leave separate for now (one real caller book,
too early to generalize a third knob).

**Finding 5 — Dead code:** see Phase 1 (done) and Phase 2 (pending) below.

## Phase 1 — Dead-code cleanup, Category A — **DONE, on this branch**

Deleted (verified zero references via repo-wide grep before removal):
`scripts/podcast/_fix_chapter_commas.py`, `_fix_slide_deck_validation.py`,
`_run_slide_convergence_batch.py`; `branch_prefix()` + its dead tests in
`_branching.py`/`test_technical_path.py`; `plan-dashboard/src/pages/api/ai/summarize-section.ts`
(confirmed absent from the current route list, no caller); 4 duplicate
`podcast-auditor` agent-spec files. Corrected 5 stale doc mentions
(CLAUDE.md, AGENTS.md, framework.md, audit-prompt.md, polish-and-ai.md) that
referenced the removed code. All 42 tests in `test_technical_path.py` pass.
Not committed yet — pending your say-so.

**Skipped, flagged instead of silently patched:** the planned one-line
"fiction path" note in `_workspace/plan/architecture.md` — that document
turned out to describe a retired branch/folder model (`book/<slug>` naming,
`drafts/`→`published/` folders) and a phase-numbering scheme that doesn't
match the real orchestrator. See Phase 3.

## Phase 2 — Dead code confirmation — **DONE**

Asked Asif one question at a time; resolved and committed
(`bca2fef5`):
- WC8 cluster (`augment_book.py`, `reconcile_book.py`, `segment_book.py` +
  their support modules) — **flag, don't delete.** Real manual toolchain
  (each already self-documents as "WC8 holistic pipeline" with USAGE
  examples), not wired into either main route by design. One-line docstring
  note added to the 3 entry points.
- 3 one-off CLI utilities (`normalize_double_parens.py`,
  `sanitize_contract_yaml.py`, `split_pdf_asaas.py`) — **flag, don't
  delete.** Same reasoning. Noted.
- `plan-dashboard/src/lib/reader/format-for-copy.ts` — alias-aware check
  confirmed zero importers under any path (unlike the manual tools above,
  no plausible reason to be unwired). Asked, approved, **deleted.** Verified
  clean via `astro check` (0 errors) and `npm run smoke` (32/32).

## Phase 3 — `architecture.md` refresh — **DONE** (commit `cbe439d3`)

Chose the banner + targeted-correction approach over a full rewrite (the doc
spans domains beyond this review's scope). Added: (a) a top-of-doc stale
banner pointing at `CLAUDE.md`/`framework.md`/`book-pipeline-cutover.md` as
authoritative; (b) corrected the "Branch + Content Lifecycle" diagram + policy
text to the bucket-grouped / status-field model; (c) a callout ahead of the
Backbone phase diagram noting the real `_progress.py` PHASES sequence. Regenerated
the 3 plan-dashboard snapshot JSONs per the locked snapshot-sync rule. Verified
`astro check` 0 errors, `/architecture` route 200.

**Cross-cutting finding surfaced during Phase 3 (feeds Phase 4):** `architecture.md`
Decision Record **DR-013** states *"Retroactive enhancements for shipped books =
addendum-only. Never re-run the pipeline against KaR, M&D, Ayyuhal Walad, etc."*
"M&D" == `the-master-and-the-disciple`, one of Phase 4's two required fixture
books. See Phase 4.

## Phase 4 — v2 cutover validation run — **APPROVED (full matrix), NOT STARTED**

Asif chose "Full matrix as originally planned" on 2026-07-16 after being shown
the DR-013 conflict, the cross-branch blast radius, and the multi-day cost.
**Still requires resolving the DR-013 question before touching M&D** (see below)
— the approval was to run the full matrix, but it does not by itself override a
locked Decision Record; confirm with Asif whether the book/PDF branch is exempt
from DR-013's "never re-run the pipeline against M&D" rule, since Phase 4
requires re-running `0book-compose` against exactly that book.

**The run** (per `book-pipeline-cutover.md` §Validation gate): full knob-matrix
`{book_augmentation: none|source_only} × {book_voice: faithful|author_companion}`
= 4 cells/book × 2 books (`the-master-and-the-disciple`, `mukhtasar-ul-asar-2`)
= 8 cells, each through `book-challenger` (filter report for BK-P4 faithfulness)
+ `book-render-challenger` (RENDER-CLEAN).

**Feasibility findings (from the 2026-07-16 scoping agent — no hard blocker, but
key mechanics):**
- **`visual-layout.json` is automatable** — it's a plain JSON file (schema in
  `scripts/podcast/_visual_layout.py`, `normalize_placement` gives every field a
  safe default; only `visual_id` required). No browser drag-and-drop needed: a
  ~15-line script can read `book/visuals/index.json` and emit one
  `{visual_id, anchor: suggested_anchor}` placement per candidate, writing
  `book/visual-layout.json` directly (same schema the `PUT /api/studio/visual-layout`
  endpoint validates). **This helper does not exist yet — must be written.**
- **PDF render is a CLI call:** `python3 scripts/podcast/build_book_pdf.py <BOOK_DIR> --json`.
- **Challengers are subagents, not scripts** — invoke `book-challenger` as
  `challenge book <slug>` (runs ALL 11 probes; no way to scope to BK-P4 alone,
  filter the report after) and `book-render-challenger` as `<slug>`.
- **Fixture state:** neither book has `book_pipeline_v2`/`book_augmentation`/
  `book_voice` set; both already have real book artifacts on their OWN content
  branches. `the-master-and-the-disciple` is `phase: publish` (failed G5).
  `mukhtasar-ul-asar-2` has `deliverable_mode: translation_edition`,
  `phase: preflight`. Running the matrix means checking out those content
  branches and force-overwriting artifacts there — bigger blast radius than the
  maintenance branch. **Do the runs on the books' own branches, not this one.**
- **Credentials:** `claude` CLI authenticated (flat-rate, the compose/illustrate/
  voice/augment steps all use `claude -p` — $0 tracked spend). `az login` active,
  both API keys in Azure Key Vault `podcast-factory-vault`. **Gaps:** Python
  `google-genai` and `Pillow` not installed — `google-genai` only blocks the
  Composer's interactive "generate new image" (NOT the automated candidate path);
  `Pillow` absence degrades gracefully (watermark crop falls back to plain copy).
- **Cost/time:** `claude -p` steps are $0 in dollars but ~3h wall-clock each for
  `0book-compose`/`0book-illustrate` on a large book. 8 cells × ~3h ≈ multi-day
  continuous run. The cutover doc itself notes the environment killed the
  multi-hour recompose twice. **This needs a stable long-running session and
  probably a heartbeat/resume strategy — do NOT attempt in one unmonitored shot.**

### Phase 4 — execution log (2026-07-16, session 2)

**Environment prep (done):** `Pillow` installed into `.venv` (google-genai was
already present); `az login` active; `claude` auth OK (start-session ping).

**Mechanics locked in:**
- Knobs are per-book `_system/series-config.yaml` keys (`book_augmentation`,
  `book_voice`); the v2 flag comes from the `BOOK_PIPELINE_V2=1` env override,
  which `_pipeline_flags.py` documents as existing exactly for fixture-book
  validation (no config-flag commit needed).
- Cell entry point is `phases/book_driver._drive_book_branch` (design →
  compose(v2) → illustrate → slide-import → awaiting-layout halt). Each phase
  self-commits via `phase_git_commit` on the content branch.
- Runner: `_workspace/experiments/v2-matrix/run_cell.sh` (gitignored sandbox).
  Per cell: stamps knobs, deletes stage outputs (KEEPS `book/_chunks` compose
  checkpoint + `book-toc.json` — design/compose idempotency is in-pipeline),
  runs the driver, then auto-layout + `build_book_pdf.py --json`, snapshots
  artifacts to `_workspace/experiments/v2-matrix/results/<cell>/`, commits the
  cell on the content branch. `resume` mode re-runs slide-import → layout →
  render without redoing compose (for after a deck halt).
- `--auto-layout` helper: `_workspace/experiments/v2-matrix/auto_layout.py` —
  emits `book/visual-layout.json` from `book/visuals/index.json`, alternating
  standalone-center / wrap-left / wrap-right so the render exercises both flow
  modes book-render-challenger validates.
- Branches: `mukhtasar-ul-asar-2` had NO content branch (its history sits on
  `develop`; `Islamic/mukhtasar` is stale/merged) — created
  `Islamic/mukhtasar-ul-asar-2` off `develop`@`bc2b2cac` per branch policy, in a
  worktree at `/Users/ahmac/Code/podcast-factory-worktrees/mukhtasar-ul-asar-2`
  so the maintenance branch stays checked out in the main tree. M&D will get the
  same worktree treatment on `Islamic/the-master-and-the-disciple` once DR-013
  is resolved.
- **New blocker found (mua2):** `slide-decks/book-framing.md` exists but
  `book-deck.pdf` was never dropped → slide-import will `AuthoringHalt` every
  mua2 cell BEFORE candidate emission. Compose/illustrate (the expensive part)
  still runs. Options: Asif generates the deck in NotebookLM (best fidelity), or
  authorizes `slide-decks/book.SKIP` (diagram-candidates only; standing rule
  says that bypass needs his explicit say-so). Asked alongside DR-013.

**Results matrix (verdicts recorded as cells finish):**

| Cell | Book | augmentation | voice | compose | render | book-challenger BK-P4 | render-challenger |
|---|---|---|---|---|---|---|---|
| c1 | mukhtasar-ul-asar-2 | none | faithful | ON HOLD (Asif: "focus only on M&D for now"; killed at 15 chunks, checkpointed) | — | — | — |
| c2 | mukhtasar-ul-asar-2 | source_only | faithful | ON HOLD (same) | — | — | — |
| c3 | mukhtasar-ul-asar-2 | none | author_companion | ON HOLD (same) | — | — | — |
| c4 | mukhtasar-ul-asar-2 | source_only | author_companion | ON HOLD (same) | — | — | — |
| c5 | the-master-and-the-disciple | none | faithful | RENDER-DONE 13:18Z (114pp A4, 15 visuals, fluency 0 reverts, 2 self-healed chunk retries) | ✅ | challengers running | challengers running |
| c6 | the-master-and-the-disciple | source_only | faithful | DEFERRED to MacBook Air (Asif: stop after c5) | — | — | — |
| c7 | the-master-and-the-disciple | none | author_companion | DEFERRED to MacBook Air | — | — | — |
| c8 | the-master-and-the-disciple | source_only | author_companion | DEFERRED to MacBook Air | — | — | — |

**Stop-after-c5 order (Asif, 2026-07-16):** c5 runs to completion incl. both
challengers, everything pushes, then the loop stops. c6–c8 + the Phase 5/6b/7
tail continue on the MacBook Air via the TRACKED continuation package at
`_workspace/plan/v2-matrix/` (CONTINUATION.md + portable run_cell.sh +
auto_layout.py, pushed on the maintenance branch). M&D's chunk cache gets a
force-add convenience commit at finalize so the laptop skips base recompose.

**Blockers resolved (2026-07-16, Asif via AskUserQuestion):**
- **DR-013 (amended by Asif, same day):** re-running the PDF/`0book-*` phases
  against shipped books is AUTHORIZED ("you can rerun the pdf for books"), but
  DR-013's wording must NOT be amended with an exemption ("Don't exempt") — the
  a5479fff clarification was reverted in a follow-up commit; DR-013 stands
  verbatim, and this plan file is the record of the one-time authorization.
  M&D cells unblocked; the
  `Islamic/the-master-and-the-disciple` branch was fast-forwarded to
  `develop`@`bc2b2cac` (it was a fully-merged ancestor, 418 commits behind — no
  v2 code at its old tip) and runs in its own worktree at
  `/Users/ahmac/Code/podcast-factory-worktrees/the-master-and-the-disciple`.
- **mua2 deck (superseded, Asif 2026-07-16):** "use the existing slide-deck
  generated file" — verified NO deck PDF exists anywhere (repo, worktrees,
  Downloads/Desktop/Documents; the 2.9MB Downloads PDF is md5-identical to the
  reading edition, and mua1 is in the same never-exported state). The existing
  generated files are `book-deck-source.txt` + `book-framing.md`, so per his
  direction the cells proceed WITHOUT a NotebookLM deck: `slide-decks/book.SKIP`
  created in the mua2 worktree (the standing-rule bypass, explicitly authorized).
  mua2 cells now flow straight to awaiting-layout with diagram candidates only
  (zero visuals for the aug=none cells — diagrams are forbidden there); the
  slide-candidate path is validated by the M&D cells, whose real deck exists.
  If a real deck PDF ever lands at the main-tree path, the heartbeat still picks
  it up and slide-import can be re-run per cell in `resume` mode.

Both books run in PARALLEL (one worktree each, 3 claude workers per compose).

Cell logs: `_workspace/experiments/v2-matrix/logs/<cell>.log` (+ `.pid`).

## Phase 5 — v2 cutover execution — **Tier 2, gated on Phase 4 passing**

Flip `book_pipeline_v2` default to True; delete `generate_translation_edition.py`
+ the `_inject_figures` path in `_book_illustrate.py` + the `inject_slides`
write in `_slide_import.py` + the legacy `0book-compose` dispatch branches in
`book_driver.py`; remove flag scaffolding; docs-sweep (`SKILL.md` +
`framework.md` + `podcast-challenger.md` Category catalog) if `_rules.py` or
orchestrator state fields changed; regenerate plan-dashboard snapshots; sync
TS↔Python mirrors; run `repo-surgeon --scope podcast`.

## Phase 6 — Podcast Factory Astro Site validation (NEW — brackets Phase 5)

The Studio/Book Composer surface (`plan-dashboard/src/pages/studio/[slug]/*`,
`composer_visual.py`, `visual-layout.json`) is exactly what curates
`book_pipeline_v2`'s "awaiting_layout" visual candidates, and just received
new header/autosave work on `develop`. This surface needs validating both
now (baseline) and again after Phase 5 (regression check).

**6a — Baseline, run now:** `cd plan-dashboard && npm run smoke` (deterministic,
zero model spend — boots the dev server, hits every page route incl. all
`studio/[slug]/*` sub-pages, fails on console errors/5xx/failed requests).

**Result (2026-07-16, this branch, fixture slug `ayyuhal-walad`): 30/32 clean.**
Two pre-existing failures, confirmed unrelated to this branch's changes
(grepped — neither failing route touches anything deleted/modified in Phase 1):
- `/studio/new` → `/api/intake/form-options` returns 500
- `/studio/ayyuhal-walad/edit` → `/api/studio/section-depth` AND
  `/api/studio/action-items` both return 500

These are pre-existing bugs on `develop` at `bc2b2cac`, not a Phase-1
regression. Not fixed here — out of scope for a dead-code cleanup; flagged
for Asif to decide whether to fix now or fold into Phase 6b.

**6b — Full pass, run after Phase 5 lands:**
1. `npm run smoke` again (must still be clean minus the 2 known pre-existing
   failures above, unless Asif asked for those fixed first).
2. `site-health-sentinel` agent — visual QA sweep at desktop (~1440px) and
   mobile (~390px), light/dark, across every route found in `src/pages/`:
   `/`, `/overview`, `/architecture`, `/infrastructure`, `/intelligence`,
   `/pipeline-paths`, `/system-map`, `/db-schema`, `/corpus`, `/quality`,
   `/security`, `/plan`, `/about`, `/annotation-ops`, `/library` (+`[slug]`),
   `/studio` (+`new`, `[slug]` index/compose/book/live/preview/arabic-review/style/view/edit),
   `/pronunciation` (+`[slug]`), `/pre-upload` (+`[slug]`), `/wisdom`.
   Extra focus on Studio compose/book/preview states given the v2 visual-curation
   tie-in — the "awaiting_layout" candidate list, drag/resize/align, Generate
   PDF button, zoom.
3. `html-view-challenger` on any view touched by Phase 5's changes.
4. `npm run lint:views` + `npm run check` (astro check) — both must be clean.

**Action:** 6a is done (see result above). 6b runs only after Phase 5, and
only with Asif's go-ahead given it invokes agents (not free, though far
short of Phase 4's multi-hour LLM run).

### 6a follow-up — both pre-existing bugs fixed (2026-07-16, this branch)

**Bug 1 — wrong Python interpreter.** `/api/intake/form-options` (and 4
sibling routes: `pronunciation.ts`, `pronunciation/build-bundle.ts`,
`studio/visual-op.ts`, `studio/generate-book-pdf.ts`, plus both spawn sites
in `lib/intake-cli.ts`) all hardcoded `spawn('/usr/bin/python3', …)` — macOS's
Command Line Tools Python 3.9, which does not have the pipeline's
dependencies (PyYAML etc. — `requirements.txt`) installed. `bootstrap.md`'s
documented setup is a project `.venv` with those deps installed. Fix: added
`getPythonBin()` to `content-paths.ts` (prefers `<repo>/.venv/bin/python3`,
env-overridable via `PODCAST_FACTORY_PYTHON`, falls back to
`/usr/bin/python3` if no venv exists) and pointed all 5 call sites at it —
one shared resolver instead of 5 copies of a wrong hardcoded path.

**Bug 2 — missing DB migrations.** `/api/studio/section-depth` and
`/api/studio/action-items` hit `SqliteError: no such table: section_depths` /
`action_items` — the local `content/knowledge-base/knowledge.db` (gitignored,
machine-local) didn't even have a `schema_migrations` tracking table, meaning
`_db.run_migrations()` had never been run against it. Fix: ran it
(`.venv/bin/python3 -c "from _db import run_migrations; run_migrations()"`)
— applied all 29 pending migrations, idempotent and additive, matches the
documented rebuild path (`corpus_sync.py rebuild()` already calls this). Pure
local data-state fix, nothing to commit (the db file is gitignored).

**Verification:** `npm run smoke` now 32/32 clean (was 30/32). `npm run check`
(astro check) 0 errors. `npm run lint:views` clean. Pipeline's
`test_technical_path.py` still 42/42 green.

## Phase 7 — Merge back to `develop`

Once Phases 1-6 are resolved to Asif's satisfaction: ask explicitly before
merging `chore/pdf-route-consolidation-and-site-validation` back into
`develop` (not pre-authorized by any existing Tier — this is a maintenance
branch, not a content `<Bucket>/<slug>` branch, so the automatic
publish-triggered merge rule doesn't cover it).

## Current state (2026-07-16, end of session)

**Branch `chore/pdf-route-consolidation-and-site-validation`, 4 commits ahead of
`develop`@`bc2b2cac`, clean tree:**
- `6852f344` — Phase 1 dead-code cleanup
- `dd11289e` — site bug fixes (Python interpreter resolver + DB migrations)
- `bca2fef5` — Phase 2 resolution (flag manual tools, delete `format-for-copy.ts`)
- `cbe439d3` — Phase 3 architecture.md staleness banner + corrections + snapshots

**Done:** Phases 1, 2, 3 + both site bugs. **Approved but not started:** Phase 4
(full matrix — but resolve DR-013 first). **Not started:** Phase 5 (cutover
execution, gated on 4), Phase 6b (post-cutover site QA), Phase 7 (merge to
develop).

**Next action for a fresh session:** see the continuation prompt in
`/Users/ahmac/.claude/plans/CONTINUE-pdf-route-consolidation.md`.
