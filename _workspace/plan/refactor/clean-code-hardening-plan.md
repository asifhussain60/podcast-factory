# Clean-Code & Architecture Hardening — podcast-factory pipeline + Astro site

> **Status:** APPROVED by Asif 2026-07-18. Not yet started. Execute in a fresh session with the kickoff prompt at the bottom. Start tranche = R0 + R1.

## Context

The 2026-07-18 repo audit removed 38 files of dead code and fixed the correctness/security items, but deferred the *structural* debt for a deliberate, sequenced plan. This is that plan. It refactors both surfaces toward the clean-code standards the repo *already documents* (DR-005 modularization, the frozen-registry + dependency-injection patterns, the typed-loader pattern) — standardization, not invention.

The debt, measured:

- **Pipeline:** not a real Python package — **261 of 287 modules** carry `sys.path.insert` hacks, and the two orchestrators import the shared `phases/` package two incompatible ways (a latent duplicate-module bug). **No linter/formatter/type-checker** despite ~94% type-hint coverage. **19 files exceed the repo's own DR-005 ≤600-line rule** (`_chapter_design.py` 1329, `_rules.py` 1047, `_translation_edition.py` 1014 …), and two basename collisions (`_convergence.py` ×5, `augmenter.py` ×2) will break under qualified imports.
- **Site:** a **3,051-line `StudioPoc.tsx` God component** (one function ~2,460 lines, 60 `useState`, 43 `useCallback`, 23 inline fetches) shipping from a folder named `poc/`; **87 raw `fetch()` calls** with no shared client; **two divergent markdown renderers**; fat `.astro` frontmatter; **no ESLint/Prettier**; a 130KB `theme.css`.

**Verified during planning (corrects an earlier assumption):** DR-005 is documented as "Enforced by pre-commit + CI" but **nothing actually checks line count** in the hook or CI — the enforcement claim is stale. So R3's real fix is to *make the standard enforceable* (grandfather the current 19, block new violations, burn the list down), not to blanket-split cohesive files.

Intended outcome: every pipeline file within DR-005 and importable as a package; every LLM-touching function testably injectable; the site editor decomposed into single-responsibility hooks; one fetch client; one renderer; honest names; and lint/type gates that keep it clean going forward.

## Decisions locked (from Asif)

- **Renames: Studio-centric** — `poc/` → `components/studio/editor/` (`StudioPoc` → `StudioEditor`), `corpus-mock/` → `components/corpus/`, `corpus-mock-sample.ts` → `corpus-fallback.ts`, `studio-poc.css` → `studio-editor.css`.
- **Packaging: phased, late & gated** — the full conversion is in the plan but sequenced last, behind a go/no-go gate after R3.

## Guiding principles

1. **Copy the exemplars, don't invent.** Pipeline: `_rules.py` frozen-dataclass registry, `_etymology.build_etymology_atoms(generator=, verifier=)` Callable-DI, the `phases/` `is_done`/`execute` contract, `tools/content_reviewer/` as the packaging model. Site: `src/lib/reader/studio-pipeline.ts` (pure-fn + typed + thin async loader), `src/lib/api-responses.ts` (envelope), `src/lib/localServerClient.ts` (typed client with timeout).
2. **Smallest change that satisfies the standard; no gold-plating.** Split modules that genuinely *mix responsibilities* (DR-005 is the guide the repo already chose), not cohesive ones that merely exceed a line count. Migrate/rename mechanically. Do not expand scope because a phase is open.
3. **Gate every phase; each is independently shippable and separately approved.** No phase merges without its surface's full gate set green.
4. **Honor the locked contracts:** DR-009 (no version stamps); DR-013 (shipped books addendum-only — this plan touches *code/site*, never shipped book content); the two TS↔Python mirror pairs stay in lockstep per-commit; every plan edit regenerates the dashboard snapshots in the same commit.

## Roadmap integration

Slot as a new **`waves_refactor:`** block in `_workspace/plan/refactor/plan.yaml` (the snapshot generator auto-discovers any `waves_*` key — no generator change), with matching `plan.md` prose. It subsumes the open **Wave H "code-quality refactor"** items. Steps **R0–R5** below. After each phase's plan edit: `cd plan-dashboard && npm run snapshot`, stage the three JSONs in the same commit.

