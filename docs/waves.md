# Podcast Factory — wave log

Dated records of what changed in each build wave, newest first. Moved out of
`framework.md` on 2026-07-26: it was 448 lines of which the first 238 were this log,
so more than half the pipeline spec was history — and because the spec is linked from
CLAUDE.md it loads into session context, meaning the log cost tokens on every turn.

Kept rather than deleted. These sections are design rationale — *why is it this way* —
which is the most expensive kind of knowledge to lose and the kind agents actually
read. Not folded into `CHANGELOG.md`: release-please owns and regenerates that file
from conventional commits, so hand-written sections there would be clobbered.

`framework.md` now holds only the timeless reference material: the content tree, the
agent roster, the deliverable routes, the audio engines, and the conventions.

---

## 2026-06-18 Wave — work-level teaching allocator + curated audio density + 0d hardening

For multi-volume **works** (one synthesized teaching ledger split across volumes,
e.g. `al-anwaar-al-lateefah`), a pre-pass guarantees every concept is placed once,
deduplicated, in the right volume, before any volume's 0d runs.

- **Teaching allocator** — [`allocate_teachings.py`](scripts/podcast/allocate_teachings.py).
  LLM-assisted hybrid (flat-rate `claude -p`, no API spend): spine teachings placed
  DETERMINISTICALLY by book order (consistent with the section word-offset partition);
  augmentation placed into sections by batched LLM classification with a Jaccard top-K
  shortlist; conservative LLM dedup (canonical airs once, variants kept for the reading
  edition — no teaching lost). Emits `<work>/_system/_volume-split.json` and a no-loss/
  no-repeat GATE (`union==N`, one volume each, each cluster one home, variants
  consistent) that **raises** on failure. Resume-safe via `_system/_alloc/` checkpoints.
- **Work-level pre-pass** — [`orchestrate_work.py`](scripts/podcast/orchestrate_work.py)
  `_ensure_allocation()` runs the allocator once for synthesized works (those whose
  `work.yml` declares a shared `ledger`), idempotent on a passing gate, before any
  volume's 0d. Works intaked as per-volume PDFs (no shared ledger) are skipped untouched.
- **Gated 0d consumption** — [`_chapter_design.py`](scripts/podcast/_authoring/_chapter_design.py)
  `_volume_allocation()` injects this volume's authoritative ordered concept list +
  a cross-volume "already-taught" seed (R-NO-DOCTRINE-REPEAT) into the 0d prompt;
  returns empty for single books so **single-book 0d is byte-identical** (zero
  regression). A present-but-malformed `_volume-split.json` WARNS instead of silently
  degrading.
- **Curated breathable density** — per-book `episode_max_concepts` (orchestrator-state
  `config.episode_max_concepts` or series-config), default = the global
  `EPISODE_MAX_CONCEPTS` (3, unchanged for every existing book). Relaxing it yields
  FEWER, fuller episodes (e.g. al-anwaar vol-01: 11 breathable vs 15 crammed), honoring
  the "audio curated / reading edition full-depth" model. Rebound once at
  `author_phase_0d` entry (one book per process → safe).
- **0d robustness** — the per-source-chapter slicer clamps `end_line` to the file
  length (`min(planned, len(refined_lines))`), fixing a common TOC final-line overshoot
  for ALL books; the allocation block forbids cross-episode/continuity references in
  authored chapters/contracts (those leak into NotebookLM literally).

## 2026-06-10 Density wave — chapter-density standard + citation/sermon rules + set integrity

`CHALLENGER_VERSION` bumped 2.4 → 2.5. Standard: [docs/standards/chapter-density.md](docs/standards/chapter-density.md).

- **R-MAX-CONCEPTS** — every episode carries ≤3 concept-level `## H2` sections
  (frames excluded), ~1,500–2,500 words each. Constant `EPISODE_MAX_CONCEPTS` in
  [`_validator_constants.py`](scripts/podcast/_validator_constants.py); auditor
  [`chapter_density_audit.py`](scripts/podcast/chapter_density_audit.py) (discovery
  via `_paths.iter_content()`, nested volumes included). Enforced three places:
  Phase 0d prompt + deterministic post-write gate
  ([`_chapter_design.py`](scripts/podcast/_authoring/_chapter_design.py) rejects +
  deletes over-dense output before the done marker), and the $0 preflight smoke
  gate check #4 ([`preflight_chapter.py`](scripts/podcast/phases/preflight_chapter.py))
  — both OPT-IN via `density_standard: 2` in series-config (legacy books advisory).
