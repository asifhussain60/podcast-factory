# Holistic Code + Visual QA Audit — podcast-factory Pipeline + Podcast Factory Astro Site

## Mission

Run a full, systematic audit of the `podcast-factory` repo across three domains:

1. **The pipeline** — every Python script under `scripts/podcast/`, the shared library modules (`_paths.py`, `_rules.py`, `_branching.py`, `_quality.py`, `_notebooklm_table.py`, `_validators_framing.py`, etc.), and the orchestrator (`orchestrate_book.py`).
2. **The Podcast Factory Astro Site (code quality)** — all Astro pages and components under `plan-dashboard/src/`, the TypeScript library modules under `plan-dashboard/src/lib/`, and the mirror files (`content-paths.ts`, `peq-scores.ts`, `editorial.ts`, `stage-review.ts`).
3. **The Podcast Factory Astro Site (visual QA)** — a self-correcting screenshot loop that verifies every UI surface at representative viewports and states, finds concrete visual defects, fixes them in source, and iterates to convergence.

The goal is a prioritised, actionable findings report — not a description of what the code does. Every finding must name the specific file(s) and line range(s), state the violation, state the consequence (regression risk, maintenance cost, correctness hazard), and propose the minimal correct fix. Run domains 1 and 2 first (static analysis), then domain 3 (visual QA loop), so code-quality fixes are already applied before screenshots are captured.

---

## Audit lens — domains 1 and 2 (apply all four to every module)

### 1 — DRY (Don't Repeat Yourself)

Scan for:
- Logic, constants, or string literals copy-pasted across two or more files.
- Path construction code that exists outside `_paths.py` / `content-paths.ts`.
- Branch-name computation that exists outside `_branching.py`.
- Score thresholds or quality constants defined outside `_rules.py` / `_quality.py`.
- NotebookLM table rendering outside `_notebooklm_table.py`.
- Framing-validator logic duplicated in callers instead of staying in `_validators_framing.py`.
- Repeated `subprocess.run` / `shutil` / `jq` incantations that could be a shared helper.
- Duplicate Astro component structures (e.g. card layouts, status badge patterns, table wrappers) that could be a shared component.
- CSS variable references hardcoded as literal colour values instead of `--c-*` tokens (violation of the Cortex HTML View Quality Standard).

### 2 — SOLID principles

**S — Single Responsibility**
Every class, function, and script should own exactly one reason to change. Flag:
- Scripts that both drive a pipeline phase AND manage file I/O AND validate output (three concerns).
- Orchestrator sections that mix process control, logging, cost accounting, and branch management.
- Astro components that fetch data, transform it, and render UI in a single component.

**O — Open/Closed**
New content profiles, phases, or buckets should require no edits to existing logic — only additions. Flag:
- `if category == "Islamic"` / `elif category == "Fiction"` chains that need a new arm for every new bucket (should be a dispatch table or strategy).
- Phase sequences hardcoded as ordered lists rather than registry-driven.
- Video style selection via `if/elif` instead of a `VIDEO_STYLE_MAP[content_profile]` lookup.

**L — Liskov Substitution**
If phase drivers share a common interface, any phase driver should be substitutable. Flag:
- Phase driver functions with wildly inconsistent signatures (some take `slug`, some take `slug + pdf_path`, some take `state_dict`).
- Inconsistent return contracts (some return `True/False`, some return `dict`, some raise, some print-and-exit).

**I — Interface Segregation**
Callers should not depend on interfaces they don't use. Flag:
- Utility modules that import heavy optional dependencies at module level, forcing every caller to pay the import cost even when the feature is unused.
- Shared helper functions bundled with unrelated helpers in the same module (e.g. git helpers and cost helpers in the same file).

**D — Dependency Inversion**
High-level pipeline logic should depend on abstractions, not concrete I/O calls. Flag:
- `orchestrate_book.py` directly calling `open()`, `subprocess.run()`, or `shutil.copy()` rather than delegating to named abstractions.
- Astro pages calling raw `fetch()` or `fs.readFileSync()` instead of library functions in `src/lib/`.
- Hardcoded API endpoint URLs in component files rather than a centralised config.

