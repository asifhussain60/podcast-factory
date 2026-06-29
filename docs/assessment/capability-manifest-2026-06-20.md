# Podcast-Factory — Capability Manifest & Architecture Assessment

**Snapshot date:** 2026-06-20 · **Branch:** develop @ af7f6a5 · **Scope:** pipeline + web app + knowledge base
**Validation depth:** STATIC only (import health, dependency resolution, code↔doc/spec consistency, determinism).
Runtime / integration / end-to-end validation are NOT covered here — they are spend-gated (Azure, Gemini, ElevenLabs)
and/or require manual external steps (NotebookLM upload/download). See "Validation status legend" below.

> This is a point-in-time snapshot. The repo runs ~685 commits / 14 days; treat anything here as accurate as of the
> date above and re-derive before relying on a specific detail. The living architecture views (dashboard snapshots,
> plan.yaml) remain the continuously-regenerated source of truth.

## Validation status legend

| Status | Meaning |
|---|---|
| Statically Sound | Imports cleanly, deps resolve, code matches its spec/docs. Runtime NOT exercised. |
| Statically Sound — With Risks | As above, but a named risk (silent degradation, untested path, portability). |
| Statically Unverifiable | Cannot confirm statically (e.g. needs runtime/external service or a heavy dep absent from venv). |
| Spec/Code Gap | A documented rule or capability has no enforcing implementation, or vice versa. |

---

## 1. Architecture Assessment

The system is a layered, single-writer pipeline that converts source documents (mostly scholarly Arabic books) into
NotebookLM-driven podcast bundles, companion reading-edition PDFs, slide decks, and optional video — plus an Astro web
app (reader + Studio editor + plan/architecture dashboard) and a knowledge-base/corpus engine.

**Layers (top to bottom):**

1. **Entry & control** — `orchestrate_book.py` (lock, arg-parse, watchdog spawn) → `phases/initial_driver.py`
   (0a→0f) and `phases/resume_dispatcher.py` (resume routing) → `phases/chapter_driver.py` (per-chapter loop).
2. **State machine** — `_progress.py` (atomic state file, the canonical `PHASES` tuple, stale-resume detection),
   supervised by `supervise_run.py` + `watch_orchestrator.sh` (fast-fail, single-actor, cost ceiling).
3. **Deterministic spine** — `_paths.py` (↔ `content-paths.ts`), `_branching.py`, `_rules.py` (the single rule
   authority), `_content_profile.py`, `_work_manifest.py`. Computes every path, bucket, branch name deterministically.
4. **Semantic quality layer** — authoring + enrichment (`_augmentation.py`, `_literary.py`), doctrinal fidelity
   (`_doctrinal.py`), validators (`_validators*.py`, `build_episode_txt.py` hard gate), contract validation
   (`_contract_validation.py`), PEQ scoring (`_quality.py`), and the convergence loop (`_convergence.py`,
   `_dialogue_convergence.py`) driven by the challenger/trainer agents.
5. **Media engines** — Azure (OCR/Speech/Translate/DALL-E), ElevenLabs (dormant), Gemini/Imagen3, Pillow slides,
   FFmpeg stitching, Playwright PDF, plus deterministic SVG/Quran-injection helpers.
6. **Publishing & delivery** — `publish_to_library.py` (G1–G7 gates, status-flip in place), `deliver_book.py` /
   `export_distribution.py` (Google Drive).
7. **Knowledge base** — `intelligence/{extractor,librarian,augmenter}.py`, `_db.py` (SQLite), dedup + concept index,
   `corpus_sync.py` (DB↔JSONL).
8. **Web app** — `plan-dashboard/` (Astro pages, `/api/*` SSR routes, reader/Studio components, snapshot JSONs).

**Architectural strengths (verified statically):**

- **Single sources of truth are real, not aspirational.** `PHASES` (phase order), `_rules.py` (all rule constants),
  `_paths.py` (all paths), and `emit_finding()` (the only ledger-write path) are each centralized and re-exported,
  with a drift-guard test for the phase list. This is the backbone that keeps a 180-module pipeline coherent.
