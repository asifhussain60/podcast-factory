# Module-decomposition refactor specs (deep-read audit, 2026-06-13)

Status: **DRAFT — awaiting per-spec approval. No code changed.**

Three Flag-class Single-Responsibility / Open-Closed findings from the 2026-06-13
deep-read audit. Each is behaviour-preserving by intent; each touches working, tested,
high-churn code, so each is gated on explicit approval before execution. All three carry
the no-regression discipline: trace current behaviour, apply, verify traced behaviour
preserved, revert-and-revise on failure.

These specs live here (not in `plan.yaml`) precisely because they are *proposed*, not
shipped. On approval + execution, the shipped step is recorded in the commit + handoff
log per plan-tracking discipline.

---

## Spec 1 — `_framing.py`: Strategy registry for prompt variants (LOWEST RISK)

**Target:** `scripts/podcast/_authoring/_framing.py`
**Finding severity:** P2 · **Verdict:** Flag

### Current behaviour (traced — must be preserved)
- `author_framing(book_dir, chapter_slug, timeout=FRAMING_TIMEOUT) -> str` is the public
  entry. Exported via `_authoring/__init__.py:46`; called from
  `phases/per_chapter.py:128` as `author_framing(book_dir, chapter_slug)`.
- Variant selection: `_resolve_prompt_variant(category)` — `sites→consumer`,
  `explainers→technical`, else `islamic` (back-compat default).
- Prompt builders: `_build_consumer_framing_prompt(...)` and
  `_build_technical_framing_prompt(...)` exist as functions; **the islamic prompt is
  inline** in `author_framing` at `_framing.py:348` (`prompt = ( ... )`). There is no
  `_build_islamic_framing_prompt` today.
- `author_framing` also owns: category detection, sermon-contract parse
  (R-SERMON-VERBATIM), episode-number/path resolution (X7 letter-suffix rule), the
  shellout (`_run_claude_p`), a `compress_prompt` sub-step (`_framing.py:780`), and
  artifact assertion.

### Regression traps (CRITICAL — these have bitten before)
1. `tests/test_technical_path.py` does `inspect.getsource(author_framing)` and asserts
   the source string literally contains `'explainers'` (lines ~628, ~814). If the
   `explainers→technical` mapping moves into a registry dict in a *different* function,
   `getsource(author_framing)` no longer contains `'explainers'` and the test fails.
   **Mitigation:** keep the registry as a module-level dict in `_framing.py` AND have the
   tests assert against `inspect.getsource(_framing)` (module) or the registry keys —
   update the two assertions in the same commit. Do not silently break them.
2. `test_framing_cache.py:53` and `test_per_chapter_augment.py:75` monkeypatch
   `author_framing` **by name** — the public name and signature must not change.

### Target structure
1. Extract the inline islamic prompt (`:348`) into `_build_islamic_framing_prompt(...)`
   with the SAME signature shape as the consumer/technical builders.
2. Introduce a module-level registry:
   `FRAMING_PROMPT_BUILDERS: dict[str, Callable[..., str]] = {"islamic": _build_islamic_framing_prompt, "consumer": _build_consumer_framing_prompt, "technical": _build_technical_framing_prompt}`.
3. `_resolve_prompt_variant` stays (still the category→variant map) — or fold its body
   into a second registry `CATEGORY_TO_VARIANT` keyed dict with `.get(category, "islamic")`.
4. `author_framing` selects `builder = FRAMING_PROMPT_BUILDERS[_resolve_prompt_variant(category)]`
   and calls it — replacing the `if _use_consumer_prompt / elif _use_technical_prompt /
   else inline` block.

### Steps
1. Extract islamic builder (pure move of the string literal; no logic change).
2. Add the two registries.
3. Replace the selection branch with a registry lookup.
4. Update the two `inspect.getsource` assertions to target the module/registry.
5. Run `python3 -m pytest scripts/podcast/tests/test_technical_path.py` +
   `test_framing_cache.py` + `test_per_chapter_augment.py`.

### Test plan
- Existing tests cover variant routing (technical/explainers, consumer/sites) — they are
  the regression gate. Add one unit test: `FRAMING_PROMPT_BUILDERS.keys() == {islamic,
  consumer, technical}` and each value is callable.
