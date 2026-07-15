<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT. Recover older entries from git history when needed.
-->
# Current work - status

**Last updated:** 2026-07-15 2:42 PM EST (Studio UX redesign Phases 0-2 shipped)

**Latest — Composer/Preview/LIVE-Session redesign, Phases 0-2 on `develop`.**
Four commits (`b6685d5`, `bcfe7db`, `7b1c584`, `04e2bcf`) toward a 4-phase Studio UX
redesign (plan: `~/.claude/plans/a-no-this-is-mossy-comet.md`). **Phase 0** — durable
contract: `docs/standards/studio-composer-quality.md` (REQ-SC-*), skill
`skills-staging/studio-composer/SKILL.md` (registered), deterministic Preview↔PDF
parity probe `plan-dashboard/scripts/preview-fidelity-check.mjs` (PF-* ids; PDF side
live via pdftotext, preview side is a guarded Phase-3 seam) + `preview-fidelity-challenger`
agent, and `/studio/<slug>/live` wired into the smoke + sentinel manifests. **Phase 1** —
"Chapters" tab restyled as a `.lib-tab-cta` pill matching "PDF Generator"; a new
"LIVE Session" pill on the overview tab row + composer header. **Phase 2** — new LIVE
Session view `/studio/<slug>/live` (`live.astro` + `live-session.css` own identity,
reuses `book-reader.css` prose): reading column + a right-hand read-only explanation
panel that scroll-syncs to the in-view section and shows that section's Companion
notes; a bucket-filterable, multi-volume-nested book picker sourced from `listContent()`
(`live-index.ts` + `live-session.ts`). Gated: html-view-challenger PASS Level 1,
site-health-sentinel PASS, 31/31 smoke clean. **Remaining: Phase 3** (rename Read→Preview,
whole-book paginated preview reusing `book-print.css` via vendored Paged.js — needs a
one-file download OK) and **Phase 4** (full-merge the Edit canvas: text + figure
place/resize in one surface, inspector Edit-only — the highest-risk rework).

**Prior — Editor UX parity across both editors + a durable null-hook fix.**
Three commits on `develop` (`efa86c2`, `36149ea`, `aa2f544`). (1) **Book Composer
editor** (`/studio/<slug>/compose`, `book-composer.ts` + `book-composer.css`) is
now a word-processor-style editing surface: a framed editor card with a
`:focus-within` accent ring and a tinted toolbar header; a **font · size · B/I/U**
toolbar (font selector Sans/Serif/Lato/Inter/Mono/Dyslexic, a text-size stepper,
B/I/U + H/quote/list); **Kindle-style paper themes** Light/Sepia/Dark; the writing
area fills the column and **justifies** (headings excluded); a white full-width
hero banner with a full-width description. (2) **Edit & Enrich editor**
(`StudioPoc.tsx` + `studio-poc.css`) got the SAME reading-comfort controls
(font/size/paper) + justified full-width prose, as React state persisted to the
SAME `cx-editor-*` localStorage keys so a choice carries between both editors; the
picked Latin face is PREPENDED to the mixed-script ProseMirror stack so Arabic
still falls through to Amiri; the B/I/U bar was intentionally NOT ported
(StudioPoc has its own mark tooling). (3) **Shared fonts**: new
`src/styles/editor-fonts.css` self-hosts Inter/Lato/OpenDyslexic (WOFF2 400/700 +
OFL under `public/fonts/*`), imported by both editor pages (composer duplicate
removed). Editor-view controls are VIEW-ONLY — `book.md` carries no font/size, so
the printed book is unaffected; underline is editor-only (the reader's markdown
renderer escapes raw HTML, no underline syntax). (4) **Durable fix**:
`resolve.dedupe: ['react','react-dom']` in `astro.config.mjs` ended the recurring
"Cannot read properties of null (reading 'useContext'/'useRef')" island blanks
(a nested dep resolved its own React). Also cleared a stale/corrupt
`node_modules/.vite` optimize cache that had blanked Edit & Enrich mid-session.
**Verification**: `lint:views` clean, `astro check` 0 errors, `npm run build`
clean, and the headless smoke sweep is **30/30 routes clean** (was 29/30 with
`/corpus` failing before the dedupe). Visual sign-off via the browser tools was
deferred (they disconnected mid-session); the changes are CSS/state-scoped and
gate-verified.