- **Determinism in path computation is clean.** No clock/random/cwd dependence in path logic; the only env input
  (`PODCAST_FACTORY_ROOT`) is now honored identically by Python and TypeScript (fixed af7f6a5, 2026-06-20).
- **Defense-in-depth on quality.** Hard build-time gates → convergence loop → publish gates → post-prod review, with
  an append-only findings ledger feeding a regression-gated trainer. Verdicts cannot silently downgrade.
- **Graceful degradation is pervasive** for external services (missing Quran mirror → English left intact; missing
  cover → renders anyway; Azure error → actionable message + manual `--retry-phase`).

**The dominant cross-cutting risk: silent no-ops.** The same "degrade quietly when data is absent" pattern that makes
the system robust also hides gaps. Multiple gates skip without emitting any finding when their inputs are missing
(see Risk Register R1). This is the single theme most worth addressing systemically.

---

## 2. Capability Manifest

Grouped by subsystem. Columns: Capability · Entry point · Key files · External deps · Tests · Static status.

### 2.1 Orchestration & state machine

| Capability | Entry point | Key files | External deps | Tests | Static status |
|---|---|---|---|---|---|
| Atomic state persistence | `read_state/write_state/update_phase` | `_progress.py` | none | test_state_machine, test_phases | Statically Sound |
| Phase registry & ordering | `_progress.PHASES` | `_progress.py`, `_phases.py` | none | test_phases (drift guard) | Statically Sound |
| Per-book lock | `_acquire_book_lock` | `orchestrate_book.py` | fcntl | (integration only) | Statically Sound — With Risks (no unit test) |
| Cost guard (real-money ceiling) | `cost_ceiling_check` | `cost_guard.py`, `_cost_ledger.py` | reads ledger | none direct | Statically Sound — With Risks (R2) |
| Initial driver (0a→0f) | `run_initial` | `phases/initial_driver.py` | LLM/Azure | test_routing_capabilities, e2e | Statically Sound |
| Resume dispatcher | `run_resume` | `phases/resume_dispatcher.py` | none | test_orchestrate_work_pause/paths | Statically Sound |
| Chapter driver (per-chapter loop) | `_drive_per_chapter_and_after` | `phases/chapter_driver.py` | LLM | test_audio_driver, e2e | Statically Sound |
| Supervision + watchdog | `watch_orchestrator.sh`, `supervise_run.py` | same | git, jq | test_run_supervision | Statically Sound — With Risks (R3) |
| Preflight gates | `preflight_initial/resume`, `run_doctor` | `phases/preflight.py`, `preflight_doctor.py` | Azure probe | e2e | Statically Sound |
| Cost ledger | `append_cost_row` | `_cost_ledger.py` | none | (indirect) | Statically Sound |
| Session grouping | `derive_sessions` | `_sessions.py` | none | test_sessions (11) | Statically Sound |
| Stage-review gate | `read_stage_review` | `_stage_gate.py` | none | none | Statically Sound — With Risks (no test; misplaced?) |

### 2.2 Deterministic spine & publishing

| Capability | Entry point | Key files | External deps | Tests | Static status |
|---|---|---|---|---|---|
| Path resolution (Py↔TS mirror) | `content_dir` / `contentDir` | `_paths.py`, `content-paths.ts` | `PODCAST_FACTORY_ROOT` (opt) | test_phases (path/bucket/volume) | Statically Sound (parity confirmed af7f6a5) |
| Bucket / profile routing | `bucket_for_profile`, `phase_capabilities` | `_rules.py` | none | test_routing_capabilities | Statically Sound |
| Branch naming | `branch_name` | `_branching.py` | none | (path tests) | Statically Sound |
| Reading-edition PDF path | `_find_pdf` | `deliver_book.py`, `export_distribution.py` | none | — | Spec/Code Gap (R4: two inconsistent finders) |
| Google Drive delivery | `_default_target`, `deliver` | `deliver_book.py` | Google Drive mount | — | Statically Sound — With Risks (R5: hardcoded user/path) |
| Publish gates G1–G7 + status-flip | `publish` | `publish_to_library.py` | none | (gate tests) | Statically Sound — With Risks (R6: G7 `--allow-mode-2` bypass) |
| Distribution export | `export` | `export_distribution.py` | Google Drive, ffmpeg | — | Statically Sound — With Risks (R4) |
| Secrets resolver | `resolve_secret` | `_secrets.py` | Azure Key Vault | — | Statically Sound |
| Work manifests / density profiles / archetypes | various | `_work_manifest.py`, `_density_profiles.py`, `_archetypes.py` | none | (path/volume tests) | Statically Sound |

