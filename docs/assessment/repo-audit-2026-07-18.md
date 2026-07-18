# Full Repo Audit — 2026-07-18

*Two-surface audit: the podcast-factory pipeline (`scripts/podcast/`, ~100k LOC across 404 Python files) and the Podcast Factory Astro Site (`plan-dashboard/`, ~37k LOC across 228 TS/Astro files).*
*Method: repo-audit skill phase discipline (orientation → digital twin → verification → findings → challenge → approval gate). Five parallel read-only investigators + direct spot-verification of every high-consequence claim.*
*Status: **IDENTIFY-ONLY. AWAITING APPROVAL before any change.***
*Branch: `develop` (clean working tree). Generated 5:38 AM EST.*

---

## At a glance

The repo is in genuinely good health. The build is green, the working tree is clean, the Python test suite collects **1,593 tests with zero errors**, `.gitignore` is disciplined, and there are only 14 TODO markers (most of which are intentional placeholder-detection logic, not aging debt). No P0 (nothing broken, no active security breach, no data-loss path).

The debt that exists is concentrated in three places: **(1)** a large, cleanly-severable dead surface on the Astro site (the superseded chapter-reader UI) plus a scatter of retired pipeline modules; **(2)** two genuine correctness/hygiene defects (a reader PEQ score that always reports full Fidelity, and a local DB password committed to source); and **(3)** edge-of-repo drift (a stale fourth agent-registry that breaks on a fresh machine, a one-sided TS↔Python mirror, and a handful of docs still on the retired `content/drafts/` layout).

Two prior-audit items remain open: the plaintext DB password (2026-05-30 A1) and the missing Gemini retry/backoff (2026-05-30 A3). The third (missing search mirror DB, A2) is resolved.

---

## What's healthy (verified, listed so it isn't re-litigated)

- **Test collection clean** — 127 test files, 1,593 tests, 0 collection errors (`pytest --collect-only`). No test imports a deleted module.
- **No Python god-modules** — nothing exceeds the ~1,500-line threshold; the largest (`_authoring/_chapter_design.py` 1,329, `_rules.py` 1,047) do legitimately broad jobs.
- **PEQ scoring core in sync** — weights, thresholds, voice flag, all `R_INTEREST_*` patterns and extraction regexes match between `peq-scores.ts` and `_quality.py`/`intelligence/challenger_scoring.py` (the *Fidelity input* is the sole divergence — see R2).
- **Agent mirror disciplined** — `.github/agents/*.agent.md` is byte-identical to canonical `infra/claude-agents/` for all 22 shared specs.
- **Snapshots in sync** — all three dashboard snapshots were regenerated in the same commit that last touched their sources; `.snapshot-version` current.
- **Cortex lint gate green** — zero inline `style=`, zero external-SVG refs, zero sized `<svg>`, zero quoted inline handlers in gate scope; the 5 remaining inline styles are the sanctioned floating-UI/CSS-custom-property patterns in excluded paths.
- **`framework.md` clean** — zero stale `content/drafts`/`branch_prefix`/`server/`/`site/` references. All retired dirs confirmed absent on disk.
- **Debris posture clean** — only one tracked debris file (a `translation-run.log`); dev logs, `dist/`, `.astro/`, `.DS_Store`, `.venv/`, `node_modules/` all correctly untracked/ignored.

---

## Risk register (severity-sorted)