- Behaviour-preservation check: a new content category is now ONE dict entry + ONE
  builder (Open/Closed satisfied).

### Blast radius
1 file changed + 2 test assertions updated (same commit). No call-site changes. Low risk.

---

## Spec 2 — `_chapter_design.py`: split `author_phase_0d` along its Step 1/2/3 seams

**Target:** `scripts/podcast/_authoring/_chapter_design.py:169-1079`
**Finding severity:** P2 · **Verdict:** Flag

### Current behaviour (traced — must be preserved)
- `author_phase_0d(book_dir, *, length_tier="extended", unit_mode="auto",
  timeout=DEFAULT_TIMEOUT, toc_timeout=PHASE_0D_TOC_TIMEOUT, sc_timeout=PHASE_0D_SC_TIMEOUT,
  log=print, category=None) -> str`.
- Called from `phases/initial_driver.py:169`
  (`author_phase_0d(bd, length_tier=length_tier, unit_mode=unit_mode, log=_info)`);
  exported via `_authoring/__init__.py:44`; imported in `orchestrate_book.py:141`.
- 910-line function, ~356 lines of embedded prompt strings. Its own docstring documents:
  - Step 1: TOC + plan (one small claude call) → `_chunks/0d/source-toc.json`.
  - Step 2: per-source-chapter loop (one call each) → `chapters/ch##.txt`,
    `chapter-contracts/*.yml`, `_chunks/0d/sc-NNN.{rationale,source-map}.md`,
    `sc-NNN.done` resume markers.
  - Step 3 (deterministic stitch): concat sc-NNN.rationale → chapters-rationale.md;
    concat sc-NNN.source-map (shared header) → source-chapter-map.md.
- Also owns: `_read_profile_and_planning`, topic-floor validation
  (`_topic_floor_violations`), the "rc=0 but no artifacts" guard (`:951`).
- Returns a summary string (`:1074`).

### Regression traps
1. `tests/test_technical_path.py:347` asserts via `inspect.signature(author_phase_0d)`
   that the `category` kwarg exists. **The public signature must not change.**
2. `tests/e2e/test_full_pipeline.py` injects `author_phase_0d=self._mock_0d` by keyword —
   public name + injectability must be preserved.
3. Step 2's `sc-NNN.done` resume-safety is load-bearing (orchestrator-crash recovery).
   Any extraction MUST preserve the marker-write order: artifacts first, `.done` last.

### Target structure (private helpers; public coordinator unchanged)
- `def _phase_0d_plan(...) -> dict` — Step 1: build TOC prompt, shellout, parse
  `source-toc.json`, return the plan dict.
- `def _phase_0d_author_chapters(plan, ...) -> None` — Step 2: per-SC loop incl.
  resume-marker discipline + the no-artifacts guard.
- `def _phase_0d_stitch(...) -> None` — Step 3: deterministic concat (NO LLM).
- `author_phase_0d(...)` becomes the thin coordinator: read config → `_phase_0d_plan`
  → `_phase_0d_author_chapters` → `_phase_0d_stitch` → return summary. Signature byte-identical.

### Test plan (golden-output — required before refactor)
The LLM steps (1, 2) are non-deterministic, but **Step 3 (stitch) is fully deterministic**
given the `sc-NNN.{rationale,source-map}.md` inputs. Author a golden test BEFORE touching
the function:
1. Fixture: a temp book dir with 2–3 canned `_chunks/0d/sc-NNN.rationale.md` +
   `sc-NNN.source-map.md` + `sc-NNN.done` files (no LLM needed).
2. Call `_phase_0d_stitch` (post-extract) — or, pre-extract, drive the stitch region —
   and assert `chapters-rationale.md` + `source-chapter-map.md` match a committed golden
   byte-for-byte.
3. This pins the deterministic seam so the extraction is provably behaviour-preserving on
   the part that doesn't need a live model. Steps 1/2 stay covered by the existing mocked
   e2e (`test_full_pipeline.py`).

### Blast radius
1 file changed + 1 new golden test + fixtures. No call-site changes (signature frozen).
Medium risk (high-churn, every-book path) — golden test is the mitigation. Refactor only
after the golden test is green on current `main` behaviour.