### 2.3 Semantic quality layer

| Capability | Entry point | Key files | Convergence | Tests | Static status |
|---|---|---|---|---|---|
| Augmentation checks (W1–W6) | `run_all` | `_augmentation.py` | 5 inner / 3 outer; W1/W2 auto-revert | test_augmentation_challenger (+3) | Statically Sound — With Risks (R1) |
| Doctrinal fidelity (T1–T5) | `run_doctrinal_checks` | `_doctrinal.py` | P0 fixer ≤3; T3 hard gate | test_doctrinal | Statically Sound — With Risks (R1: T4 stub, non-Islamic no-op) |
| Chapter/framing validators | `validate_chapter/framing` | `_validators*.py`, `_validator_constants.py`, `build_episode_txt.py` | build-time hard gate | test_validators_pronunciation (+) | Statically Sound — With Risks (R7: P1-vs-P0 path ambiguity) |
| Contract validation (4 gates) | `validate_contract_full` | `_contract_validation.py`, `_extract_contract.py` | smoke/extract/lint/0d | test_contract_validation (427L) | Statically Sound |
| PEQ scoring (5 axes) | `score` | `_quality.py`, `challenger_scoring.py` | once/chapter, gates verdict | test_challenger_scoring | Statically Sound — With Risks (R8: voice-axis silent degrade) |
| Chapter convergence loop | `run_convergence_for_chapter` | `_convergence.py` | 3 outer, fixer ≤3/P0, no downgrade | test_convergence_parse/safety_rails | Statically Sound |
| Dialogue gate + convergence | `gate_dialogue_script`, `run_dialogue_convergence` | `_validators_dialogue.py`, `_dialogue_convergence.py` | 5 max; render-blocking verdict | test_dialogue_gate/script | Statically Sound |
| Literary revoice | `run` | `_literary.py` | post-audio, idempotent | test_literary_guardrail | Statically Sound — With Risks (R1: invalid voice silent fallback) |
| Findings ledger + learning | `emit_finding`, `learn_aggregate/propose` | `_rules.py` | append-only, fcntl | test_convergence_safety_rails | Statically Sound |
| Sermon-verbatim rule | (none) | `_rules.py` R_SERMON_VERBATIM | — | none | **Spec/Code Gap (R9: rule defined, no enforcer)** |

### 2.4 Media engines