---

## The plan

### R0. Foundation — install the guardrails (both surfaces) — *start here*

> Add the net BEFORE refactoring, sized honestly to each tool's real cost. No runtime behavior changes.

- **Ruff + Prettier + ESLint — the cheap, high-value gates.** Add `ruff` (lint + format) to a new `pyproject.toml`; add `eslint` (typescript-eslint) + `prettier` to `plan-dashboard/`. Start with **auto-fixable rules**, land the mechanical auto-fixes as one reviewable commit per surface, then wire `make lint` + `npm run lint` into pre-commit and CI. Fast baseline-clean.
- **mypy — gradual, NOT a day-one global gate.** Type-checking 100k LOC that was never checked is its own project; forcing it globally would stall everything. Add mypy config in **opt-in mode** (per-module `# mypy: strict` / `[[tool.mypy.overrides]]`), enable it file-by-file as modules are touched in R3/R4, and run it non-blocking in CI until a real subset is clean. Leverages the existing ~94% hints without a big-bang.
- **Make DR-005 actually enforced.** Add a line-count check (pre-commit + CI) with the current 19 over-limit files **grandfathered** into an allowlist; new violations block. R3 removes files from the allowlist as it splits them. Also correct architecture.md's stale "Enforced by pre-commit + CI" note to match reality.
- *Value:* every later phase refactors against real linters + an enforceable modularization rule that can't silently regress. Highest leverage, lowest risk — and the recommended first tranche alongside R1.

### R1. Site — honest names + the shared fetch client — *start here*

> Two mechanical, low-blast-radius wins the rest of the site work builds on.

- **Renames (Studio-centric, patch all imports):** `poc/` → `studio/editor/` (3 sites), `corpus-mock/` → `corpus/` (6 sites), `corpus-mock-sample.ts` → `corpus-fallback.ts` (4 sites), `studio-poc.css` → `studio-editor.css` (3 sites). One isolated commit; `astro check` proves it.
- **`apiFetch<T>()`** — new `src/lib/api-fetch.ts`: path+query building, JSON body/headers, `res.ok`→typed error (preserving current throw-on-error semantics so no call site changes behavior), JSON parse, generic `<T>` tied to the `api-responses.ts` `{ok,data}|{ok,error}` envelope, optional abort/timeout (mirror `localServerClient.ts`). Migrate the 87 raw fetches **incrementally**, deferring `StudioEditor`'s 23 to R2 (they move there anyway). Finish `api-responses.ts` adoption in the 22 hold-out routes.
- *Value:* one place for HTTP error/JSON handling; the file tree stops lying about what's production.

### R2. Site — decompose the God component (highest regression risk — strictly incremental)

> The largest site win and the plan's riskiest step. 60 `useState` / 43 `useCallback` are interdependent; a careless split causes autosave races and stale closures. Therefore: mechanical extractions first to de-risk, then **one stateful hook at a time with a browser-verify between each** — never a big-bang.

- **Pass 1 — mechanical (low risk):** extract constants (`ACTION_REGISTRY`, `MARKER_PATTERNS`, `SURAH_MAP`, `DEPTH_LEVELS_BY_PROFILE`, `EDITOR_FONTS`) to `studio-editor-constants.ts`; extract the standalone imperative-DOM pickers (`_buildDepthPicker`/`openTagPicker`, ~lines 323–589) to their own file; extract dialog subcomponents (`ReplaceDialog`, `DenoiseDialog`, `AiResultPanel`, `TermCurationPanel`); migrate the 23 fetches to `apiFetch`. Verify after each.
- **Pass 2 — stateful hooks, one per commit, browser-verified each time:** `useEditorPrefs`, `useAutosaveDraft`, `useStageApproval`, `useAiActions`, `useTermCuration`, `useReplaceTool`, `useDenoiseTool`, `useSectionDepth`, `useAnnotations`. Target: main `StudioEditor` ≤600 lines.
- **Merge the two markdown renderers** (`markdown.ts` + `source-render.ts`) behind one options API `renderMarkdown(input, {headingIds, tables, angleMarkers, sectionMarkers, arabicBlockquotes})` with a shared `escapeHtml`/`renderInline`/`flush*` core (4 call sites).
- **Thin the fat pages:** extract `studio/[slug]/index.astro`'s 185-line frontmatter into `src/lib/reader/library-view.ts` (follow `studio-pipeline.ts`); same for `studio.astro`.
- **CSS:** split `theme.css` (130KB) into token vs component layers; split `studio-editor.css` (95KB) by concern.
- *Value:* the most-churned, most-fragile surface becomes navigable and unit-testable.

