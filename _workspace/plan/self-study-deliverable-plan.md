# Self-Study Hybrid Islamic Educational Translation Deliverable — Approved Plan

**Status:** APPROVED 2026-07-16 (render-time approach). Cutover landed 2026-07-17;
foundation (Steps 1–2) shipped 2026-07-17.

**Decisions settled 2026-07-17 (were OPEN):**
- **Decision 1 (Key Takeaways):** option (a) — **labeled study-summaries.** A gated,
  clearly-labeled "Study summary" block scoped to this deliverable is the explicit,
  scoped exception to the anti-summary principle (never a silent relaxation).
- **Decision 2 (sub-headings):** option (a)+(b) — **source-derived section markers plus a
  light AI pass** for short navigational sub-titles where the source has none (titles are
  navigation only, never new teaching).

**Progress:**
- ✅ **Step 2 (renderer extension) + Step 1 (spike) — DONE 2026-07-17.** The opt-in
  self-study render mode is in `book-html.mjs` (`renderMd(md, crosswalk, {selfStudy})` +
  `buildBookHtml({selfStudy})`, body class `book-self-study`): bullet lists → `<ul>`, the
  0book-augment editorial fences → labeled **Contextual note** asides, and
  `study-summary` fences → **Study summary** asides. Styling in `book-print.css`
  (token-only). Default render is byte-for-byte unchanged (all branches gated on
  `selfStudy`); a companion fix stops the augment comment-fences from leaking as visible
  text in the default reading edition. Regression guard: `book-html.test.mjs` (4 tests,
  `node --test`). Verified visually (spike page: chapter-open, drop-cap, bullet list, both
  asides distinct + on-theme). astro check 0/0/0, lint:views clean, smoke 32/32.
- ✅ **`--self-study` invocation + Steps 4–5 — DONE 2026-07-17.** `_self_study.py`
  materializes `book/book-self-study.md` from `book.md` (base never mutated): per chapter
  it generates a **Study summary** (Step 5, Decision 1 — labeled, faithfulness-gated,
  chapter-only, `NONE` when too slight) and a KB-grounded **Contextual note** (Step 4 —
  reuses the fixed `_book_augment` enrichment: veto + doctrinal gate). Idempotent (rebuilds
  from the clean base). `build_book_pdf.py --self-study` runs the prep then renders
  `book-self-study.pdf` (a distinct in-repo artifact — no edition-titled copy, no Drive
  publish); `--no-generate` renders an existing self-study md as-is. Flag threads
  build_book_pdf.py → render-book-pdf.mjs (argv[6]) → buildBookHtml({selfStudy}).
  Verified END-TO-END: a real 9-chapter book rendered to a 117pp self-study PDF with the
  labeled Contextual-note + Study-summary asides on each chapter, reading-edition
  typography intact. Tests: `test_self_study.py` (6 cases — gate, format, materialize,
  idempotency, base-untouched, drop). Full suite 1232 passed; astro/lint/smoke green.
- ✅ **Studio "Self-study PDF" button — DONE 2026-07-17.** The Preview page
  (`/studio/<slug>/preview`) has a "Self-study PDF" action beside "Generate PDF":
  a themed confirm (`confirmDialog`) → `POST /api/studio/generate-self-study-pdf`
  (spawns `build_book_pdf.py <dir> --self-study --json`, mirrors generate-book-pdf.ts) →
  shared status line. Both buttons disable while either runs. Verified: button renders
  on-theme, confirm dialog shows the correct copy, zero console errors; astro check
  0/0/0, lint:views clean, smoke 32/32. (Sync endpoint — the generation is minutes-long
  LLM; acceptable for this single-user local tool. A background-job/polling variant is a
  possible future hardening.)
- ⏳ **Remaining:** Step 3 (render-time term definitions at first use, via `define-term`),
  Step 6 (source-derived + light-AI intra-chapter sub-headings — note: sub-heading
  insertion interacts with the `^## ` chapter-split used by summary/note generation, so it
  needs care to key blocks to numbered chapters, not inserted sub-titles), Step 7
  (challenger gates — extend `book-challenger` for term-once/note/summary faithfulness +
  `book-render-challenger` for the new blocks).

**Original two OPEN decisions (now settled above) and full plan follow.**

**Provenance:** approved after an adversarial review of a first draft. The draft framed this
as a compose-time "profile"; two grounded code investigations proved that fights the
pipeline, and the approach was flipped to render-time. The rejected assumptions are recorded
below so we don't relapse into them.

## What this deliverable is

Classical Arabic Islamic texts → a "Contemporary Academic / Self-Study Hybrid" English
**PDF**: faithful translation + inline term definitions + Quran/Hadith set apart + indented
Contextual Notes (hashiyah replacement) + per-section Key Takeaways, in a strict Markdown
schema, for a reader studying without a teacher. Success = a **consistent, well-written PDF**
across a whole book.