---

## Spec 3 — `StudioPoc.tsx`: decompose the God Component + de-imperative the pickers

**Target:** `plan-dashboard/src/components/reader/poc/StudioPoc.tsx:500-1930`
**Finding severity:** P2 · **Verdict:** Flag (largest blast radius — phase it)

### Current behaviour (traced — must be preserved)
- Default export `StudioPoc(props)` — the LIVE production studio editor, routed at
  `src/pages/studio/[slug]/[step].astro:224`; also referenced by
  `src/pages/api/studio/save-stage.ts` (the PM serializer contract).
- One ~1,430-line component function, **25 `useState` hooks**, owning: lineage state +
  `switchLineage`, chapter switching, stage approval (`approvedStages`, `finalized`),
  save I/O (`saving`/`saveError` → save-stage API), AI panel
  (`aiBusy`/`aiKind`/`aiResult`/`aiOptions`/`aiError`), section depths + tag maps,
  Arabic toggle, diff rendering (`showPrevDiff`), TipTap editor config (`StudioDecos`
  useMemo, `MarkerHighlight` extension), inspector tabs.
- **46 `document.*` / `createElement` calls.** `_buildDepthPicker` (`:269`),
  `_buildTagPicker` (`:388`), `openDepthPicker`/`openTagPicker` build raw
  `HTMLDivElement` popovers imperatively and append them outside React reconciliation —
  inconsistent with the reader's React popovers (`TopicPopover`/`TermPopover`/`QuranPopover`).
- 0 inline `style=` (className + `--c-*` tokens) — **Cortex-clean; do not touch styling.**

### Regression traps
1. The save-stage API contract (`api/studio/save-stage.ts`) depends on the component's
   simple PM markdown serializer — serializer output must be byte-identical after refactor.
2. The deep-link index contract: `[step].astro` passes `initialChapIdx`; props shape frozen.
3. Track-changes (jsdiff word-level), Arabic-toggle decorations, and verse-chip (FC-1)
   are decoration-based and non-destructive — extraction must keep the decoration plugins
   wired to the same editor instance.
4. This is a Cortex-governed UI surface — the html-view-challenger agent must gate the
   result, and `npm run lint:views` must stay clean.

### Target structure (phased — do NOT do in one commit)
- **Phase 3a (hooks, no UI change):** extract `useStageApproval`, `useAiPanel`,
  `useSectionDepths` custom hooks (state + handlers move out; JSX unchanged). Lowest risk.
- **Phase 3b (pickers → React):** replace `_buildDepthPicker`/`_buildTagPicker` +
  `open*Picker` with React-rendered popover components matching `TopicPopover` (CSS-var
  positioning via `style={{'--popover-*'}}` — the sanctioned token pattern). Removes the
  46-call imperative DOM layer.
- **Phase 3c (child components):** split inspector tabs + the AI panel + the lineage rail
  into child components under `reader/poc/` (or rename out of `poc/` — see naming note).

### Naming note (P3, separate decision)
The `poc/` path + "spike" header are misleading for a production surface. A rename
(`poc/StudioPoc.tsx` → `studio/StudioEditor.tsx`) touches 2 imports + 1 API doc comment.
Defer as its own small change; do NOT bundle into the decomposition.

### Test plan
- No component tests exist today. Before 3b/3c: capture the visual-QA baseline (the audit
  loop) for `/studio/<slug>/edit` at desktop+mobile, and a save-stage round-trip check
  (edit → save → reload → identical markdown). Re-run after each phase.
- Gate every phase through `npm run lint:views` + the html-view-challenger agent.

### Blast radius
1 component file (phased across 3 commits) + new hook/component files. Phase 3a low risk;
3b/3c medium (decoration wiring, serializer). Visual-QA loop is mandatory after 3b/3c.

---

## Recommended execution order (on approval)
1. **Spec 1** (`_framing` registry) — lowest risk, smallest blast radius, immediate
   Open/Closed win.
2. **Spec 2** (`author_phase_0d`) — only after the golden stitch test is green.
3. **Spec 3** (`StudioPoc`) — phased 3a → 3b → 3c, visual-QA gated; largest effort.