### 3 — Design patterns

Identify where a recognised pattern would reduce coupling or clarify intent, and where an existing pattern is misapplied. Look for:

- **Strategy** — is video-style selection (`teaching_hybrid` / `scenic` / `technical`) a strategy object, or scattered `if/elif` chains?
- **Template Method** — do pipeline phases share a common skeleton (load state → run → write state → advance) that could be a base class?
- **Registry / Plugin** — is phase registration a dict-of-callables or hardcoded in the orchestrator loop?
- **Observer / Event** — does cost accounting happen inline in each phase, or does a central ledger observe phase completions?
- **Builder** — are episode/framing documents assembled with string concatenation, or a typed builder?
- **Repository** — does `orchestrator-state.json` access go through a single reader/writer abstraction, or do multiple scripts `json.load` it directly?
- **Adapter** — are the TS↔Python mirror files (`content-paths.ts` ↔ `_paths.py`) adapted from a shared schema, or maintained independently with drift risk?

### 4 — Anti-patterns and regression risk

Flag any of the following:

| Anti-pattern | Signal to look for |
|---|---|
| **Magic strings** | Bucket names, phase names, status strings, file suffixes as string literals rather than named constants from `_rules.py` |
| **God script** | Any single script > ~300 lines doing unrelated things |
| **Shotgun surgery** | A single logical change (e.g. adding a new bucket) requiring edits to 5+ files |
| **Primitive obsession** | Passing raw `str` slug/path everywhere instead of a typed `ContentPath` or `BookRef` |
| **Dead code** | Deprecated functions or legacy path helpers still exported and callable with no real caller (e.g. `branch_prefix()`, removed 2026-07-16, was one) |
| **Mutable global state** | Module-level mutable dicts or lists shared across function calls |
| **Silent swallow** | `except Exception: pass` or `except Exception: continue` without logging |
| **Implicit ordering** | Phases that depend on sibling phase side-effects without declaring it |
| **Hardcoded test data** | Slug/path constants baked into non-test scripts |
| **Stale documentation** | Docstrings or inline comments that contradict current behaviour |
| **Mirror drift** | `content-paths.ts` and `_paths.py` diverging on bucket list, path structure, or fallback logic |
| **Inline style leak** | Any `style=` attribute or `<style>` block in Astro components (Cortex HTML View Quality Standard violation — mechanical violation blocks commit via `npm run lint:views`) |
| **Component prop drilling** | Passing the same prop through 3+ component levels instead of a store or context |

---

## Scope boundaries

**Include:**
- `scripts/podcast/` — every `.py` file
- `plan-dashboard/src/` — every `.astro`, `.ts`, `.tsx` file
- `plan-dashboard/scripts/` — build/snapshot scripts
- Mirror pairs: `content-paths.ts` ↔ `_paths.py`, `peq-scores.ts` ↔ `_quality.py` + `challenger_scoring.py`, `editorial.ts` + `stage-review.ts` ↔ their Python generators

**Exclude** (out of scope for this audit):
- `content/` subdirectories (generated artefacts, not source code)
- `_workspace/plan/` (planning docs, not code)
- `skills-staging/` (skill definitions, audited separately)
- `server/` and `infra/` (retired — do not resurface)

---

## Process — domains 1 and 2 (static analysis)

Work through the scope in this order to catch cross-cutting issues before module-level ones:

1. **Dependency graph pass** — read all `import` statements across `scripts/podcast/`. Build a mental (or actual) module dependency graph. Identify circular imports, unused imports, and modules that import more than they expose.

2. **DRY sweep** — grep for duplicate string literals, duplicate logic blocks, and duplicate path/branch construction. Any string that appears verbatim in 3+ files and has semantic meaning is a DRY violation candidate.

3. **SOLID sweep** — for each module, state its single responsibility in one sentence. If you cannot, it violates SRP. Then check O, L, I, D as above.

4. **Pattern audit** — for each architectural concern (phase dispatch, state I/O, cost accounting, content routing), name the current pattern and the better pattern if one exists.

