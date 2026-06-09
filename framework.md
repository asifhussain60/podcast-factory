# Podcast Factory Ecosystem Framework

**Last updated:** 2026-06-09

This document governs the **`podcast-factory`** repo: the multi-phase podcast pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series, the Azure stack that powers OCR / translation / speech, and the agents/skills that support podcast authoring. Memoir + site work moved to the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of the 2026-05-22 split. The Anthropic API proxy (`server/`) and the Cloudflare deploy scaffold were retired the same day — see §"Retired" below. The previous cross-machine coordination model (operator files, machine-id detection, per-machine book branches) was retired 2026-05-23 — see §"Single-machine model" below.

## 2026-06-09 Wave M — multi-volume works + profile routing + autonomy rails

Holistic-hardening wave. Four landed pieces (intake UI is a separate follow-on):

- **Multi-volume "works" (Phase 1).** A multi-volume work = ONE branch + a parent
  folder `content/<Bucket>/<work_slug>/` holding a `work.yml` manifest (ordered
  volumes + shared-library pointers) and nested `vol-NN/` dirs, each a normal book
  dir. The single layout seam `_paths.py` was EXTENDED (not forked): `find_content`/
  `iter_content` descend a `work.yml`-marked parent and yield each volume under the
  COMPOSITE slug `<work_slug>-vol-NN` (e.g. `asaas-vol-02`), discovered by marker +
  `vol-*` glob (no yaml dep). `slug_of(path)` gives the collision-free identity;
  `work_rollup_status` rolls a work up to `published` only when ALL volumes are.
  Manifest CONTENTS are read by the thin `_work_manifest.py` (intake / pause-driver /
  dashboard only). `_branching.branch_for_work` maps any volume/work slug to the one
  work branch. A flat book ending in `-vol-N` (e.g. `journey-to-the-west-vol-1`) is
  NEVER mistaken for a volume — descent requires a parent manifest. Single books stay
  flat with NO manifest, byte-identical. Intake: `intake_book.py <pdf> --work <slug>
  --volume N` (ONE PDF per volume); single-book `intake_book.py <pdf> <slug>` unchanged.

- **Profile-driven phase routing (Phase 2).** `_rules.phase_capabilities(profile)` is
  the SINGLE accessor for every phase-skip decision (0a OCR / 0c phonetics / 0e
  enrichment), over `CONTENT_TYPE_REGISTRY`. `initial_driver` reads
  `caps.skip_phonetics` / `caps.skip_enrichment` from the book's `content_profile`
  instead of the legacy `category` tag — so a `books`-category item that is actually
  technical now correctly skips. A compat shim keeps pre-`content_profile` consumer
  books (`sites`/`explainers`) on the skip path.