## Approved approach — render-time presentation layer, NOT a compose profile

Keep the faithful composer (and the seam/dedup work from this session) UNTOUCHED. `book.md`
stays semantic; the self-study format is built as a render-time transformation over it, plus
ONE gated compose-adjacent layer (inline notes). This is how the pipeline already does Quran
styling (plain `> quote` → styled block at render), minimizes regression to the route being
consolidated, and reuses more of the pipeline.

### Rejected draft assumptions (do not relapse)

- ❌ "Make the structure gate mode-aware." Structure is pipeline-owned at THREE gates
  (rejects model top heading, demotes interior `##`→`###`, and model `## X` is misread as a
  new CHAPTER by TOC/crosswalk/seam-dedup). The model must keep emitting prose only.
- ❌ "Register a third profile." No profile/deliverable registry exists — two knobs
  (`book_augmentation`, `book_voice`) feed a fixed 2-stage chain.
- ❌ "Seed a compose-time term ledger from the glossary." Glossary holds Arabic-script
  overlay only (no English definitions, no render-time first-use gate). Terms are defined
  idiomatically at reader/render time via the existing `/api/ai/define-term` engine.

## Reuse audit (verified in code)

| Capability | Status |
|---|---|
| Faithful base translation, Quran anchoring, honorifics | reuse as-is (consume its `book.md`) |
| Renderer + Quran-blockquote synthesis pattern (`book-html.mjs`) | reuse + extend |
| Reader term-definition engine (`define-term` + Gemini, same infra as the Gems tool) | reuse |
| `_book_augment` doctrinal veto + corpus-only grounding | adapt (chapter-append → paragraph-inline) |
| Renderer bullet-list + callout parsing | BUILD (`renderMd` has no list parser today) |
| Render-time first-use term tracking | BUILD |
| Per-section Key Takeaways extraction | BUILD + Decision 1 |
| Intra-chapter sub-headings | Decision 2 |

## OPEN decisions (settle at execution time)

**Decision 1 — Key Takeaways vs the pipeline's anti-summary principle.** The pipeline
actively bans summaries (anti-cliché blacklist; slide authoring is "re-presentation not
summary"). Options: (a) labeled, source-extraction-gated Takeaways scoped ONLY to this
deliverable; (b) surface the source's OWN enumerated points where it enumerates (already
permitted, no invented summary — the faithful default); (c) drop Takeaways. Lean: (b)
default, (a) only if Asif wants true study-summaries and accepts the label.

**Decision 2 — where intra-chapter sub-headings come from** (model can't emit them). Options:
(a) source-derived (`_source_headings` exists); (b) a light design pass proposing sub-titles;
(c) chapter-level only. Lean: (a)+(b).

## The steps

1. **Spike** — render ONE finished chapter through the self-study layer (term inlining + one
   Contextual Note + Quran/Hadith blocks + a Takeaways treatment per Decision 1) to a styled
   PDF page; no compose changes. Proves the approach + tests Decisions 1/2 on real output.
2. **Extend the renderer** — add bullet-list + Contextual-Note callout parsing to
   `book-html.mjs::renderMd` + `book-print.css` classes (reuse `--c-*` tokens; gate through
   the Cortex html-view-challenger). Hard prerequisite for every new block.
3. **Render-time term definitions at first use** — batch pass inlining "term (definition)"
   at first occurrence of each glossary-wrapped term, definitions from `define-term`, deduped
   once per book. No compose-time ledger.
4. **Inline Contextual Notes** — adapt `_book_augment` to paragraph-anchored inline notes,
   reusing its doctrinal veto + corpus grounding unchanged. (Compose-adjacent; land AFTER the
   Phase-5 cutover.)
5. **Key Takeaways** — implement the Decision-1 option.
6. **Sub-headings** — implement the Decision-2 option; model still emits prose only.
7. **Schema-conformance gates** — extend `book-challenger` (term-defined-once, note
   faithfulness, citation format) and `book-render-challenger` (new blocks render clean).

## Sequencing

Render-time work (Steps 1–3) is loosely coupled to the compose consolidation and could begin
fairly independently. The compose-adjacent piece (Step 4) lands after the Phase-5 cutover so
it's built on the single consolidated route.

## DoD / risks

DoD: spike consistency acceptable; `book-challenger` schema dim 0 P0 + terms-once + notes
faithful; `book-render-challenger` RENDER-CLEAN (Cortex honored); a full book renders as a
consistent self-study PDF. Risks: anti-summary conflict (Decision 1 — explicit scoped choice,
never a silent relaxation); sub-heading provenance (Decision 2); renderer scope creep (keep
minimal, pass html-view-challenger); render-time term consistency (one batch pass, not
per-chunk).