5. **Anti-pattern scan** — run the anti-pattern checklist above over all files in scope.

6. **Mirror sync check** — diff `content-paths.ts` against `_paths.py` at the semantic level. List any bucket, fallback path, or function that exists in one but not the other.

7. **Regression risk scoring** — for each finding, assign a regression risk level:
   - 🔴 **P0** — active regression risk or correctness bug (fix before next pipeline run)
   - 🟡 **P1** — will cause a regression as the codebase grows (fix before next feature)
   - 🟢 **P2** — maintainability / readability (fix opportunistically, batch with related work)

---

## Process — domain 3 (visual QA self-correcting loop)

Run this pass after applying all static-analysis fixes from domains 1 and 2. The loop is capped at 5 iterations; stop earlier if a full iteration surfaces zero actionable defects or if you are producing cosmetic churn rather than real fixes.

**Setup.** Determine how the site runs locally by reading `plan-dashboard/package.json` and `plan-dashboard/astro.config.*`. Start the dev server (`cd plan-dashboard && npm run dev`) if it is not already running and confirm it is reachable via browser-automation or screenshot tooling before proceeding. Identify every route the Astro site exposes — inspect `plan-dashboard/src/pages/` for static routes and any dynamic `[...slug]` patterns. Cross-reference with `git status` and `git diff` to flag any page or component touched by recent changes; those surfaces are mandatory. The app's primary screens (dashboard, reader, plan view, any status or archive pages) are always in scope regardless of recent diff.

**Surface inventory.** Before capturing a single screenshot, build an explicit list: every route URL, every component that renders independently as a meaningful UI state, and every theme or mode variant the app supports (check for light/dark toggles, any `data-theme` attribute, or CSS custom-property overrides in the design system). Record this list; every entry must be visited at least once per iteration.

**Screenshot discipline.** Create a single throwaway folder at `plan-dashboard/.visual-qa/` at the start of the loop. Capture every surface at a minimum of two viewports — `~1440px` desktop width and `~390px` mobile width — and in every meaningful state: default, hover or focus, expanded or collapsed, empty, loading, error, and any theme variants. Name files descriptively (e.g. `dashboard--desktop--default.png`, `reader--mobile--empty.png`). Record the exact path of every file written so cleanup is precise. Do not invent a state you cannot actually trigger; if a state requires seeded data or a specific orchestrator phase, note it as untestable rather than skipping silently.

**Judgment criteria.** Open and inspect each image before making any assertion about how it looks — do not claim a surface looks correct from memory or from reading source code alone. Judge every captured state against the Cortex HTML View Quality Standard (`docs/standards/html-view-quality.md`, cite findings by REQ-NNN) and the repo's `--c-*` CSS custom-property token system. Hunt specifically for: clipping or overflow at either viewport; text truncation that loses meaning; element overlap or misalignment; inconsistent spacing or sizing relative to surrounding elements; text contrast insufficient for readability; off-theme or hardcoded colour values (any hex, `rgb()`, or named colour not routed through a `--c-*` token is a defect); broken, distorted, or oversized images and SVGs; z-index or stacking glitches; broken responsive layout (columns collapsing unexpectedly, content escaping its container); missing or invisible keyboard focus styles on interactive elements; and anything that looks unintentional relative to the surrounding design. A judgment of "looks correct" is only valid if it is grounded in a screenshot captured in the current iteration.

**Fix discipline.** For every real defect, make the smallest correct fix in the source — a component file, a layout file, or a CSS/token definition — matching existing patterns and reusing the design tokens, utility classes, and component abstractions already present in the codebase. Never add inline `style=` attributes, never hardcode colour or spacing values, never add new dependencies, and never touch files unrelated to the defect. After each fix, re-screenshot only the affected surface(s) at both viewports and re-judge before marking the defect resolved. Do not mark a defect resolved without a confirming screenshot from the current iteration.

