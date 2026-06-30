# Pipeline and Site Manifest Audit, 2026-06-30

Scope: git history from 2026-06-10 through 2026-06-30 across `scripts/podcast/`, `plan-dashboard/`, `framework.md`, `skills-staging/`, `infra/claude-agents/`, `.github/agents/`, `docs/`, and `_workspace/plan/`.

Branch audited: `codex/fix-translation-edition-book-quality`

## At a Glance

- Current state is a multi-route pipeline: podcast source production, NotebookLM/audio ingest, the augmented companion PDF route, and the articulated translation PDF route.
- The Podcast Factory Astro Site passed the HTML view lint gate and production build.
- The podcast Python test suite passed when run with repo-root `PYTHONPATH`, which is required by tests that import `scripts.podcast...` as a package namespace.
- Two spec drifts were found and fixed: framework/skill docs still described B1-B3 book gates, and `book-challenger` only described the augmented companion-book route.

## Recent Work Manifest

### 2026-06-10 to 2026-06-11: Density, slides, and reading-edition hardening

- Added autonomous slide-deck weave, book folder skeleton, book-level single-deck mode, and slide intelligence with OCR/vision analysis.
- Locked chapter-density standards, topic floor, concept inventory, and retry-phase downstream clearing.
- Added session grouping, per-session Drive delivery folders, and the NotebookLM upload table/session reader grouping.
- Raised book-compose and book-illustrate timeouts to match real chapter budgets.
- Added Amiri and Amiri Quran fonts, PDF review punch-list fixes, book-cover tests, and a two-surface pipeline plus Astro audit.

### 2026-06-12 to 2026-06-14: Audio v2 and NotebookLM default

- Added pluggable audio-engine registry, dialogue scripts, script gates, production rendering, pronunciation dictionaries, voice library, and Studio engine/credit display.
- Added NotebookLM normalization and Azure transcription for dropped audio, then restored NotebookLM as the default for Islamic scholarly content while quarantining ElevenLabs.
- Added deterministic Quran recitation scaffolding for the ElevenLabs path and glossary v2 human curation.
- Added `audio-ingest`, durable NotebookLM worklists, mp3 transcode delivery, and Drive-aware publishing errors.
- Added challenger coverage for BK-P6 prose craft and podcast CS7-CS11 set checks.

### 2026-06-15 to 2026-06-17: Studio cockpit, Arabic review, and source preservation

- Added Studio redesign surfaces: hub, series deck, in-site reader, audio player, editable metadata, command palette, guarded slug rename, per-halt review cockpit, draft retention, Explain action, action-item queue, and global find-and-replace.
- Added Arabic review and curation flows: review page, term suggestions, editable Arabic term replacement, one-click accept, raw Arabic accent color, duplicate key fixes, and phonetic/script identity matching.
- Fixed source pipeline issues: audio source rejoins the canonical path at 0b, 0f tolerates mixed `length_target` types, contract auto-repair at 0d, and word-count-aware TOC timeouts.
- Added Arabic preservation and integrity features: glossary field repair, canonical Quran Arabic atoms, verified-model Arabic, Arabic integrity gates, and terminology preservation.
- Added multi-source synthesis, cross-chapter doctrine de-duplication, and concise heading rules.

### 2026-06-17 to 2026-06-24: Allocator, corpus, architecture pages, and audits

- Added six-volume Al Anwaar scaffolding, work-level teaching allocator, `episode_max_concepts`, volume composite slug resolution, TOC `end_line` clamping, and cross-episode reference guards.
- Added corpus collision-aware merge rebuild, unique-id shrink guards, and snapshot idempotence.
- Updated the Podcast Factory Astro Site architecture page diagrams with build-time rendered diagrams and enforced the REQ-010 reading-text floor.
- Routed Approve, Studio editorial, and intake through the canonical content resolver.
- Restored pipeline tests, cleared dependency advisories, stripped authorial-apparatus noise, and fixed Mermaid mindmap multi-root render failures.

### 2026-06-27 to 2026-06-30: Arabic recitation and translation edition

- Added Arabic recitation path support.
- Reconciled digital-twin governance findings and synced challenger activation copies.
- Added the `translation_edition` pipeline path.
- Added source-aligned translation-edition gates: prose integrity, body coverage, source crosswalk, title/source drift detection, crosswalk-aware PDF rendering, table of contents, source crosswalk page, page numbers, and AI-disclaimer panel.

## Current Route Specifications

### Podcast path

- Source: `chapters/chNN-<slug>.txt`, in author voice.
- Output: NotebookLM upload bundle and audio/transcript flow.
- Gates: `podcast-challenger`, `slide-deck-challenger`, and `validate_ship_ready.py` G1-G13.
- Boundary: `book/` artifacts never feed NotebookLM.

### Augmented companion PDF route

