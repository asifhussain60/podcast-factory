# Podcast Factory Ecosystem Framework

**Last updated:** 2026-05-30

This document governs the **`podcast-factory`** repo: the multi-phase podcast pipeline that converts scholarly Arabic books into NotebookLM-driven podcast series, the Azure stack that powers OCR / translation / speech, and the agents/skills that support podcast authoring. Memoir + site work moved to the sibling **[journal](https://github.com/asifhussain60/journal)** repo as of the 2026-05-22 split. The Anthropic API proxy (`server/`) and the Cloudflare deploy scaffold were retired the same day — see §"Retired" below. The previous cross-machine coordination model (operator files, machine-id detection, per-machine book branches) was retired 2026-05-23 — see §"Single-machine model" below.

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

## Content tree

Post-2026-05-23 restructure (one flat repo, content container with drafts + published children):

```
podcast-factory/
├── content/                                        ← CONTENT CONTAINER
│   ├── drafts/                                     ← WORKSHOP (was: _workspace/books/ + per-branch content/podcast/library/books/)
│   │   └── <slug>/                                 ← per-book in-progress state
│   │       ├── _system/
│   │       │   ├── orchestrator-state.json
│   │       │   ├── challenger-report.md
│   │       │   ├── series-plan.md
│   │       │   └── …
│   │       ├── chapter-contracts/
│   │       ├── chapters/                           ← TTS-safe source per chapter
│   │       ├── episodes/
│   │       ├── transcripts/
│   │       ├── m4a/                                ← rendered audio (when present)
│   │       ├── slide-decks/                        ← internal slide artifacts
│   │       └── meta.yml                            ← book-level state + provenance
│   │
│   └── published/                                  ← PUBLISHED CATALOG (was: library/, read-only by convention)
│       ├── _meta/catalog.md                        ← auto-generated cross-book index
│       ├── archetypes/                             ← cross-book reference (e.g., islamic-scholastic-text.md)
│       ├── books/<slug>/                           ← shipped per-book outputs
│       │   ├── index.md                            ← book metadata
│       │   ├── transcript/                         ← polished NotebookLM SOURCE per chapter
│       │   └── podcasts/                           ← episode bundles organized by series
│       └── {articles,documents,interviews,lectures,letters}/
│
└── _workspace/                                     ← operational docs only (NO books/ here anymore)
    ├── plan/                                       ← response template + design plans + proposals
    ├── setup/                                      ← azure-stack.md + machine bootstrap docs
    ├── orchestrator-logs/
    ├── runbooks/                                   ← incl. repo-split.md historical reference
    └── _archive/, audit/, chats/, proposals/
└── content/
    ├── _shared/arabic/                   ← independent copy of cross-utility data (journal has its own)
    └── podcast/
        ├── _README.md
        └── .skill/                       ← handbook + _learning substrate
            ├── ROADMAP.md
            ├── handbook/                 ← book-agnostic skill refs + templates
            └── _learning/                ← cross-book pattern learning substrate
```

Promotion from workspace → library is one-way and explicit via `scripts/podcast/publish_to_library.py`; manual edits to `content/published/` are CI-checked.

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
| `podcast-extract` | [infra/claude-agents/podcast-extract.md](infra/claude-agents/podcast-extract.md) | Single-chapter → NotebookLM bundle fast path |
| `podcast-publisher` | [infra/claude-agents/podcast-publisher.md](infra/claude-agents/podcast-publisher.md) | Move shipped content from drafts/ to published/books/ (gates G1–G7) |
| `podcast-trainer` | [infra/claude-agents/podcast-trainer.md](infra/claude-agents/podcast-trainer.md) | Cross-book pattern learner; refines podcast-challenger + handbook with regression gates |
| `refine-prompt` | [infra/claude-agents/refine-prompt.md](infra/claude-agents/refine-prompt.md) | Refines a raw request into one compact instruction-paragraph |

Retired 2026-05-23: `podcast-operator` (multi-machine "where am I, what's next?" entry — no longer needed in single-machine model). Retired 2026-05-28: `docs-updater` + `reconcile` (both targeted `docs/architecture/index.html` which has been deleted — architecture documentation now lives in `_workspace/plan/architecture.md` and the Astro site). Lingering wrappers under `.github/agents/` for `CORTEX`, `repo-surgeon`, and `operating-contract` predate the 2026-05-23 canonical-direction flip and are mirrored without an `infra/` counterpart; they survive for backwards-compatibility with older session prompts.

---

## The podcast skill: `podcast`

**Purpose:** Convert scholarly Arabic books into NotebookLM Audio Overview podcast series.

**Owns:** `content/drafts/<slug>/` (orchestrator state + chapter contracts + chapters + episode drafts + transcripts), with promotion to `content/published/books/<slug>/` (shipped) via `publish_to_library.py`.

**Reads:** sources Asif provides + [scripts/podcast/_rules.py](scripts/podcast/_rules.py) (Python rule modules — canonical authority) + [infra/claude-agents/podcast-challenger.md](infra/claude-agents/podcast-challenger.md) (per-Category check definitions) + `content/_shared/arabic/` + `content/_shared/islam/` (read-only). The prior `content/podcast/.skill/handbook/` tree was retired 2026-05-23; its conceptual content lives in the code authority above.

**Triggers:** `/podcast`, `/extract-chapter <ref>`, `claude --agent podcast-orchestrator`.

**Phases:** 0a (ingest) → 0b (refine) → 0c (phonetic) → 0d (chapter design) → 0e (enrich) → 0f (review halt) → per-chapter authoring (extract + framing + build → challenger convergence) → ship via `publish_to_library.py` → trainer.

---

## Single-machine model

The pipeline is **machine-agnostic**. Most work is done by Anthropic + Azure remotely (LLM calls, OCR, translation, speech), so the host machine carries no special-snowflake configuration. The repo runs the same way on any Mac with `python3`, `git`, and the Azure stack credentials (per [docs/setup/azure-stack.md](docs/setup/azure-stack.md)).

- **Per-content branches (locked 2026-05-24).** Every new piece of content (book, document, lecture, article, letter, interview, or generic draft) is processed on its own typed branch off `develop`. The branch name is `<prefix>/<full-slug>` where `<prefix>` derives from the content's `category` field via [scripts/podcast/_branching.py](scripts/podcast/_branching.py): `book/`, `doc/`, `lecture/`, `article/`, `letter/`, `interview/`, or `draft/` (fallback). Slugs are always full kebab-case (never abbreviated). Branches merge back to `develop` only after `podcast-publisher` ships the artifacts to `content/published/`.
- **No per-machine coordination.** The earlier two-machine model (operator files, `~/.machine-id` detection, book-queue mutex, coordination-protocol §15) was retired 2026-05-23. The cross-machine assignment layer is gone; content branches now serve only as isolation, not as work assignment.
- **`scripts/start-session.sh`** is the simplified session bootstrap — fetches origin, fast-forwards develop, surfaces in-flight content branches + next-action commands.

---

## Duplicated general-utility skills (also in sibling journal repo as independent copies)

| Skill | Purpose |
|---|---|
| `skills-staging/clean-commit/` | Pre-commit / commit-quality discipline |
| `skills-staging/cowork-brief/` | Refine raw request → compact instruction-paragraph |
| `skills-staging/repo-surgeon/` | Holistic architecture audit, orphan cleanup |
| `skills-staging/tell-me/` | Codebase tour / explainer skill |
| `skills-staging/usage-auditor/` | Token / API usage audit |

Each is an independent copy. Edits here do NOT cross-propagate to the sibling journal repo.

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
- **Per-book ownership** — one book is owned by one machine at a time (see `_workspace/plan/book-queue.md`). Don't touch a book that's not on your machine's branch.