| Capability | Entry point | External service / dep | Secret | Static status |
|---|---|---|---|---|
| Audio engine registry / voice casting | `resolve_audio_engine` | ElevenLabs (dormant) | ELEVENLABS_API_KEY | Statically Sound — With Risks (R10: dormant, untested reactivation) |
| Azure OCR/Speech/Translate/DALL-E | `docintel_analyze_pdf`, `transcribe_audio`, `translate_text`, `generate_image_dalle` | Azure (stdlib urllib) | Key Vault | Statically Sound — With Risks (R11: no offline/fallback) |
| ElevenLabs TTS | `text_to_dialogue` | ElevenLabs | ELEVENLABS_API_KEY | Statically Sound (dormant) |
| Audio fingerprint / style score | `fingerprint`, `score_against_profile` | numpy + FFmpeg | — | Statically Unverifiable (numpy absent from this venv) |
| Quran citation → Arabic injection | `inject_recitations` | mirror.db (read-only) | — | Statically Sound (deterministic, no LLM) |
| MP3 frame chunking | `chunk_mp3_bytes` | none (stdlib) | — | Statically Sound |
| TTS sanitization | `sanitize_text` | none (stdlib) | — | Statically Sound |
| Book compose (whole-book revoice) | `compose_book` | Opus, mirror.db | Max | Statically Sound |
| Book cover | `ensure_cover` | Gemini flash image | GOOGLE_API_KEY | Statically Sound (non-blocking) |
| Book PDF render | `build_book` | Node + Playwright/Chromium | — | Statically Unverifiable (needs chromium) |
| Fiction illustrated PDF | `main` | Gemini Imagen3 + Playwright | GOOGLE_API_KEY | Statically Unverifiable |
| Video storyboard + images | `generate_video_layer.main` | Gemini + Imagen3 | GOOGLE_API_KEY | Statically Sound — With Risks (R12: per-episode no spend cap) |
| Pillow slide render | `render_all_slides` | Pillow | — | Statically Unverifiable (PIL hard-required) |
| Video stitch | `stitch_video.main` | FFmpeg | — | Statically Sound (equal-split rule confirmed) |
| Slide deck authoring/convergence | `author_deck_pair`, `converge_slide_deck` | Max | — | Statically Sound |
| Slide replicate (PDF→SVG) | `analyze_and_replicate_slides` | Max vision, Poppler | — | Statically Sound (non-blocking, raster fallback) |
| Slide import (PDF→figures) | `import_slides` | Poppler, Max vision | — | Statically Sound |
| SVG geometry lint / patterns | `geometry_findings`, pattern fns | none (stdlib) | — | Statically Sound |
| NotebookLM transcription | `transcribe_notebooklm.main` | Azure Speech, ffprobe | Key Vault | Statically Sound — With Risks (R11) |

### 2.5 Knowledge base & web app