- **R-QURAN-CITATION-FORMAT** — canonical inline Quran reference is plain English
  `(chapter N, verse M)`; terse `(Q N:M)` / `(Quran N:M)` / bare `(N:M)` P1-flagged
  (`assert_quran_citation_format`). References never invented; challenger Cat A1
  harmonized to the same format.
- **R-NO-TRANSLIT-FORMULA** — `*Arabic translit* — *translation*` formula pairs
  forbidden in chapter prose (English translation only); ≥4-token diacritic italic
  runs flagged (`assert_no_translit_formula_pairs`).
- **R-PRESERVE-ARABIC-SOURCE** (2026-06-16) — for Arabic-scholarly content, the
  chapter SOURCE preserves every transliterated Arabic term / name / book title /
  surah / honorific verbatim; the English-vs-Arabic decision is made later by the
  human in the Astro phonetic-alignment review, and audio anglicization is applied
  downstream of those decisions (glossary/exonym sanitize layer), never baked into
  the source. Supersedes R-NO-ARABIC-NAMES / R-SURAH-ENGLISH-ONLY / R-ALQAAB inside
  the islamic-7-tier branch of [`_enrichment.py`](scripts/podcast/_authoring/_enrichment.py);
  the contradictory "always prefer the English equivalent" clause was removed from
  the Phase 0d prompt ([`_chapter_design.py`](scripts/podcast/_authoring/_chapter_design.py)).
  (Fixes the regression where 0e per-chapter calls anglicized terms non-deterministically.)
- **R-ARABIC-IN-CHAPTERS** (2026-06-24) — Islamic scholarly chapter sources must
  persist Arabic script beside glossary-backed Arabic terms, while phonetic
  respelling stays out of prose and remains in the glossary / Customize prompt.
  Deterministic post-enrichment injection writes `term (Arabic)` from the curated
  glossary, and finalize gate G13 blocks any Islamic book whose chapters have no
  Arabic script.
- **R-NO-DOCTRINE-REPEAT** (2026-06-16) — Phase 0d's sequential per-source-chapter
  loop threads a running ledger of concept-doctrines already taught by earlier
  chapters (deterministic H2-title extraction via `chapter_density_audit`, no extra
  LLM call, resume-safe) and injects an "already taught — call back, don't re-teach"
  directive into each chapter's authoring prompt. Prevents cross-chapter repetition
  at the source ([`_chapter_design.py`](scripts/podcast/_authoring/_chapter_design.py));
  the chapter-set P8 verbatim check is the detection floor. This is PREVENTION and
  only helps chapters authored AFTER it landed.
- **Retroactive cross-chapter de-dup** (2026-06-16) — the complement for books whose
  0d predates R-NO-DOCTRINE-REPEAT (e.g. kunooz). [`dedup_cross_chapter.py`](scripts/podcast/dedup_cross_chapter.py)
  reuses the P8 shingle logic (inline bibliographic citations stripped — citing the
  same source across chapters is scholarship, not duplication) to locate genuine
  repeated-doctrine runs, picks the earliest chapter as the home, and proposes a
  one-line callback. Dry-run first. A repeat that is a STANDALONE paragraph is
  auto-collapsible; a repeat WOVEN into unique prose is FLAGGED for an authoring
  rewrite and never blunt-cut (a cut leaves dangling lead-ins/restatements — proven
  on kunooz, where all genuine repeats are embedded). Scripture quotations and
  deliberate bookends are surfaced for human judgment, not auto-removed.
- **R-SERMON-VERBATIM** — sermons render WHOLE as their own concept section;
  contract carries `sermon: {present, section_title}`; framing author injects a
  `## Verbatim Recitation` block (post-author gate in
  [`_framing.py`](scripts/podcast/_authoring/_framing.py); compression re-author
  preserves it).