- **Per-volume autopilot + safety rails (Phase 3).** `orchestrate_work.py` is a
  work-level SEQUENCER (NOT a 2nd supervisor) — it drives volumes in order, hands the
  active volume to the existing `supervise_run.py ensure`, and PAUSES between volumes
  (Q4: "autopilot per volume, pause between volumes"); `--advance` starts exactly one
  next volume, never auto-launched. `converge_chapter` gained mid-loop cost ceilings
  (F35: per-chapter cap → FAILED+degrade; per-book `book_cost_cap_usd` → systemic
  COST-CEILING halt so the supervisor won't relaunch), a 2-consecutive-fixer-failure
  early halt, episode-rebuild surfacing, and an intra-iteration heartbeat. F32 framing
  cache: a restart with an unchanged chapter skips LLM re-authoring via a `.framing-sig`
  sidecar.

- **De-patch + F38 close-out (Phase 4).** Duplicated `_run`/`_err`/`_info` extracted to
  `_subprocess.py`. **F38 / DR-015 pool choice (documented):** unattended bulk phases
  (0b–0e chunked authoring via `_chunking.make_sdk_invoke_fn`, and the tighten pre-pass
  via `_tighten_helpers.spawn_claude`) invoke the model through the **Anthropic SDK on
  the METERED API pool**, NOT the interactive `claude -p` Max pool. This is DR-015's
  intent: unattended code that fires >10 calls/book must stay on the isolated metered
  pool (so spend is cost-covered and never diverts the interactive Max token), and the
  mid-loop cost ceiling covers exactly this spend. The stable instructions block is
  prompt-cached. A grep gate (`test_no_claude_p_in_unattended.py`) pins that no
  `claude -p` shellout reappears.

## 2026-06-03 Wave L — content-level gating + etymology + augmentation challenger

Category-gated augmentation for Islamic scholarly books, Quranic etymology weaving,
and a new challenger category. Non-Islamic books are unaffected (opt-in by `content_level`).

- **Content-level gate (L-1/L-2)** — migration `025_atoms_add_content_level.sql` adds
  `content_level` to atoms; Wave M migration `026_atoms_update_content_level_ladder.sql`
  expands the CHECK to the 6-level Kashkole ladder (general → advanced → taveel → mamsool
  → mabda_maad → haqaiq; `universal` outside the ladder, always eligible).
  [`_rules.py`](scripts/podcast/_rules.py) `allowed_content_levels()` drives
  cumulative-downward selection in [`augmenter.py`](scripts/podcast/intelligence/augmenter.py)
  `_fetch_doctrine_atoms` + mirrored in [`augment_book.py`](scripts/podcast/augment_book.py).
  Only doctrine is gated; Quran/Hadith/Term/Etymology are universal.
- **Atom categorization (L-3)** — [`knowledge/categorize_atoms.py`](scripts/podcast/knowledge/categorize_atoms.py):
  tag heuristic + Gemini Flash classified 555 doctrine atoms against the 6-level ladder
  (taveel 206, haqaiq 195, advanced 118, general 36; 73 below-threshold left NULL for
  review). Old 4-level names (esoteric/realities/shariah/history) remapped by migration 026.
- **Etymology weaving (L-4)** — `_fetch_matching_etymology` + `_build_etymology_block`
  weave a SPOKEN root-insight (≤3/chapter, never spelling Arabic letters);
  [`knowledge/fill_etymology_phonetics.py`](scripts/podcast/knowledge/fill_etymology_phonetics.py)
  bakes house-style phonetics into the 35 etymology atoms.
- **Anti-repetition (L-5)** — `episode-augment-ledger.json` excludes atoms used by other
  episodes so none repeats across chapters of a book.
- **Category W (L-6)** — [`_augmentation.py`](scripts/podcast/_augmentation.py) W1–W6:
  genuine-gap (P1), natural (P1), etymology discipline (P1), content-level integrity (P0),
  no-fabrication (P0), no-cross-chapter-repeat (P1). `CHALLENGER_VERSION` bumped 2.3 → 2.4.

## 2026-05-30 Wave 8 (WC8) — what changed

Studio re-platform, intelligence scoring, and holistic pipeline design:

- **K6 — 5-axis PEQ scoring** — [`_quality.py`](scripts/podcast/_quality.py) adds a fifth axis: Interest (weight 0.15). Weights rebalanced: Fidelity 30%, Voice 20%, Structure 18%, Enrichment 17%, Interest 15%. `_interest_score()` is deterministic (no API). `CHALLENGER_VERSION` bumped 2.2 → 2.3.
- **Category V (Interest checks)** — [`podcast-challenger.md`](infra/claude-agents/podcast-challenger.md) adds V1–V5: curiosity hook, challenge-defeat arc, modern relevance, no-strawman, rhetorical cadence. All P1/P2; feeds the Interest PEQ axis.
- **SN-7 terminus-technicus guard** — [`gemini_refine.py`](scripts/podcast/gemini_refine.py) injects `R_TERMINUS_PRESERVE` protect-list from `glossary.yml` into both denoise and normalize prompts. Retro-fix run on all 5 Ayyuhal chapters.
- **Host roles guardrail** — `HOST_ROLE_CONTRACT` dict (3 presets: teacher/student, teacher/questioner, scholar/debater) + `HOST_ROLE_CONTRACT_DEFAULT` in [`_rules.py`](scripts/podcast/_rules.py). 7th editorial card `host_roles` in the Studio cockpit.
- **Stage gate + runner** — [`_stage_gate.py`](scripts/podcast/_stage_gate.py) (review reader/writer) + [`stage_runner.py`](scripts/podcast/stage_runner.py) (CLI: check gate → run next WC8 stage producer). `--status` prints a per-chapter ✅/🔄/⬜ table.
- **Podcast bundle + slides** — [`assemble_bundle.py`](scripts/podcast/assemble_bundle.py) validates chapters/framings/slides, runs 5-axis PEQ inline, emits the mandatory NotebookLM upload table. [`generate_slide_decks.py`](scripts/podcast/generate_slide_decks.py) authors two-file slide pairs via Gemini 2.5 Flash (thinking disabled, maxOutputTokens=8000, trailing-whitespace strip). All 5 Ayyuhal slide decks produced.
- **Studio re-platform** — `/studio` page with `EditorialCards.tsx` (7 cards, @dnd-kit sortable drag-reorder on list cards, cmdk corpus search on Key Focus). `/intake` page (`NewContentForm.tsx`, `EditorialDefaults.tsx`, `api/intake/create.ts`). `save-stage.ts` API writes edits back to `_stages/<ch>/<stage>.md` with `.md.bak` backup.
- **Holistic pipeline gap identified** — WC8 `_stages/` normalized content (4,295w total) is NOT ready for podcast output. Arabic spine was never reconciled with English translations. New scripts planned: `full_book_denoise.py`, `reconcile_book.py`, `segment_book.py` (output to `chapters-wc8/`, ~4,500w per episode). Total new cost: ~$0.30.

## 2026-05-25 cleanup wave — what changed

A single-day cleanup arc closed ~28 pipeline-debt F-items, shipped the scholarly-conversation rubric v2.2, retired unused scaffolds (02/03/04), consolidated branches to one-per-active-book, and landed foundational layers for the multi-day F31/F32/F34 refactors. Operator-visible additions:

- **Phase 0g dual-auditor** ([orchestrate_book.py:phase_0g_audit_bundles](scripts/podcast/orchestrate_book.py)) runs `audit_bundle.py` + `audit_bundle_gemini.py` in parallel against every per-chapter NotebookLM bundle. Reports at `BOOK_DIR/audits/<EP-slug>.audit.{claude,gemini}.md`.
- **Scholarly-rubric v2.2** — [_rules.py:CHALLENGER_VERSION](scripts/podcast/_rules.py) bumped 2.1 → 2.2. Five new R-* rule families inlined into [_workspace/prompts/gemini-bundle-auditor.md §4](_workspace/prompts/gemini-bundle-auditor.md). Six matched fixtures at [_learning/fixtures/](content/podcast/.skill/_learning/fixtures/).
- **Per-chapter loop hardening** in [orchestrate_book.py:_drive_per_chapter_and_after](scripts/podcast/orchestrate_book.py): F33-second graceful-degrade (`failed_slugs` set; continue on failed chapter); F35-second `per_chapter_cost_cap_usd` series-plan flag (default $5); F37 `chapter_timings` per slug; F12 `_resolve_episode_id()` reads `contract.episode_number`.
- **Convergence robustness** — F11 preserves prior SHIP verdicts when later-iteration challenger times out ([_convergence.py](scripts/podcast/_convergence.py)).
- **Framing word-cap guard** — F1 compression re-author before build gate ([_authoring.py:author_framing](scripts/podcast/_authoring.py)).
- **Parallel windows** — F34-second [_chunking.py:run_windowed](scripts/podcast/_chunking.py) `max_workers` param; Phase 0b/0c default 3 (`PHASE_0B_MAX_WORKERS` / `PHASE_0C_MAX_WORKERS` env). ~3× wall-clock, cost-neutral.
- **Concurrency-safe ledgers** — fcntl LOCK_EX on findings.jsonl ([_rules.py:emit_finding](scripts/podcast/_rules.py)) + cost-ledger.jsonl ([_cost_ledger.py:append_cost_row](scripts/podcast/_cost_ledger.py)).
- **Azure cost tracking** — F36 `append_azure_{docintel,translator,speech}_cost` wired at ingest_source.py, translate_bundle.py, ocr_image_pages.py, transcribe_episode.py.
- **Cross-book dashboard** — [scripts/podcast/cross_book_dashboard.py](scripts/podcast/cross_book_dashboard.py) fleet-level phase/status/cost/timing table. `--since 7d --json --out` supported.
- **Rule-firing telemetry** — `learn_aggregate.py --by-check-id --since <window>` top-50 ranked histogram. Forward-looking `bypassed_gate` field on emit_finding.
- **Scaffold retirement** — F30 bundle shape now: chapter source + `00-framing.md` + `99-show-notes.md`. 02/03/04 stubs no longer emitted.
- **Tradition-pack registry** — F31 `_doctrinal.py:tradition_pack_dir / load_doctrinal_pack`; build gate skips with `T-NO-PACK` info when no pack exists for the book's `source_tradition`.
- **Episode-format enum** — F32 2 → 7 values; `EPISODE_FORMAT_FULLY_WIRED = (deep_dive, debate)` distinguishes tested from new entries.
- **Editorial-frontmatter exclusion + thesis_relevance** — F4 + F23 Phase 0d author prompt EXCLUDES editor's intros / translator's prefaces from the episode array; each contract requires `thesis_relevance` field.

For the line-by-line F-item map see [_workspace/plan/pipeline-debt.md](_workspace/plan/pipeline-debt.md).

---

## Podcast path vs PDF path — two deliverables per book

Every book produces **two** deliverables on the same branch, in the same `content/<Bucket>/<slug>/` folder:

- **Podcast path — the podcast.** The final-reviewed, enriched per-chapter text in the **original author's voice** (`chapters/chNN-<slug>.txt`) is the SOLE NotebookLM source, one chapter → one episode. Gated by `podcast-challenger` (audio) + `slide-deck-challenger` (decks). [build_episode_txt.py](scripts/podcast/build_episode_txt.py) always selects the author-voice chapter — never `chapters/literary/` (wiring fixed 2026-06-04; regression-guarded by `scripts/podcast/tests/test_episode_source_wiring.py`).
- **PDF path — the companion book.** Phases `0book-design → 0book-compose → 0book-render` (gated by `series.enable_book_branch`, NON-blocking on the podcast ship, run before the finalize halt so both deliverables are reviewed together) re-segment the source into a book-craft chapter structure, revoice it into modern author-first-person prose with Arabic scripture (script + English beneath) and plain transliteration ([scripts/podcast/_translit.py](scripts/podcast/_translit.py) ↔ [plan-dashboard/src/lib/translit.ts](plan-dashboard/src/lib/translit.ts)), and render `book/book.pdf` (Playwright) + the in-site reader view (`/studio/<slug>/book`). Gated by `book-challenger`. The revoice — formerly the retired per-chapter `0literary` step — lives here and NEVER feeds NotebookLM.

Phases live in [scripts/podcast/_progress.py](scripts/podcast/_progress.py) `PHASES`; the book driver is [scripts/podcast/phases/book_driver.py](scripts/podcast/phases/book_driver.py).

---

## Content tree

Type-first layout (2026-06-04): every item lives at `content/<Bucket>/<slug>/`. `draft`/`published`/`archived` is a `status` field on `_system/orchestrator-state.json` (mirrored to `publication.status` in `meta.yml`), NOT a folder. Bucket is derived from the content profile via `bucket_for_profile()` in [scripts/podcast/_rules.py](scripts/podcast/_rules.py); the resolver is [scripts/podcast/_paths.py](scripts/podcast/_paths.py) (TS mirror [plan-dashboard/src/lib/content-paths.ts](plan-dashboard/src/lib/content-paths.ts)), which scans buckets first and falls back to the legacy `drafts/`/`published/` layout so a partial migration never breaks readers.

```
podcast-factory/
├── content/                                        ← CONTENT CONTAINER
│   ├── Islamic/                                     ← BUCKET (scholarly Islamic texts/lectures)
│   │   └── <slug>/                                  ← per-book state (any status)
│   │       ├── _system/
│   │       │   ├── orchestrator-state.json           ← carries `status: draft|published|archived`
│   │       │   ├── challenger-report.md
│   │       │   ├── series-plan.md
│   │       │   └── …
│   │       ├── chapter-contracts/
│   │       ├── chapters/                            ← TTS-safe source per chapter
│   │       ├── episodes/
│   │       ├── transcripts/
│   │       ├── m4a/ (or audio/)                     ← rendered audio (gitignored, on disk only)
│   │       ├── slide-decks/                         ← internal slide artifacts
│   │       └── _system/meta.yml                     ← book-level state + provenance (publication.status)
│   ├── Technical/                                   ← BUCKET (e.g. claude-code-training)
│   │   └── <slug>/ …
│   ├── Fiction/                                     ← BUCKET (e.g. journey-to-the-west)
│   │   └── <slug>/ …
│   ├── Guides/                                      ← BUCKET (e.g. healthequity)
│   │   └── <slug>/ …
│   │
│   ├── published/                                   ← cross-book reference ONLY (no per-book folders)
│   │   ├── _meta/catalog.md                         ← auto-generated cross-book index
│   │   └── archetypes/                              ← cross-book reference (e.g., islamic-scholastic-text.md)
│   ├── knowledge-base/                              ← canonical extracted-knowledge library
│   └── _shared/arabic/                              ← independent copy of cross-utility data (journal has its own)
│
└── _workspace/                                     ← operational docs only (NO books/ here anymore)
    ├── plan/                                       ← response template + design plans + proposals
    ├── setup/                                      ← azure-stack.md + machine bootstrap docs
    ├── orchestrator-logs/
    ├── runbooks/                                   ← incl. repo-split.md historical reference
    └── _archive/, audit/, chats/, proposals/
```

Publishing is a one-way, explicit status flip via `scripts/podcast/publish_to_library.py` (it writes `status=published` in place; it does NOT copy folders).

---

## Agents

The canonical source-of-truth for every agent is [infra/claude-agents/](infra/claude-agents/). The `.github/agents/*.agent.md` mirrors are auto-generated by [scripts/podcast/sync-agent-wrappers.sh](scripts/podcast/sync-agent-wrappers.sh) (canonical direction flipped 2026-05-23 per AU-X2-002).

| Agent | Canonical spec | Role |
|---|---|---|
| `podcast-orchestrator` | [infra/claude-agents/podcast-orchestrator.md](infra/claude-agents/podcast-orchestrator.md) | Autonomous book-to-NotebookLM pipeline driver |
| `podcast-auditor` | [infra/claude-agents/podcast-auditor.md](infra/claude-agents/podcast-auditor.md) | Repo-level health audit — drift, regressions, gaps |
| `podcast-blueprint` | [infra/claude-agents/podcast-blueprint.md](infra/claude-agents/podcast-blueprint.md) | Content-aware episode-structure planner (slot 05.5-blueprint) |
| `podcast-challenger` | [infra/claude-agents/podcast-challenger.md](infra/claude-agents/podcast-challenger.md) | Semantic-quality review (convergence loop ≤5 iterations before any bundle ships) |
| `slide-deck-challenger` | [infra/claude-agents/slide-deck-challenger.md](infra/claude-agents/slide-deck-challenger.md) | Visual-quality challenger for slide-deck bundles |
| `book-challenger` | [infra/claude-agents/book-challenger.md](infra/claude-agents/book-challenger.md) | Semantic-quality challenger for the companion reading edition (PDF path `book.md`) — Arabic-script accuracy, no-teaching-lost, voice consistency |
| `podcast-extract` | [infra/claude-agents/podcast-extract.md](infra/claude-agents/podcast-extract.md) | Single-chapter → NotebookLM bundle fast path |
| `podcast-publisher` | [infra/claude-agents/podcast-publisher.md](infra/claude-agents/podcast-publisher.md) | Flip a finalized book's `status` draft→published in place (gates G1–G5+G7; G6 obsolete) |
| `podcast-trainer` | [infra/claude-agents/podcast-trainer.md](infra/claude-agents/podcast-trainer.md) | Cross-book pattern learner; refines podcast-challenger + handbook with regression gates |
| `refine-prompt` | [infra/claude-agents/refine-prompt.md](infra/claude-agents/refine-prompt.md) | Refines a raw request into one compact instruction-paragraph |

Retired 2026-05-23: `podcast-operator` (multi-machine "where am I, what's next?" entry — no longer needed in single-machine model). Retired 2026-05-28: `docs-updater` + `reconcile` (both targeted `docs/architecture/index.html` which has been deleted — architecture documentation now lives in `_workspace/plan/architecture.md` and the Astro site). Lingering wrappers under `.github/agents/` for `CORTEX`, `repo-surgeon`, and `operating-contract` predate the 2026-05-23 canonical-direction flip and are mirrored without an `infra/` counterpart; they survive for backwards-compatibility with older session prompts.

---

## The podcast skill: `podcast`

**Purpose:** Convert scholarly Arabic books into NotebookLM Audio Overview podcast series.

**Owns:** `content/<Bucket>/<slug>/` (orchestrator state + chapter contracts + chapters + episode drafts + transcripts); shipping is a `status` draft→published flip in place via `publish_to_library.py` (no folder move).

**Reads:** sources Asif provides + [scripts/podcast/_rules.py](scripts/podcast/_rules.py) (Python rule modules — canonical authority) + [infra/claude-agents/podcast-challenger.md](infra/claude-agents/podcast-challenger.md) (per-Category check definitions) + `content/_shared/arabic/` + `content/_shared/islam/` (read-only). The prior `content/podcast/.skill/handbook/` tree was retired 2026-05-23; its conceptual content lives in the code authority above.

**Triggers:** `/podcast`, `/extract-chapter <ref>`, `claude --agent podcast-orchestrator`.

**Phases:** 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring (extract + framing + build → challenger convergence) → ship via `publish_to_library.py` → trainer.

---

## Single-machine model

The pipeline is **machine-agnostic**. Most work is done by Anthropic + Azure remotely (LLM calls, OCR, translation, speech), so the host machine carries no special-snowflake configuration. The repo runs the same way on any Mac with `python3`, `git`, and the Azure stack credentials (per [docs/setup/azure-stack.md](docs/setup/azure-stack.md)).

- **Per-content branches, grouped by content bucket (locked 2026-06-07, supersedes the 2026-06-04 bare-slug model).** Every new piece of content is processed on its own branch off `develop`, named `<Bucket>/<full-slug>` (e.g. `Fiction/journey-to-the-west-vol-1`, `Islamic/ayyuhal-walad`) via [scripts/podcast/_branching.py](scripts/podcast/_branching.py) — `branch_name(category, slug, *, profile=None, bucket=None)` returns `<Bucket>/<slug>`, resolving the bucket from `content_profile` (via the shared `_paths.resolve_bucket`, so branch bucket == folder bucket) and falling back to a coarse `category` map (defaulting to Islamic). Type prefixes (`book/`/`lecture/`…) were retired 2026-06-04; `branch_prefix()` kept deprecated for back-compat. Slugs are always full kebab-case (never abbreviated). Branches merge back to `develop` only after `podcast-publisher` flips the item's `status` to `published`.
- **No per-machine coordination.** The earlier two-machine model (operator files, `~/.machine-id` detection, book-queue mutex, coordination-protocol §15) was retired 2026-05-23. The cross-machine assignment layer is gone; content branches now serve only as isolation, not as work assignment.
- **`scripts/start-session.sh`** is the simplified session bootstrap — fetches origin, fast-forwards develop, surfaces in-flight content branches + next-action commands.

---

## Setup stage — pre-pipeline system check (added 2026-06-07)

Before any pipeline work runs, the orchestrator executes a **Setup stage** that resolves machine-readiness problems up front instead of crashing deep inside a phase. Two parts:

1. **Interpreter self-heal** ([scripts/podcast/orchestrate_book.py](scripts/podcast/orchestrate_book.py) `_ensure_capable_interpreter`) — if the active interpreter can't `import yaml`, the orchestrator transparently re-execs under the repo virtualenv `.venv/bin/python` (which carries PyYAML/anthropic/requests). A sentinel env var (`_PODCAST_REEXECED`) prevents an exec loop; a missing/incomplete venv surfaces an actionable `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. This eliminates the failure mode where system `python3` (lacking deps) crashed every phase at `import yaml` and the watchdog mis-reported it as "working tree dirty".

2. **Doctor / system check** ([scripts/podcast/preflight_doctor.py](scripts/podcast/preflight_doctor.py) `run_doctor`) — runs at the top of `main()` for BOTH initial and resume, **before the watchdog is spawned**, so a failure fails fast with the exact fix command instead of the watchdog retry-looping a doomed run 20×. Four checks: **deps** (yaml/anthropic/requests importable), **claude-auth** (keychain OAuth-token expiry pre-check + a live `claude -p` ping mirroring `_run_claude_p`'s API-key-stripped Max path; a 401/expired token halts with `claude login`), **anthropic-net** (api.anthropic.com:443 reachable), **azure** (OCR/Translate probe — skipped automatically on resumes where phase 0a already completed). Flags: `--doctor` runs only the check and exits (0=ready, 1=blocked); `--skip-doctor` bypasses it (use only when the failing subsystem is unused by the phases being run). The watchdog ([scripts/podcast/watch_orchestrator.sh](scripts/podcast/watch_orchestrator.sh)) also prefers `.venv/bin/python` for the same dependency reason.

---

## Duplicated general-utility skills (also in sibling journal repo as independent copies)

| Skill | Purpose |
|---|---|
| `skills-staging/clean-commit/` | Pre-commit / commit-quality discipline |
| `skills-staging/repo-surgeon/` | Holistic architecture audit, orphan cleanup |

Each is an independent copy. Edits here do NOT cross-propagate to the sibling journal repo.

**Removed 2026-06-02:** `cowork-brief`, `tell-me`, `usage-auditor` — ADLC/journal-repo tools with no invocation path in podcast-factory. Tombstoned in `docs/reference/skill-registry.md`.

---

## Retired 2026-05-22

- **Anthropic API proxy** (`server/`) — Node/Express proxy bound to 127.0.0.1:3001. The journal app no longer needs the Anthropic API; this surface is gone from both repos. Not migrated to journal.
- **Cloudflare deploy scaffold** — `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`. Same reason: no Workers-served journal site any more.
- **Docs related to the retired stack** — `docs/anthropic-api-setup.md`, `docs/proxy-setup.md`.
- **External orphan** — the `journal` and `journal-dev` Cloudflare Workers on Cloudflare itself remain orphaned external state; Asif may delete via the Cloudflare dashboard when convenient.

---

## What lives in the sibling `journal` repo (NOT here)

- `content/babu-memoir/` (the memoir)
- `site/` (static React display of memoir chapters; local-only post-2026-05-22)
- `scripts/memoir/` + `scripts/site/`
- `skills-staging/journal/`, `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/`
- `.github/agents/journal-orchestrator.agent.md`, `.github/agents/journal-challenger.agent.md`
- `infra/claude-agents/journal-challenger.md`

---

## Azure-on-disk layout reminder

Azure resources retain the original `journal-*` naming convention (resource group `rg-journal-ai`, all `journal-*` cognitive services, storage, Key Vault). The `APP_NAME` field in `infra/azure/azure-config.env` was changed from `"journal"` to `"podcast-factory"` 2026-05-22 as a config-label change only; **no Azure-side rename was performed**, all resources keep their existing names indefinitely.

---

## Conventions

- **No emojis in code or commits** unless explicitly invited.
- **Status emojis (🟢 🟡 🔴 ⚠) in responses** per the 4-part response template (canonical at `_workspace/plan/response-template.md`).
- **Markdown links for files and commits** — `[name](path)` and `[abc1234](https://github.com/asifhussain60/podcast-factory/commit/abc1234)`.
- **Per-content branches** — every piece of content runs on its own typed branch off develop. Multiple books may be in-flight simultaneously; isolation is via branches, not machine ownership.