| Capability | Entry point | Key files | Tests | Static status |
|---|---|---|---|---|
| Atom extraction (B1) | `extract_atoms_for_book` | `intelligence/extractor.py` | test_intelligence_extractor (8) | Statically Sound |
| Librarian merge (B2) | `merge_into_library` | `intelligence/librarian.py` | test_intelligence_librarian (10) | Statically Sound |
| Augmenter (B3) | `augment_episode_text` | `intelligence/augmenter.py` | test_intelligence_augmenter (11) | Statically Sound (disabled by default) |
| Dedup engine | `dedup` | `intelligence/dedup_corpus.py` | test_corpus_dedup | Statically Sound |
| Concept index | `build_concepts` | `intelligence/concept_index.py` | none | Statically Sound — With Risks (no tests; untagged atoms unmapped) |
| Corpus sync (DB↔JSONL) | `export`/`rebuild` | `intelligence/corpus_sync.py` | test_corpus_sync | Statically Sound (rebuild additive; export clobbers — see memory) |
| SQLite DB + migrations | `get_connection`, `run_migrations` | `_db.py`, `schema/001..031` | test_db (6) | Statically Sound |
| Wisdom ingest | `ingest_all` | `intelligence/wisdom_ingest_knowledge.py` | test_wisdom_ingest (sparse) | Statically Sound — With Risks (chunk/tag logic untested) |
| Astro pages (22) + layouts | `src/pages/*.astro` | plan-dashboard | **none** | Statically Unverifiable (no test; lint:views = HTML only) |
| API routes (`/api/studio`, `/api/corpus`, …) | `src/pages/api/*` | plan-dashboard | **none** | Statically Unverifiable (R13) |
| Content path resolver (TS) | `contentDir`, `statusOf` | `content-paths.ts` | **none** | Statically Sound — With Risks (mirror drift; no parity test) |
| Snapshot system (3 JSONs) | `regenerate-snapshots.{mjs,py}` | plan-dashboard/scripts | none | Statically Sound |
| Reader / Studio / Intake surfaces | reader/*, studio/*, intake/* | plan-dashboard/src/components | **none** | Statically Unverifiable |

---

## 3. Capability Dependency Graph (control & data flow)

```
PDF/source
  → preflight (auth, git, Azure probe)
  → initial_driver: 0a ingest (Azure OCR/Translate) → 0b refine → 0c phonetic → 0ci Islamic gate
        → 0d chapter design (writes contracts; contract validation gate) → 0e enrich (augmenter, knowledge.db)
        → 0literary (Gemini) → 06a review → 0f series-plan HALT
  → [human review] → resume_dispatcher
  → chapter_driver loop: per chapter { extract → frame → build_episode_txt (HARD GATES: validators, doctrinal T3)
        → convergence (challenger ≤5 inner / 3 outer; fixer ≤3/P0; PEQ verdict) }
        → per-chapter-optimize → per-chapter-slides (slide convergence)
        → audio-script → audio-render (NotebookLM=manual | ElevenLabs=api)
        → finalize HALT
  → [human review + NotebookLM produce audio] → audio-ingest (Azure transcription) → postprod-review
  → 0book-compose (Opus revoice) → 0book-illustrate/slide-import → 0book-render (Playwright PDF)
  → publish_to_library (G1–G7, status-flip) → deliver_book/export_distribution (Google Drive)
  → trainer (regression-gated rule diffs) → merge <Bucket>/<slug> → develop

Cross-cutting:
  _rules.py  ──feeds──> validators, doctrinal, augmentation, quality, contract, convergence
  _paths.py  ──feeds──> every phase + publishing; mirrored by content-paths.ts (web app)
  _progress.py state file ──read/written by──> every phase; watched by supervise_run + watchdog
  emit_finding() ──> _learning/findings.jsonl ──> aggregate/propose ──> trainer
  knowledge.db ──> augmenter (0e), Quran injection, web /api/corpus
  cost-ledger.jsonl ──> cost_guard ──> supervisor halt; surfaces real (Azure/Gemini) spend only
```

**Shared resources (contention points):** the per-book `orchestrator-state.json` (single-writer, enforced by lock +
single-actor supervisor); `_learning/findings.jsonl` (multi-book concurrent — fcntl-locked); `knowledge.db` (WAL mode);
the three dashboard snapshot JSONs (regenerated, not hand-edited).

**Mirror pairs that must move together:** `_paths.py` ↔ `content-paths.ts`; `_quality.py`/`challenger_scoring.py` ↔
`peq-scores.ts`; the `_system/` JSON schema ↔ `editorial.ts`/`stage-review.ts`.

---

## 4. Risk Register

| ID | Risk | Severity | Where | Recommended action |
|---|---|---|---|---|
| R1 | **Silent no-op gates** — doctrinal (non-Islamic tradition packs, T4 farman stub), augmentation (content_level absent), literary (invalid voice) all skip WITHOUT emitting any finding when inputs are missing | High (systemic) | `_doctrinal.py`, `_augmentation.py`, `_literary.py` | Emit an INFO/P2 finding whenever a gate skips for missing data, so skips are auditable |
| R2 | Cost-guard check is read-only; halt decisions scattered across supervisor + chapter_driver; a new long phase can bypass the cap | Medium | `cost_guard.py` consumers | Centralize the ceiling check in a pre-phase hook |
| R3 | 900s staleness threshold hard-coded in 3 places (`_progress`, `supervise_run`, shell); drift breaks auto-recovery silently | Medium | supervision trio | Extract to one config constant |
| R4 | PDF finder differs: `deliver_book` prefers titled edition, `export_distribution` only `book.pdf` — same book can ship different PDFs to different targets | Medium | `deliver_book.py`, `export_distribution.py` | Unify on one `_find_pdf()` |
| R5 | Google Drive target hardcodes username + macOS mount path (non-portable) | Low (single-machine by design) | `deliver_book.py` | Accept Drive root via env/config; fine to defer |
| R6 | `publish` G7 `--allow-mode-2` lets a non-converged book ship with verdict=unknown | Medium | `publish_to_library.py` | Keep, but ensure audit marks it; consider requiring a reason string |
| R7 | Quran-citation & translit-formula asserts are labelled "P1" but sit on the `sys.exit` hard-fail path — advisory vs blocking is ambiguous | Medium | `build_episode_txt.py` | Decide + relabel/refactor; add the missing test |
| R8 | PEQ voice axis silently redistributes weight to fidelity when exemplar vectors absent — callers get a degenerate 4-axis score with no warning | Medium | `_quality.py` | Emit P2 when voice axis unavailable |
| R9 | `R_SERMON_VERBATIM` defined in rules but no enforcing function or test — sermons may split across H2 sections undetected | Medium (Spec/Code Gap) | `_rules.py`, `build_episode_txt.py` | Implement `assert_sermon_verbatim()` + test before a sermon-bearing book ships |
| R10 | ElevenLabs engine dormant since 2026-06-14; reactivation path untested at scale | Low | `_audio_engines.py`, `_elevenlabs.py` | Add a smoke test before reactivation |
| R11 | Azure services have no offline/fallback; 0a OCR, audio-ingest, video block on Azure availability | Medium (external) | `_azure.py` consumers | Accept (manual `--retry-phase`); document RTO |
| R12 | Video generation has a per-image cost-ledger but no per-episode spend cap | Medium | `generate_video_layer.py` | Add per-episode cap or pre-gen budget assertion |
| R13 | **Web app + API routes have ZERO automated tests** (22 pages, 14 studio routes, all components); broken snapshot/route surfaces only in prod | High | `plan-dashboard/` | Add SSR smoke + API contract tests; at minimum a content-paths Py↔TS parity test |
| R14 | Wisdom pipeline ~1 test across 20 modules; rewrite/annotate/dedup unvalidated | Medium | `scripts/wisdom/` | Backfill unit tests on the deterministic logic |

---

## 5. Test Coverage Analysis

- **Strong:** path/branch/content/volume (146 tests), contract validation (427-line suite), doctrinal, dialogue gate,
  convergence safety rails, intelligence extractor/librarian/augmenter (29 tests), DB + migrations.
- **Full suite:** 1421 passed, 1 skipped, 1 collection error (`test_episode_engine_and_style.py` requires `numpy`,
  absent from this venv — pre-existing environment gap, not a code defect).
- **Weak / absent:** web app (zero), wisdom pipeline (~1, live-only), concept index (zero), cost guard (none direct),
  per-book lock (integration only), the "non-wired" episode-format P1 warning path, R_SERMON_VERBATIM.
- **Environment caveat:** `numpy`/`PIL`/`chromium` are trusted as installed; there is no session-start preflight for
  them (the orchestrator only probes PyYAML), so their absence surfaces only at the relevant phase.

---

## 6. Gap Analysis (summary)

- **Functional:** R_SERMON_VERBATIM unenforced (R9); concept index leaves untagged atoms unmapped (blocks Wave 2
  semantic search); no automatic Azure-transcription chunking for >~50MB audio.
- **Validation:** web app, wisdom layer, concept index untested; numpy-dependent audio modules unverifiable here.
- **Documentation:** CLAUDE.md is largely accurate (video rules, audio rules, determinism all confirmed); the one
  recently-corrected stale claim (infra/cloudflare) is already fixed in history.
- **Security/secrets:** vault-first resolution is clean; no secrets in code. Google Drive path is the only hardcoded
  user identifier (single-machine by design).
- **Operational:** silent-no-op gates (R1) are the biggest observability gap; staleness-threshold duplication (R3) and
  scattered cost-halt logic (R2) are the main resilience gaps.

---

## 7. What this assessment did NOT do (honest scope)

- No runtime execution of any phase (would spend Azure/Gemini and needs manual NotebookLM steps).
- No integration/E2E verification of multi-service workflows.
- No web app build/render verification (no `npm run build` executed).
- No verification of numpy/PIL/chromium-dependent code paths.

These are the spend-gated / external-dependency phases (Protocol Phases 2–3) and require explicit authorization plus,
for the audio leg, a human at the NotebookLM keyboard.