- **R-HEADING-CONCISE** (2026-06-16) — every concept `## H2` section heading is a
  SHORT noun-phrase heading (≤6 words, the INVARIANT-6 soft cap), like a
  professional book heading — NOT a full statement ('The veiling chain', not 'The
  veiling chain that runs from the Father of Imams to the hidden Imam'); detail
  belongs in the prose, structural frames keep their canonical shape. PREVENTION:
  injected into the Phase 0d authoring prompt
  ([`_chapter_design.py`](scripts/podcast/_authoring/_chapter_design.py)) and the
  0e enrichment prompt ([`_enrichment.py`](scripts/podcast/_authoring/_enrichment.py)).
  DETECTION: `check_chapter_set.py` P11 (`check_section_heading_conciseness`,
  advisory P2, excludes frames via the density-audit frame regex).
- **Chapter-set integrity CS7–CS11** — [`check_chapter_set.py`](scripts/podcast/check_chapter_set.py)
  gains deterministic P7 source coverage (line-range union vs refined source),
  P8 overlap + cross-chapter 12-gram duplication, P9 sermon integrity, P10 set
  density, P11 section-heading conciseness; CS11 (flow/conceptual integrity) is challenger judgment. For
  `density_standard: 2` books, P0 set findings HALT post-0d before Phase 0e spend
  ([`preflight.py::_run_chapter_set_check`](scripts/podcast/phases/preflight.py)).
  **(2026-06-16 fix)** `check_band_fit` no longer crashes on a numeric/range
  `length_target` (it did `(... ).lower()` on an int, aborting `run()` before the
  P8 cross-chapter check — so the report read a false "clean"); `_resolve_band`
  now tolerates band-token / range / numeric targets. The preflight wrapper now
  FAILS LOUD — empty/unparseable check output writes a "CHECK DID NOT COMPLETE"
  report (never "clean") and halts density-standard books, instead of silently
  recording 0 findings.
- **Retry-phase rewind fixed** — `--retry-phase` now clears EVERY downstream phase
  via the canonical `PHASES` order (was hardcoded 0b–0e), incl. per-chapter ledgers;
  direct per-chapter retry still preserves completed slugs (watchdog recovery).
  Tests: `tests/test_retry_phase_clearing.py`, `tests/test_chapter_set_integrity.py`.

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
- **Wave-N authorial-apparatus noise (2026-06-23; expanded/hardened 2026-06-24)** — the denoise step historically stripped only OCR/translator/editor apparatus, never the author's own NON-teaching meta about the book-object (circulation/copyright notices, ijazat-to-record + treasury-deposit provenance, colophons). That class passed every filter and fanned into all four surfaces (book / chapters / episodes / slide-decks). The 2026-06-24 expansion adds `NZ-REFERENCE-TAIL`: bibliographic tails after wisdom/saying blockquotes in chapter prose, such as `in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam (Saying) 147`; the quote and speaker stay, the reference scaffolding is stripped. The hardening also adds front-matter/readership/book-description/author-bio/chain-of-narration/permission-to-read apparatus to the strip class and adds `R_PRESERVE_ARABIC_SOURCE_DIRECTIVE`: Arabic-script terms remain in chapter source for the Podcast Factory Astro Site Arabic/pronunciation review; the human later decides recite Arabic vs translate to English. Root fix: `R_NOISE_APPARATUS_CATEGORIES` / `_PROTECT` / `_PATTERNS` / `R_NOISE_APPARATUS_DIRECTIVE` / `strip_noise_reference_attributions` in [`_rules.py`](scripts/podcast/_rules.py), injected into `gemini_refine.DENOISE_SYS` + `full_book_denoise.build_system_prompts` (the latter also made book-agnostic — its prompts were hardcoded to "Ayyuhal Walad") and baked into Phase 0e via `strip_reference_attribution_noise.py`. PROTECT-list keeps doctrine (wilayah/allegiance, inherited-from-prophets epistemics), the quoted saying, and the speaker attribution. The identify-only [`noise-auditor`](infra/claude-agents/noise-auditor.md) sweeps all four surfaces, emits `NZ-*` findings to `_learning/findings.jsonl`, stamps `NOISE_AUDITOR_VERSION`. First incident + remediation: al-Anwaar al-Lateefah vol-01 ch01a opener; reference-tail expansion: al-Anwaar al-Lateefah vol-01 Nahj/Hikam saying references.
- **Host roles guardrail** — `HOST_ROLE_CONTRACT` dict (3 presets: teacher/student, teacher/questioner, scholar/debater) + `HOST_ROLE_CONTRACT_DEFAULT` in [`_rules.py`](scripts/podcast/_rules.py). 7th editorial card `host_roles` in the Studio cockpit.
- **Stage gate + runner** — [`_stage_gate.py`](scripts/podcast/_stage_gate.py) (review reader/writer) + [`stage_runner.py`](scripts/podcast/stage_runner.py) (CLI: check gate → run next WC8 stage producer). `--status` prints a per-chapter ✅/🔄/⬜ table.
- **Podcast bundle + slides** — [`assemble_bundle.py`](scripts/podcast/assemble_bundle.py) validates chapters/framings/slides, runs 5-axis PEQ inline, emits the mandatory NotebookLM upload table. [`generate_slide_decks.py`](scripts/podcast/generate_slide_decks.py) authors two-file slide pairs via Gemini 2.5 Flash (thinking disabled, maxOutputTokens=8000, trailing-whitespace strip). All 5 Ayyuhal slide decks produced.
- **Studio re-platform** — `/studio` page with `EditorialCards.tsx` (7 cards, @dnd-kit sortable drag-reorder on list cards, cmdk corpus search on Key Focus). `/intake` page (`NewContentForm.tsx`, `EditorialDefaults.tsx`, `api/intake/create.ts`). `save-stage.ts` API writes edits back to `_stages/<ch>/<stage>.md` with `.md.bak` backup.
- **Holistic pipeline gap identified** — WC8 `_stages/` normalized content (4,295w total) is NOT ready for podcast output. Arabic spine was never reconciled with English translations. New scripts planned: `full_book_denoise.py`, `reconcile_book.py`, `segment_book.py` (output to `chapters-wc8/`, ~4,500w per episode). Total new cost: ~$0.30.

## 2026-05-25 cleanup wave — what changed

A single-day cleanup arc closed ~28 pipeline-debt F-items, shipped the scholarly-conversation rubric v2.2, retired unused scaffolds (02/03/04), consolidated branches to one-per-active-book, and landed foundational layers for the multi-day F31/F32/F34 refactors. Operator-visible additions:

- **Phase 0g dual-auditor** ([orchestrate_book.py:phase_0g_audit_bundles](scripts/podcast/orchestrate_book.py)) runs `audit_bundle.py` + `audit_bundle_gemini.py` in parallel against every per-chapter NotebookLM bundle. Reports at `BOOK_DIR/audits/<EP-slug>.audit.{claude,gemini}.md`.
- **Scholarly-rubric v2.2** — [_rules.py:CHALLENGER_VERSION](scripts/podcast/_rules.py) bumped 2.1 → 2.2. Five new R-* rule families inlined into [_workspace/prompts/gemini-bundle-auditor.md §4](_workspace/prompts/gemini-bundle-auditor.md). Six matched fixtures at [_learning/fixtures/](_learning/fixtures/).
- **Per-chapter loop hardening** in [orchestrate_book.py:_drive_per_chapter_and_after](scripts/podcast/orchestrate_book.py): F33-second graceful-degrade (`failed_slugs` set; continue on failed chapter); F35-second `per_chapter_cost_cap_usd` series-plan flag (default $5); F37 `chapter_timings` per slug; F12 `_resolve_episode_id()` reads `contract.episode_number`.
- **Convergence robustness** — F11 preserves prior SHIP verdicts when later-iteration challenger times out ([_convergence.py](scripts/podcast/_convergence.py)).
- **Framing word-cap guard** — F1 compression re-author before build gate ([_authoring/_framing.py:author_framing](scripts/podcast/_authoring/_framing.py)).
- **Parallel windows** — F34-second [_chunking.py:run_windowed](scripts/podcast/_chunking.py) `max_workers` param; Phase 0b/0c default 3 (`PHASE_0B_MAX_WORKERS` / `PHASE_0C_MAX_WORKERS` env). ~3× wall-clock, cost-neutral.
- **Concurrency-safe ledgers** — fcntl LOCK_EX on findings.jsonl ([_rules.py:emit_finding](scripts/podcast/_rules.py)) + cost-ledger.jsonl ([_cost_ledger.py:append_cost_row](scripts/podcast/_cost_ledger.py)).
- **Azure cost tracking** — F36 `append_azure_{docintel,translator,speech}_cost` wired at ingest_source.py, translate_bundle.py, ocr_image_pages.py, transcribe_episode.py.
- **Cross-book dashboard** — [scripts/podcast/cross_book_dashboard.py](scripts/podcast/cross_book_dashboard.py) fleet-level phase/status/cost/timing table. `--since 7d --json --out` supported.
- **Rule-firing telemetry** — `learn_aggregate.py --by-check-id --since <window>` top-50 ranked histogram. Forward-looking `bypassed_gate` field on emit_finding.
- **Scaffold retirement** — F30 bundle shape now: chapter source + `00-framing.md` + `99-show-notes.md`. 02/03/04 stubs no longer emitted.
- **Tradition-pack registry** — F31 `_doctrinal.py:tradition_pack_dir / load_doctrinal_pack`; build gate skips with `T-NO-PACK` info when no pack exists for the book's `source_tradition`.
- **Episode-format enum** — F32 2 → 7 values; `EPISODE_FORMAT_FULLY_WIRED = (deep_dive, debate)` distinguishes tested from new entries.
- **Editorial-frontmatter exclusion + thesis_relevance** — F4 + F23 Phase 0d author prompt EXCLUDES editor's intros / translator's prefaces from the episode array; each contract requires `thesis_relevance` field.

For the line-by-line F-item map see [_workspace/plan/debt/pipeline-debt.md](_workspace/plan/debt/pipeline-debt.md).

---