### R3. Pipeline — clean-code hardening (no packaging yet)

> All pipeline wins that don't require the package conversion. Safe against the live pipeline; the 1,592-test suite is the net.

- **Split the 19 DR-005 offenders that genuinely mix responsibilities** (burning down the R0 grandfather allowlist), prioritizing the true god-modules: `_chapter_design.py` (1329), `intake_book.py` (962), `_azure.py` (840, split I/O vs parsing vs retry), `run_wave.py` (824), `_translation_edition.py`, `_slide_authoring.py`. Follow `module-decomposition-specs.md` where it already prescribes a split. A cohesive file marginally over 600 gets grandfathered, not force-split.
- **⚠ Mirror-source modules need same-commit TS checks:** `_rules.py` (holds `ALLOWED_CATEGORIES`/`bucket_for_profile`), `_quality.py` (PEQ), and `_paths.py` are the Python side of the mirror pairs — any split keeps `content-paths.ts` / `peq-scores.ts` / `challenger_scoring.py` in lockstep in the same commit.
- **Fix the basename collisions BEFORE packaging** (qualified imports surface them): disambiguate `_convergence.py` (×5) and `augmenter.py` (×2).
- **Standardize LLM-touching functions on the `_etymology` Callable-DI pattern** so they're testable without mocks.
- **Add coverage to the untested critical modules** (audit R17): `_citation_verify.py`, `score_pronunciation_risk.py`, `mcp_access.py`, `build_probe_bundle.py`, `pronunciation_ledger.py`.
- **Resolve the audit deferrals in-context:** `knowledge/augmenter.py` (delete vs wire a real fallback), `classify_slides.py` (wire vs delete + downgrade the `p3_4` DoR check), the WC8 staging trio's stage-order mirror.
- *Value:* DR-005 allowlist shrinks to empty; collisions gone; highest-risk modules gain tests.

### R4. Pipeline — packaging conversion (root-cause, LATE, go/no-go gated)

> The deepest fix, on already-cleaned collision-free modules. **Decision gate first:** after R3, reconfirm the conversion still earns its ~287-file churn (it should — it unblocks static analysis and kills the duplicate-`phases/` bug — but re-evaluate rather than auto-proceed). If go:

- Add `scripts/__init__.py` + `scripts/podcast/__init__.py` + `pyproject.toml` `[project]` with a console-scripts table for the CLI scripts; `pip install -e .`
- Convert flat imports to package-absolute (`from scripts.podcast._paths import X`) — **unifying the two `phases/` import roots** — and strip the 261 `sys.path.insert` blocks. Model on `tools/content_reviewer/`.
- Update `pytest.ini` (import mode can likely return to `prepend` once collisions are gone) and the CI install step.
- *Value:* eliminates the root cause of the pipeline's structural debt; imports become static-analyzable.

### R5. Pipeline — resolve the dormant wave-engine (optional; unblocks the last deferrals)

> `run_wave.py` + `phases/p*.py` are dormant (empty event stream, waves 1–6 all done) yet share `phases/` with the live orchestrator. Archive into its own package or delete wholesale — an explicit decision, not a silent removal.

- *Value:* removes the two-backbones-in-one-folder hazard; simplifies R4's import graph.

---

## Part A — the exact renames (approved: Studio-centric)

| From | To | Import sites |
|---|---|---|
| `plan-dashboard/src/components/reader/poc/` | `plan-dashboard/src/components/studio/editor/` | 3 (`studio/[slug]/[step].astro`, `OperatorWorkbench.tsx`, `intake/EditorialDefaults.tsx`) |
| `StudioPoc.tsx` (component `StudioPoc`) | `StudioEditor.tsx` (component `StudioEditor`) | same 3 |
| `plan-dashboard/src/components/corpus-mock/` | `plan-dashboard/src/components/corpus/` | 6 |
| `plan-dashboard/src/data/corpus-mock-sample.ts` | `plan-dashboard/src/data/corpus-fallback.ts` | 4 |
| `plan-dashboard/src/styles/studio-poc.css` | `plan-dashboard/src/styles/studio-editor.css` | 3 |

