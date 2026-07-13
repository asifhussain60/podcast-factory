<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT. Recover older entries from git history when needed.
-->
# Current work - status

**Last updated:** 2026-07-13 4:21 PM EST (Book Composer WYSIWYG upgrade)

**Latest — Book Composer preview is now truly WYSIWYG.** Closed the three
open gaps against the original Phase-4 spec (drag-to-anchor, resize handles,
float-exact preview): placed figures now render INLINE inside `.cx-body` at the
exact paragraph the PDF renderer (`scripts/visual-layout.mjs::applyLayout`)
would use (null→after intro, 0→chapter top, N→after Nth top-level `<p>`) instead
of a band at the chapter top; wrap figures truly float with body text wrapping
beside them (`.cx-body` is `display: flow-root`); a corner resize handle
(`.cx-fig-handle`, pointer-drag → width_pct, snapped 5%, clamped ≤50% wrap); and
drag-and-drop is paragraph-granular with an insertion indicator. The
preview-vs-PDF paragraph counters were proven to agree exactly (blockquote-
nested `<p>` excluded by both). Files: `compose.astro`, `book-composer.ts`,
`book-composer.css`. Gates: `astro check` 0/0/0, `lint:views` clean,
`html-view-challenger` PASS-WITH-CAUTION (the one MUST — REQ-010 1.02rem body
prose — is the pre-existing intentional print-fidelity exemption, unchanged by
this work). Verified in-browser: place → wrap float wraps text → Position moves
the figure → handle-drag 50%→30%.

**Current branch merged into develop:** book-pipeline-v2 (merge 4165160, --no-ff);
review follow-ups in 3a7534a (GET visual-layout endpoint, paragraph-level
anchor_para + "Position in chapter" Composer control, dashboard snapshots).
Fluency de-calque validated faithful on 2 real mukhtasar chapters (both kept, 59
Arabic runs preserved) — see `_workspace/plan/book-pipeline-cutover.md`. Cutover
still held pending the full knob-matrix + PDF render loop.

**Current branch merged into develop:** book-pipeline-v2 (merge 4165160, --no-ff).

**What changed:** Book Pipeline v2 landed behind the `book_pipeline_v2` flag
(default OFF — zero behaviour change on develop until a book opts in). New Astro
surface: the **Book Composer** at `/studio/<slug>/compose` (view
`studio/[slug]/compose.astro`, loader `lib/reader/composer.ts`, client
`scripts/book-composer.ts`, styles `styles/book-composer.css`) where a human
places visual candidates (align/flow/width/drag-anchor/caption/page_fit), Save
writes `book/visual-layout.json` via `api/studio/visual-layout.ts`, and Generate
PDF calls `api/studio/generate-book-pdf.ts`. Assets served by
`api/studio/visual-asset.ts`. The PDF renderer (`render-book-pdf.mjs` +
`book-print.css` under `body.book-v2`) consumes the layout contract (floats for
wrap, centered for standalone, one-plate, page-fill) — all flag-scoped. Contract
mirror: `_visual_layout.py` ↔ `visual-layout.mjs` ↔ `composer.ts` anchorKey.

**Site verification:** `lint:views` clean, `astro check` 0/0/0, `npm run build`
succeeds, `node scripts/visual-layout.test.mjs` (12) green, and the Composer was
driven in-browser (desktop + mobile): place → configure → Save writes a valid
`book.visual-layout/v1` file → wrap clamps width to 50%. `html-view-challenger`
PASS (Level 1).

**Current translation-edition state:** `mukhtasar-ul-asar-2` has a rerendered
titled PDF in `content/Islamic/mukhtasar-ul-asar-2/book/` and the Google Drive
Podcast Library copy was refreshed by `build_book_pdf.py`.

**Site verification:** `node --check plan-dashboard/scripts/render-book-pdf.mjs`,
`npm run lint:views`, `validate_book_ready.py mukhtasar-ul-asar-2`, Poppler
page-by-page blank audit, and focused podcast regression tests all pass.

**Current Al Anwaar state:** vol-01 has a 27-entry glossary and Arabic script in
all 11 chapters. Ship validation passes all 14 gates, including G13
`arabic-script-in-chapters`.

**Prior Studio status carried from develop:** Session 32 reworked the Studio Arabic
review/editor shell, unified action panel, Noise tool, raw Arabic styling, reading
width, and left-gutter mark icons. Deferred design decisions remain: NarrativeScroll
theme exception/retheme, REQ-010 typography sweep, section ids/number markers,
figure wrappers, print/smooth-scroll/metadata polish, system-map density split, and
SpendChart dead-code removal.