**Do not:** redesign, restyle, or improve things that are not actually broken — fix defects, never gold-plate or change copy or behaviour. Do not claim "looks good" or "done" from memory without a fresh screenshot proving it. Do not invent issues to justify another iteration — an empty pass is the success signal, not a failure.

**Cleanup.** When the loop converges (or the 5-iteration cap is reached), delete every file inside `plan-dashboard/.visual-qa/` and the folder itself. Delete nothing else; leave the working tree otherwise clean and never touch pre-existing files.

---

## Output format

Follow the 4-part response template from `_workspace/plan/response-template.md`. The report body must be structured as follows — no custom section labels.

### At a glance
- Total findings by severity across all three domains: P0 / P1 / P2 counts
- Top 3 systemic issues (one line each) — the ones that, if fixed, eliminate the most downstream findings
- Estimated blast radius of the top systemic issue (how many files would change)
- Visual QA convergence status: iterations run, defects found, defects resolved, any remaining open issues

### Findings — Pipeline (Python)

List findings in descending severity (P0 first). Each finding entry:

```
### [P0|P1|P2] <Short title>

**Files:** `path/to/file.py` lines N–M
**Violation:** <Which principle or anti-pattern, one sentence>
**Consequence:** <What breaks or degrades if this is not fixed>
**Fix:** <Minimal correct change — specific, not generic>
```

### Findings — Astro Site code quality (TypeScript/Astro)

Same format as above. Include mirror-drift findings here under the sub-heading **Cross-domain (mirror drift, shared contracts)**.

### Findings — Astro Site visual QA

Present as a table:

| Surface | Viewport | State | Defect found | Fix applied | File changed | Confirmed resolved |
|---|---|---|---|---|---|---|

If the 5-iteration cap was reached before full convergence, add an **Open visual issues** section below the table listing unresolved defects with their last-captured screenshot description and the reason convergence stalled.

### Recommended remediation sequence

A batched, ordered plan:
- **Wave 1 (P0s + visual defects):** All P0 code findings and all confirmed visual defects. Group fixes that belong in a single commit.
- **Wave 2 (P1 systemic):** The 2–3 structural changes that unblock the most P1s (e.g. "introduce phase registry", "centralise status constants").
- **Wave 3 (P1 remaining + P2 batch):** Remaining P1s, then P2s grouped by module.

For each wave, note: estimated files changed, regression risk of the wave itself, and whether it requires a Tier 2 decision (destructive refactor touching shared state).

### Next

```
A. (Recommended) Execute Wave 1 now — all P0s and visual defects, no Tier 2 actions required, safe to chain.
B. Produce a detailed refactor spec for Wave 2 before touching anything.
C. Export this report as a tracked issue list in `_workspace/plan/debt/pipeline-debt.md`.
```

---

## Standing constraints (do not violate)

- **Tier 2 actions** (`publish_to_library.py`, merges to `main`, force-push, `rm` of tracked files) require explicit user authorisation — surface them in findings, do not execute.
- **No emojis in code or commits** — status emojis (🟢/🟡/🔴/⚠) in prose only.
- **Cortex HTML View Quality Standard** — any Astro/HTML finding must cite the specific REQ-NNN from `docs/standards/html-view-quality.md`. Do not re-copy rule text; cite by number. Run `npm run lint:views` after every visual-QA fix wave; a linter failure is a P0 finding.
- **Mirror files must stay in sync in a single commit** — any fix to `content-paths.ts` that has a `_paths.py` counterpart must be proposed as one atomic change to both.
- **No plan entry needed** for P0 bug fixes and refactors that fit inside existing plan entries — just do the work and note it in the commit + `_workspace/plan/copilot-handoff.md`.
- **Plan-tracking discipline** — if Wave 2 introduces a new architectural surface (new module, new pattern), update `_workspace/plan/refactor/plan.yaml` + `plan.md` in the same commit and regenerate snapshots via `python3 plan-dashboard/scripts/regenerate-snapshots.py`.
- **Visual QA screenshot cleanup is mandatory** — delete `plan-dashboard/.visual-qa/` and all its contents before reporting convergence. Never commit screenshots; never delete pre-existing files.