| ID | Sev | Surface | Finding | Evidence | Fit |
|---|---|---|---|---|---|
| R1 | P1 | Pipeline | Plaintext local DB password committed (now in **two** files) | `tools/source_extractor/db.py:11`, `_pull_ksessions.py:18` = `Kashkole_Local_2026!` | Accept |
| R2 | P1 | Site | Reader PEQ **Fidelity axis always = 100** — passes an empty source list | `peq-scores.ts:265,315` call `fidelityScore([], …)`; Python computes real Jaccard at `challenger_scoring.py:158` | Accept |
| R3 | P2 | Site | **23-file dead island** (old chapter-reader UI) + **12-file orphaned lib subtree** behind it (~2,500+ lines) | `components/reader/ChapterEditor.tsx` (797 ln) + cluster; unreachable from any route; 0 JSX importers | Accept (w/ caveat) |
| R4 | P2 | Pipeline | **Wave-execution engine (~30 modules) appears spent** — shares `phases/` with book drivers, two meanings of "phase" collide | `run_wave.py`, `phases/p1_1..p6_2`, `pw*`, `_acceptance.py`, `_view_updater.py`; waves 1–6 shipped per `refactor/plan.md` | Flag |
| R5 | P2 | Cross | **`.codex/hooks.json` breaks on every machine** — hardcoded foreign path `/Users/ahmac/Code/podcast-factory/...`; referenced scripts not in repo | `.codex/hooks.json` (all 4 hook commands); `.codex/hooks/` dir absent | Accept |
| R6 | P2 | Pipeline | **6 confirmed dead pipeline modules** | `phases/register_series.py`, `phases/{p24_1,p25_1,p25_7}.py`, `_augment_gemini.py`, `import_transcript.py`, `book_cost.py` — all zero code callers | Accept |
| R7 | P2 | Pipeline | **Dead WC8 staging trio** (never wired) + name-collision hazard | `stage_runner.py`+`intake_stage.py`+`_stage_gate.py`; `intake_stage.py` vs live `intake_staging.py` | Accept |
| R8 | P2 | Site | **6 uncalled API endpoints** + their exclusive helpers | `api/ai/ask-chapter.ts`, `api/annotations/{export,tags}.ts`, `api/corpus/atoms.ts`, `api/quran/etymology.ts`, `api/wisdom/search.ts` | Accept |
| R9 | P2 | Site | **`StudioPoc.tsx` — 3,051-line God component** shipping from a `poc/` dir as the production editor (134 hooks) | `components/reader/poc/StudioPoc.tsx`; imported by `studio/[slug]/[step].astro:15` | Flag |
| R10 | P2 | Site | **"poc"/"mock" naming on live production code** | `components/reader/poc/` (4 live files), `components/corpus-mock/` (renders live knowledge.db) | Accept |
| R11 | P2 | Cross | **`editorial.ts` mirror is one-sided** — claims a Python reader that doesn't exist | `editorial.ts:10` docstring vs zero `_system/editorial/` readers in `scripts/**/*.py` | Flag |
| R12 | P2 | Cross | **`docs-updater` agent has no tracked spec anywhere** — a fresh clone can't reproduce it | `git ls-files | grep docs-updater` → empty; exists only as gitignored `.claude/agents/docs-updater.md` | Accept |
| R13 | P2 | Cross | **`.codex/agents/` is a stale, undocumented 4th registry** — missing 4 canonical agents | `.codex/agents/*.toml` (18 files); no sync process; missing `book-render-challenger`, `noise-auditor`, `preview-fidelity-challenger`, `site-health-sentinel` | Accept |
| R14 | P2 | Site | **Two parallel live markdown renderers** + **no shared HTTP client** (88 raw `fetch()` across 29 files) | `markdown.ts:50` vs `source-render.ts:86`; `grep fetch(` = 88 | Flag |
| R15 | P2 | Cross | **`.mcp.json` is both tracked AND gitignored** with a false rationale | `git ls-files .mcp.json` = 1; `.gitignore:25` ignores it "contains API tokens" (it doesn't) | Accept |
| R16 | P2 | Cross | **`ALLOWED_CATEGORIES` enum drift** — TS 7 vs Python 9 | `content-paths.ts:49` (7) vs `_rules.py:227` (adds `sites`, `explainers`) | Accept |
| R17 | P2 | Pipeline | **Zero test coverage on live quality-critical modules** | `_citation_verify.py`, `score_pronunciation_risk.py`, `mcp_access.py`, `build_probe_bundle.py`, `pronunciation_ledger.py`/`_patterns.py` | Accept |
| R18 | P2 | Cross | **`docs/runbooks/watchdog.md` gives a runnable command on the retired layout** | `:11` `bash ... content/drafts/my-book-slug`; `content/drafts/` gone | Accept |
| R19 | P2 | Pipeline | **Dead-but-orphaned probe/knowledge modules** | `probe/fill_probe_meanings.py` (0 refs), `knowledge/augmenter.py` (abandoned JSONL, doc'd as "fallback" but unwired), `slides/classify_slides.py` (games its own gate by file-presence) | Accept |
| R20 | P2 | Site | **`SpendChart.tsx` never imported** (comment-only references) | `grep SpendChart` → only 2 comment mentions | Accept |
| R21 | P2 | Site | **95KB `studio-poc.css` is load-bearing but "-poc"-named**; `theme.css` 3,167 ln | imported by `studio/[slug]/[step].astro:26` | Accept |
| R22 | P2 | Pipeline | **Gemini refine path has no retry/backoff** (Azure path does) — carries forward 2026-05-30 A3 | `gemini_refine.py:179` bare `urlopen`, no 429 handling | Flag (confirm live path first) |
| R23 | P3 | Cross | **`content/drafts/` doc references** in ~6 tracked docs + 2 code docstrings (resolve correctly at runtime) | `claude-code-bootstrap-prompt.md:122`, `house-voice.md:61`, `transcription-runbook.md:39`, `clean-commit/.../folder-rules.md`, `tools/source_extractor/README.md:76`, `_stage_gate.py:8`, `stage-review.ts:8` | Accept |
| R24 | P3 | Pipeline | **Cutover residue** — stale `book_pipeline_v2`-flag comments in ~6 files; unconsumed `book-illustrated.md` artifact still written | `_book_compose.py:4`, `_book_render_checks.py:10`, `_book_augment.py:3`, `_book_voice.py:3`, `build_book_pdf._pick_book_md:92` | Accept |
| R25 | P3 | Pipeline | **Config/docstring drift** | `requirements.txt` `Pygments` unused; `knowledge/__init__.py` docstring describes deleted modules + false `NotImplementedError` claim; `Makefile` header says "journal repo" + retired proxy; `pydantic` comment stale | Accept |
| R26 | P3 | Site | **Business logic in `.astro` frontmatter** + book-specific data hardcoded in a shared lib | `studio/[slug]/index.astro` (186 ln frontmatter); `book-workspace.ts:58-60` hardcodes `ayyuhal-walad` (also dead) | Accept |
| R27 | P3 | Both | **Long-tail advisories** — dead exports (`renderProse`, `AYYUHAL_WALAD_*`); regex drift (`all[aā]h` vs `allāh`); tracked 30MB `mirror.db` (intentional, rebuildable); stray `.claude/worktrees/` copy; tracked `translation-run.log`; `infra/_README.md` count says 20/lists 19/22 exist | see detail below | Accept |

---

## Detail by category

### Correctness & security (R1, R2, R22)

**R1 — Plaintext local DB password.** `PASSWORD = "Kashkole_Local_2026!"` is committed in `tools/source_extractor/db.py:11` and `tools/source_extractor/_pull_ksessions.py:18`, used as `sqlcmd -S localhost -U sa -P`. Real-world exploitability is low — it's a *localhost* dev-container `sa` password, not a cloud/production secret, and the container is rebuilt from local dumps — but it sits in git history and the repo's own 2026-05-30 audit (A1) already flagged it as critical and prescribed the keychain pattern (`security find-generic-password -s wisdom-mssql -w`, same as `gemini_api_key`). It was never remediated and has since spread to a second file. **Action:** move to keychain via a `keychain_get()` helper; update both callers.

**R2 — Reader PEQ Fidelity always 100.** `peq-scores.ts` is live (imported by `lib/library.ts` and `studio/[slug]/index.astro`). Both scoring call-sites — `:265` and `:315` — invoke `fidelityScore([], citationsFound)` with an empty source-citation list, so `fidelityScore` returns full credit unconditionally. The Python path computes a real Jaccard overlap from the chapter's contract citations (`challenger_scoring.py:158` via `_extract_citations`). The reader-recomputed PEQ therefore reports Fidelity=100 where the pipeline may report lower — two "PEQ" numbers that legitimately disagree. **Action:** either load contract citations on the TS side, or (if this is a deliberate display simplification) document it in the file header and label the reader's Fidelity as "not recomputed."

**R22 — Gemini refine has no retry.** `gemini_refine.py:179` is a bare `urllib.request.urlopen` with no 429/500 backoff, unlike the Azure path. Carries forward 2026-05-30 A3. **Action:** confirm `gemini_refine.py` is still on a live path, then add the same exponential-backoff helper the Azure client uses. (Flagged: verify liveness first — it may be superseded by `gemini_chat.py`.)

### Dead code — the severable surfaces (R3, R6, R7, R8, R19, R20)

**R3 — the big one.** A single closed island of 23 Astro-site files (the superseded chapter-reader UI: `ChapterEditor.tsx` 797 ln, plus `ChapterInstructionPanel`, `ReaderControls`, `ReaderSettings`, `FloatingActions`, `Legend`, `QuranPopover`, `TopicPopover`, `ArabicToggle`, `ContractView.astro`) is unreachable from any page/API route — they only reference each other. Behind them sits a 12-file orphaned lib subtree (`contract-parser.ts`, `contract-render.ts`, `render-prose.ts`, `highlight-renderer.ts`, the `ref-categories/` registry, `arabic-terms.ts`, `reader-settings.ts`, `storage-keys.ts`). **Deletion caveat (verified):** a *live* `ChapterEditor` interface and `mountChapterEditor()` exist in `scripts/book-md-editor.ts` and are used by `book-composer.ts` — that's a name reuse, not the dead component. Delete the `.tsx` cluster + lib subtree as one unit; keep the interface.

**R6/R7 — dead pipeline modules.** Confirmed zero-caller (evidence = unrestricted whole-repo greps incl. `.ts`/`.astro`/`Makefile`): `phases/register_series.py` (its `phase_0g_register` is a stale duplicate of the one in `series_plan.py` that the orchestrator actually imports); `phases/{p24_1,p25_1,p25_7}.py` (orphaned Wave-24/25 runners not in the REGISTRY); `_augment_gemini.py` (self-declared unwired stub); `import_transcript.py` (self-described workaround, 0 refs); `book_cost.py` (duplicates `cost_ledger_summary.py`, 0 refs). Plus the WC8 staging trio `stage_runner.py`+`intake_stage.py`+`_stage_gate.py` (never wired; also removes the `intake_stage.py`↔`intake_staging.py` collision trap).

**R8 — dead site endpoints.** 6 API routes with zero `fetch`/reference callers: `api/ai/ask-chapter.ts`, `api/annotations/export.ts` (+ exclusive helper `annotation-export.ts`), `api/annotations/tags.ts` (+ `annotations.ts` tag helpers), `api/corpus/atoms.ts` (page loads atoms server-side instead), `api/quran/etymology.ts` (+ `fetchLocalEtymology`), `api/wisdom/search.ts` (page searches client-side).

**R19/R20 — orphaned helpers.** `probe/fill_probe_meanings.py` (0 refs repo-wide), `knowledge/augmenter.py` (abandoned JSONL augmenter documented as a "fallback" that is not actually wired — the DB-backed `intelligence/augmenter.py` is the live path), `slides/classify_slides.py` (never executed — `phases/p3_4.py` uses it only as a file-existence marker, so it games its own gate), and `SpendChart.tsx` (comment-only references).

### Structural debt (R4, R9, R10, R14, R21, R26)

**R4 — wave-execution engine.** ~30 modules exist only to drive refactor-plan waves 1–6, whose deliverables have shipped. They share the `phases/` directory with the unrelated book-pipeline drivers (two meanings of "phase" in one folder), and this is where the p24/p25 orphans accumulated. Still tested and launchd-installable, so blast radius is large but inert. **Owner decision:** archive into its own package, or confirm retired and delete wholesale.

**R9 — StudioPoc God component.** 3,051 lines, 134 `useState`/`useEffect`/`useRef`/`useCallback`, 33 top-level declarations, in one file — the actual production studio editor, shipped from a `poc/` directory. It's the most-churned site surface. **Action:** promote out of `poc/`, then split by concern (annotation state, ask/rewrite, transformation dashboard, term popovers).

**R10 — misleading names on live code.** `components/reader/poc/` (4 live files wired into the studio editor) and `components/corpus-mock/` + `data/corpus-mock-sample.ts` (renders live knowledge.db; the sample is fallback only) both signal "throwaway" while being production. **Action:** rename `poc/` → `studio/editor/`, `corpus-mock/` → `corpus/`, `corpus-mock-sample.ts` → `corpus-fallback.ts`, patch imports.

**R14 — duplication.** Two live markdown→HTML renderers (`markdown.ts:50` `renderMarkdown` vs `source-render.ts:86` `renderSourceMarkdown`) — consolidate or document why prose vs source must diverge. No shared client HTTP wrapper — 88 raw `fetch()` calls across 29 files each re-implement URL/error/JSON handling; extract a small `apiFetch(path, init)`.

### Cross-cutting drift (R5, R11, R12, R13, R15, R16, R18, R23, R25)

**R5 — `.codex/hooks.json` broken.** All four hook commands hardcode `/Users/ahmac/Code/podcast-factory/.codex/hooks/*.sh` — a foreign user and layout; the `.codex/hooks/` dir isn't even in the repo. Contradicts the machine-agnostic principle; silently no-ops on every real machine. **Action:** make repo-relative and commit the scripts, or delete the dead hook config.

**R11 — one-sided `editorial.ts` mirror.** Its docstring (`:10`) claims "the Slice-6 Python orchestrator reads the same files," but no Python file reads `_system/editorial/`. The 7 `CardId`s have zero Python consumers. **Flag:** either build the Python reader, or correct the docstring and drop `editorial.ts` from the CLAUDE.md/AGENTS.md mirror-pair contract (it's Studio-only state).

**R12/R13 — agent registry gaps.** `docs-updater` is a runnable agent with no tracked spec (add `infra/claude-agents/docs-updater.md` + `.github` mirror). `.codex/agents/` is an undocumented 4th full copy of every spec with no sync process, missing 4 canonical agents. **Action:** generate `.codex/agents/` from `infra/` like `install-claude-skills.sh` does for `.claude/`, or document + backfill. Also `infra/claude-agents/_README.md` says "20 agents," lists 19, and 22 spec files exist — regenerate the table from the directory.

**R15 — `.mcp.json` contradiction.** Tracked and committed, yet `.gitignore:25` ignores it as "contains API tokens" — it's a token-free stub (bluedot HTTP URL only); OAuth is per-machine via `/mcp`. The ignore rule is inert and its rationale wrong. **Action:** remove the `.gitignore:25` line.

**R16 — enum drift.** `content-paths.ts:49` lists 7 categories; `_rules.py:227` lists 9 (adds `sites`, `explainers`). Low runtime impact (used only in the now-empty legacy fallback scan) but a confirmable inconsistency under the mirror contract. **Action:** add `'sites'`, `'explainers'` to the TS array.

### Test & config (R17, R25)

**R17 — untested live modules.** `_citation_verify.py` (citation authenticity, used by `phases/p3_3.py`) and `score_pronunciation_risk.py` (drives the probe bundle) are the highest-correctness-risk untested modules — cover those first. Also untested: `mcp_access.py`, `build_probe_bundle.py`, `pronunciation_ledger.py`/`_patterns.py`.

**R25 — config/docstring drift.** `Pygments==2.20.0` in `requirements.txt` is imported nowhere; `knowledge/__init__.py` docstring still describes `extractor`+`librarian` (deleted 2026-06-10) and falsely claims all modules raise `NotImplementedError`; the `Makefile` header references "the journal repo" and a retired Express proxy (targets themselves are all valid); the `pydantic` requirements comment is inaccurate.

---

## Capability manifest (condensed)

**Pipeline** — two backbones share `phases/`: the **book orchestrator** (preflight→0a→0f halt→per-chapter→publish→merge, `orchestrate_book.py` + `phases/*_driver.py`, verified, clean A4 split, no circular imports) and the **wave-execution engine** (R4, spent). Live domains: 0a Azure ingest, 0b–0e LLM authoring (`_authoring/` pkg), per-chapter convergence, episode bundle build, slide decks, **Book Pipeline v2** (unified compose→augment→voice→illustrate→render, canonical render `build_book_pdf.py`, v2 cutover runtime-clean), video layer, Audio Engine v2 (dormant per manifest), post-prod transcription, publish/ship (G1–G7), the Astro-wired intake cockpit, cost tracking, source-library SQLite, learning loop, doctrinal validators, cross-book ops. Intelligence subsystem: DB-backed augmenter is the **live** augment path (`phases/per_chapter.py:191`); the extractor's public API is built+tested but **not wired** (phase-0h/`podcast-librarian` never invoked).

**Site** — ~28 page routes, 61 API endpoints (55 live, 6 dead per R8), major domains: studio (compose/edit/halts, editor core in the mislabeled `poc/`), reader libs (migrated into studio, live) vs old reader components (the R3 dead island), intake, corpus (live over knowledge.db, mislabeled "mock"), companion/gems, plan/architecture (snapshot-driven), workbench. Runtime dependency risk: four AI features (`quran/verse`, `ai/define-term`, `ai/etymology`, `wisdom/topic`) silently return null if the local `source_library_server.py` (`localhost:4390`) isn't running.

---

## Suspected — do NOT act without owner confirmation

- `_etymology.py` — built, tested, actively touched 2026-07-17, but no non-test importer. Reads as built-but-not-yet-wired WIP, not dead.
- `phases/noise_router.py` — real CLI + full tests, but not invoked in any automated phase (plan claims it "landed"). Manual CLI or unwired capability.
- `validate_registry.py` — its only non-test reference is inside the dead `register_series.py`. Verify it's still run manually before trusting it.
- ~20 manual/one-off CLIs with zero code callers that are **intentional operator tools** (self-labeled) — e.g. `render_sample_preview.py`, `segment_book.py`, `ab_compare_episode.py`, book-specific splitters. Flag, don't auto-delete.
- The corpus-build CLI chain (`populate_corpus` + `ingest_*`, `categorize_atoms`, `fill_etymology_phonetics`) — valid entry points, some tested, but may be de-facto superseded by `corpus_sync` JSONL rebuilds. Not dead; workflow-status unverified.

---

## Recommended execution order (when approved)

Per repo-audit Phase 6 ordering (debris → moves → renames → refactor → fixes), and batched so each group is independently shippable with its own regression check:

1. **Correctness & security** (R1, R2; confirm+R22) — smallest, highest-value; keychain migration + PEQ Fidelity reconcile.
2. **Dead-code sweep** (R3, R6, R7, R8, R19, R20) — delete the severable surfaces; patch references first; run `astro check` + `lint:views` + `pytest --collect-only` after.
3. **Edge-of-repo drift** (R5, R11, R12, R13, R15, R16, R18, R23, R25) — mostly one-liners and doc sweeps; low risk.
4. **Renames off misleading names** (R10, R21) — `poc/`→editor, `corpus-mock/`→corpus, `-poc.css`; reference-patch heavy, do as its own commit.
5. **Structural** (R9, R14, R26) + **test coverage** (R17) — larger refactors, one at a time with verification.
6. **Owner-decision flags** (R4 wave engine; R9 approach) — discuss before touching.

Nothing in groups 1–4 introduces a new abstraction or convention; all are deletions, renames, doc edits, or a single-line correctness fix. Group 5 is where judgment and staged review apply.

---

## Execution log — 2026-07-18 (option A: groups 1–3 approved)

Three focused commits landed on `develop`. Gates run per group: `astro check` (0 errors, 212 files), `npm run lint:views` (clean), `pytest --collect-only` (1,593 tests, 0 errors), and a full `pytest` run (1,591 passed, 1 skipped, 1 pre-existing failure — see below).

**Group 1 — correctness & security** (`b42e700`)
- **R1 DONE.** Local MSSQL `sa` password removed from `db.py` + `_pull_ksessions.py`; read from `MSSQL_SA_PASSWORD` at call time; key added to `.env.example`. Used the repo's env-var tier (`_secrets.py`), NOT keychain — the keychain tier was retired 2026-06-04, so the 2026-05-30 audit's keychain advice is stale. *The value remains in git history — rotating the local sa password is a separate operator step.*
- **R2 REJECTED (not a defect).** `peq-scores.ts` faithfully mirrors `_quality._fidelity_score` — BOTH sides return Fidelity=100 when no source-citation target is supplied, and Python's `score()` defaults `citation_ids_source` to empty exactly as the reader does. The investigator compared against the wrong reference (`challenger_scoring.py`, the heavy challenger). Changing the TS side would break the documented mirror. Left untouched.

**Group 2 — dead-code sweep** (`fa328d9`, 38 files)
- **R3 / R8 / R20 DONE (30 site files).** The chapter-reader dead island (10 components + 12-file lib subtree incl. the `ref-categories` registry), 6 uncalled API endpoints, `SpendChart.tsx`. The live `ChapterEditor` *interface* in `book-md-editor.ts` (name reuse) was retained. `QuranPopover`/`TopicPopover` verified dead (comment-only refs); `TermPopover` kept (live).
- **R6 DONE + R19 partial (8 pipeline files).** `register_series.py`, `p24_1/p25_1/p25_7.py`, `_augment_gemini.py`, `import_transcript.py`, `book_cost.py`, `probe/fill_probe_meanings.py`.
- **R7 DEFERRED.** The WC8 staging trio (`stage_runner`/`intake_stage`/`_stage_gate`) is NOT cleanly dead: `_stage_gate.STAGE_ORDER` is the canonical mirror source for the live site's stage-order (`book-workspace.ts`/`stage-roles.ts` both declare "MIRROR of Python `_stage_gate.STAGE_ORDER` … keep in sync"), and `.vscode` has a run-task for `intake_stage.py`. Untangling the canonical stage-order is a judgment call.
- **R19 DEFERRED (2 items).** `knowledge/augmenter.py` — documented as a fallback and has a *passing* test (`test_augmenter.py` imports it directly, contrary to the investigator's note); deleting it means deleting a green test. `slides/classify_slides.py` — referenced by wave-registry phase `p3_4`; couple to the R4 wave-engine decision.

**Group 3 — edge-of-repo drift** (`b606936`)
- **DONE:** R15 (`.mcp.json` gitignore rule removed), R16 (`content-paths.ts` `sites`+`explainers` added — plus their `categoryLabel`/`categoryPlural` cases, which the addition correctly exposed as an exhaustiveness gap), R11 (`editorial.ts` docstring corrected), R25 (`Pygments` dropped, `pydantic` + `knowledge/__init__.py` + `Makefile` header fixed), R18 + R23 (retired `content/drafts/` path references swept across 7 docs/tools; historical changelog entries left intact).
- **R5 / R12 / R13 DEFERRED.** `.codex/hooks.json` foreign-path breakage, `.codex/agents` backfill + `infra/_README` count, and the untracked `docs-updater` canonical spec — all multi-tree agent-registry work (destructive/generative), better done deliberately than autonomously.

**NEW finding — R28 (P1, runtime, out of scope):** `scripts/podcast/tests/test_etymology.py::test_build_pipeline_keeps_only_gated` **fails on `develop`** — `build_etymology_atoms` returns `kept=0` where the test expects `kept=1` (the confirmed atom `nafs` should survive while the unconfirmed `salaam` is dropped; instead both are dropped). Verified **pre-existing** — it fails identically at `82bcc56` (before this audit), and no audit change touched `_etymology.py` or its deps. Static collection-only checks missed it. In the recently-shipped etymology feature (active work) — surfaced, not fixed.

**Still open from the register (not in the approved batch):** R4 (wave engine, owner decision), R9/R14/R26 (structural refactors), R10/R21 (renames), R17 (test coverage), plus the pipeline deferrals R7, R19-partial, R22.

### Follow-up — 2026-07-18 (options A + B)

- **Pushed** all commits to `origin/develop`.
- **R28 FIXED** (`2c263b1`) — root cause was a *test-isolation* defect, not a product bug: `test_build_pipeline_keeps_only_gated` read the real `content/knowledge-base/` via `_existing_etymology_roots()` + `load_term_index()`, so an already-ingested `nafs` atom made the pipeline filter it as a reuse. Stubbed both global loaders in the test. Full suite now **1,592 passed, 1 skipped, 0 failed.**
- **R5 / R12 / R13 DONE** (`9d48372`) — `.codex/hooks.json` repointed from the foreign `/Users/ahmac/…` path to the existing repo-relative `.claude/hooks/` scripts; `docs-updater` canonicalized (`infra/claude-agents/` + byte-identical `.github/agents/` mirror); `infra/_README.md` registry rebuilt to 23 agents (added `docs-updater` + the four omitted book/preview challengers, moved deprecated `podcast-auditor` to a note).
- **Remaining deferrals** now narrow to owner-decision/structural items: R4 (wave engine), R7 (staging trio), R9/R14/R26 (structural), R10/R21 (renames), R17 (coverage), R19-partial (`knowledge/augmenter`, `classify_slides`), R22 (Gemini retry).