**Prior — Site-health runtime gate shipped.** The site now has a RUNTIME/visual
peer to the static `html-view-challenger`, mirroring the book pipeline's
`book-challenger` (source) vs `book-render-challenger` (rendered) split. Two
layers, both using the already-installed Playwright (no `npm install`):
(1) **deterministic, zero model spend** — `plan-dashboard/scripts/site-health-smoke.mjs`
(`npm run smoke`) boots the dev server, visits every page route in headless
chromium, hard-fails on any console error / uncaught exception / failed request /
5xx; auto-fires from the re-purposed `Stop` hook
(`.claude/hooks/ui-reviewer-stop.sh`, formerly the disabled `ui-reviewer` stub)
whenever `plan-dashboard/` changed and a server is up on :4322. (2) **visual
judgment** — the new `site-health-sentinel` agent (both agent trees + registry;
installed to `.claude/agents/`) screenshots each surface at ~1440px + ~390px
across states via `scripts/site-health-shots.mjs`, judges pixels, fixes the
smallest in-pattern source change, re-gates `lint:views` + `astro check`,
converges ≤5, deletes its throwaway `.visual-qa/`. DoD line added to CLAUDE.md;
runs as a PAIR with `html-view-challenger`. Inaugural sweep: **29/29 routes clean
(0 console errors / 0 exceptions / 0 5xx); 0 actionable visual defects** across
architecture / library (desktop+mobile) / composer / reading edition / wisdom
empty-state. Two CONTENT observations surfaced (not agent-fixable): chapter-title
echoed as the first body line in the composer + reading edition; wisdom intro
counts (19/122/1,337) vs live 0/0/0 (likely local corpus-DB gap). Dark theme on
long-form architecture views stays light-bodied — consistent with the KNOWN
deferred theme-exception work, not a regression. NOTE: the agent registry is
fixed at session start, so `site-health-sentinel` is invokable via the Agent tool
from the NEXT session onward.

**Prior — Book Composer round 2.** Three follow-up groups landed
(plan: `~/.claude/plans/create-a-detailed-plan-piped-perlis.md`): (1) **Citations**
now center BOTH Arabic and translation with tighter translation leading
(line-height 1.35), across all four CSS layers (`book-styles`, `book-print`,
`book-reader`, `book-composer`). (2) **Editing** — the chapter opens directly in
the editor by default; the **Refinement tab is now AI text actions** (Rewrite /
Expand / Condense / Simplify / Explain) that call `/api/ai/rewrite` (+ new
`expand` mode, hardened JSON parse) and `/api/ai/explain`, showing an
accept/reject option popup and replacing the editor selection; figure layout
controls moved OUT of Refinement onto a floating `.cx-fig-card` on the selected
figure (Read mode). Chapter switching while editing is guarded with a discard
confirm. (3) **Artifacts** — hover-to-enlarge preview, per-item delete + AI-edit
icon buttons, and a "New AI image" box. Net-new backend:
`scripts/podcast/composer_visual.py` (Gemini `gemini-3.1-flash-image` generate +
image-to-image edit, reuses `_visual_candidates.write_index` + `_gemini_client`)
behind `api/studio/visual-op.ts` (spawn-Python, like generate-book-pdf). Delete
removes the index entry + unlinks the file. Real Gemini image spend (~$0.04/img,
authorized). Palette item refactored to a `role="group"` with a real place-button
+ sibling action buttons (fixed the challenger's nested-interactive a11y finding).
Gates: astro check 0/0/0, lint:views clean, build OK, html-view-challenger
PASS-WITH-CAUTION → the one a11y MUST fixed. Verified in-browser: centered verse,
default editor, Rewrite→3 options→accept-replaces, inline figure card, hover
preview, real Gemini generate (gen-1.png, 670KB) → delete round-trip (fixture
restored, no content/ mutations).

**Prior — Book Composer is now a chapter-scoped editing workspace.** Three
feature groups landed (plan: `~/.claude/plans/create-a-detailed-plan-piped-perlis.md`):
(1) **Shell** — chapter picker moved to the top-left of the preview, first
chapter default, only the selected chapter renders, header trimmed to "Edit &
Enrich" (dropped "Citation styles"/"Reading edition"), and a new **Citations**
tab after Artifacts (tablist: Artifacts · Citations · Refinement · Output).
(2) **Citations tab** — reuses the `.bs-*` predefined-style picker
(plain/scholarly/elegant, persisted via `/api/studio/citation-style`) + lists
this chapter's detected Quran/hadith citations (detected in `composer.ts` from
the `blockquote.quran` markup now emitted by `markdown.ts`). The Quran verse was
toned down across all three layers (`book-print.css`, `book-reader.css`,
`book-styles.css`): no box, minimal padding, Arabic at ~body scale in
`var(--c-ink)` instead of gold. Per-type distinct PDF rendering is deferred
(declined pipeline). (3) **Edit mode** — a Read/Edit toggle mounts the same
TipTap engine (`book-md-editor.ts`, `@tiptap/core` + StarterKit) on the selected
chapter, editing **book.md directly** (not chapter source — verified via the
compose chain that source edits never reach book.md) and saving the chapter's
section via new `PUT /api/studio/book-md` (surgical section replace, `.bak`
backup). NOTE: a manual `compose_book_v2 --force` would regenerate book.md and
overwrite direct edits; book.md is the last-mile reading edition so this is
acceptable. Gates: astro check 0/0/0, lint:views clean, build OK,
html-view-challenger PASS-WITH-CAUTION (Level 1). Verified in-browser: chapter
scoping, Citations detection (2 in ch.1), toned verse (body-ink), Edit mount +
surgical save round-trip (fixture restored).

**Prior — Book Composer preview is now truly WYSIWYG.** Closed the three
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