- Trigger: `series.enable_book_branch: true` without `deliverable_mode: translation_edition`.
- Driver: `scripts/podcast/phases/book_driver.py`.
- Flow: `0book-design -> 0book-compose -> 0book-illustrate -> 0book-slide-import -> 0book-render`.
- Intent: revoice approved podcast/source material into a modern companion reading edition, with source-grounded Arabic scripture, prose craft, diagrams, and optional slide-deck weave.
- Challenger: `book-challenger` full augmented-companion catalog, including no-teaching-lost, Arabic-script accuracy, faithfulness against addition, voice consistency, segmentation sanity, and prose craft.
- Deterministic book gates: B1-B3 always apply; B4-B6 are translation-edition specific and report `n/a`.

### Articulated translation PDF route

- Trigger: `_system/series-config.yaml` has `deliverable_mode: translation_edition`.
- Drivers: `scripts/podcast/generate_translation_edition.py` and `scripts/podcast/phases/book_driver.py`.
- Flow: `0a ingest -> 0b refine -> 0book-design -> translation compose -> 0book-illustrate -> book-level slide pair -> 0book-render`.
- Intent: faithful translation/articulation of the supplied non-English source, with denoising and readability improvements only.
- Required policy: `translation_policy.augmentation` is `forbidden`, `none`, or `source_only`; `preserve_arabic_terms` remains true; visuals are black-white/monochrome.
- Required artifact: `book/source-crosswalk.json` with chapter index/title, source line ranges, source pages, Arabic source pages, source headings/excerpt, and title/source drift findings.
- Challenger: `book-challenger` translation-edition reinterpretation of the probe catalog: no-source-lost, quotation/source survival, source-grounded Arabic accuracy, no outside-source addition, dignified translation voice, source-crosswalk segmentation sanity.
- Deterministic book gates: B1-B6 all apply. `generate_translation_edition.py` treats `BOOK-BROKEN` as a hard failure because the PDF is the product.

## Audit Findings and Fixes Applied

### Finding A1: Book-gate spec drift

- Evidence: `framework.md` still said the reading-edition deliverable was gated by B1-B3.
- Current code: `validate_book_ready.py` runs B1-B6.
- Fix: updated `framework.md` and `skills-staging/podcast/SKILL.md` to document B1-B6 and route-specific behavior.
- Fix: updated `validate_book_ready.py` function docstring from B1-B3 to B1-B6.

### Finding A2: Book challenger route drift

- Evidence: `book-challenger` only described the augmented companion reading edition and did not know `deliverable_mode: translation_edition`.
- Fix: updated `infra/claude-agents/book-challenger.md` with route classification, required translation-edition artifacts, and route-specific probe reinterpretations.
- Fix: synced `.github/agents/book-challenger.agent.md` and `.claude/agents/book-challenger.md` from canonical infra spec.

### Finding A3: Root local artifact clutter

- Evidence: ignored local `.DS_Store`, `.pytest_cache/`, and `plan-dashboard/dist/` were present after test/build runs.
- Fix: removed those generated local artifacts. Kept `.claude/agents/` because `scripts/podcast/sync-agent-wrappers.sh` intentionally writes runtime activation copies there.

### Finding A4: Python test invocation needs repo-root package path

- Evidence: `pytest scripts/podcast/tests` failed collection on `test_augmenter.py` with `ModuleNotFoundError: No module named 'scripts'`.
- Resolution: rerunning with `PYTHONPATH=/Users/ahmac/Code/podcast-factory` passed all tests. This is an invocation/environment note, not a product-code failure.

## Verification

- `source .venv/bin/activate && PYTHONPATH=/Users/ahmac/Code/podcast-factory pytest scripts/podcast/tests`: 1156 passed.
- `source .venv/bin/activate && pytest scripts/podcast/tests/test_translation_edition.py scripts/podcast/tests/test_validate_book_ready.py`: 36 passed.
- `cd plan-dashboard && npm run lint:views`: clean, 0 errors, 0 warnings.
- `cd plan-dashboard && npm run build`: complete.
- `scripts/podcast/sync-agent-wrappers.sh --check`: all wrappers in sync.
- `_workspace/plan/refactor/plan.yaml`: parses with PyYAML and Ruby YAML.
- Static audit scans: no unguarded `console.log`/`console.debug` found in `plan-dashboard/src`; no hardcoded `/Users/` or `/home/` found in `scripts/podcast`, `plan-dashboard/src`, or `plan-dashboard/scripts`.

## Residual Notes

- The repo-surgeon root allow-list in `skills-staging/repo-surgeon/SKILL.md` is stale for this split-era repo because it omits legitimate current root entries such as `plan-dashboard/`, `AGENTS.md`, `CLAUDE.md`, `requirements.txt`, `pytest.ini`, `tests/`, and `tools/`. I treated it as historical guidance and audited against actual tracked repo structure instead of moving legitimate files.
- The older static capability manifest at `docs/assessment/capability-manifest-2026-06-20.md` remains a dated snapshot, not the current route contract.