Sibling `poc/` files (`EditorialCards.tsx`, `TransformationDashboard.tsx`, `StageBarChart.tsx`) move with the folder. Mechanical; one isolated commit in R1, proven by `astro check`.

## Sequencing, risk & first tranche

- **Start tranche (smallest safe valuable slice): R0 + R1.** Establishes the net and lands the low-risk site wins. Approve and execute this first; approve later phases as reached.
- After R0, the two surfaces proceed independently: **site R1 → R2**, **pipeline R3**. **R4 (packaging) and R5 (wave-engine) last**, behind decision gates.
- **Highest regression risk = R2** (God component) — mitigated by mechanical-first + one-hook-at-a-time + browser-verify. **Second = R4** (packaging) — mitigated by late sequencing, go/no-go gate, and the full suite.
- No phase changes shipped-book content (DR-013 safe). Each phase = focused, independently revertable commits.

### Discriminator pass (adversarial review applied)

Material risks surfaced and folded in: (1) DR-005-as-mandate was unverified → verified it's *unenforced*, reframed R3 to enforce+grandfather rather than blanket-split; (2) mypy-as-flippable-gate → made gradual/opt-in; (3) God-component split treated as mechanical → strict mechanical-first + one-hook-per-commit incrementality; (4) mirror-source module splits unflagged → R3 now flags same-commit TS lockstep. Remaining inherent risks (R2, R4) are sequenced and gated, not hidden.

## Verification (per phase, before each commit)

**Site (R1, R2):** `npx astro check` → 0 errors · `npm run lint` (R0 ESLint) + `npm run lint:views` → clean · `npm run smoke` → pass · `html-view-challenger` + `site-health-sentinel` agents · manual browser drive of the Studio editor (mount, autosave, AI ask/rewrite/explain, replace, denoise, section-depth, approve/finalize) — confirm zero behavior change.

**Pipeline (R3, R4, R5):** `PYTHONPATH=. python3 -m pytest -q` → 1,592 passing (baseline held) · `ruff check` + scoped `mypy` clean on touched files · `python3 scripts/podcast/_boundary_check.py` → pass · R4 only: `pip install -e .` then re-run the suite from a clean shell (no `PYTHONPATH`), import-smoke every entry point, read-only `orchestrate_book.py --status <in-flight-slug>`.

**Cross-cutting (every phase):** update `plan.yaml` (`waves_refactor:`) + `plan.md`, run `npm run snapshot`, stage the 3 JSONs same-commit; keep mirror pairs in lockstep; no version stamps (DR-009).

## Anchor files

- Exemplars to copy: `scripts/podcast/_rules.py`, `_etymology.py`, `phases/__init__.py`, `tools/content_reviewer/`, `plan-dashboard/src/lib/reader/studio-pipeline.ts`, `src/lib/api-responses.ts`, `src/lib/localServerClient.ts`.
- New files: `pyproject.toml`, ESLint/Prettier config, `src/lib/api-fetch.ts`, `src/lib/reader/library-view.ts`, `studio/editor/` hooks + dialogs + constants, DR-005 line-count check + grandfather allowlist.
- Roadmap: `_workspace/plan/refactor/plan.{md,yaml}`, `architecture.md`, `plan-dashboard/scripts/regenerate-snapshots.py`.

---

## Kickoff prompt (paste into a fresh session)

> Execute the approved refactor plan at `_workspace/plan/refactor/clean-code-hardening-plan.md`. Begin with the **R0 + R1** tranche only: add the Ruff/Prettier/ESLint gates (auto-fix first, advisory→ratchet), wire an enforceable DR-005 line-count check with the current 19 files grandfathered, then do the Studio-centric renames and the `apiFetch<T>()` client. Follow the plan's per-phase verification gates and the roadmap-integration/mirror/snapshot rules. Pause for my approval before R2, R3, R4, or R5.
