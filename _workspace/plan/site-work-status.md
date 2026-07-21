<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT. Recover older entries from git history when needed.
-->
# Current work - status

**Last updated:** 2026-07-21 5:46 PM EST (Composer authority + honorifics)

**Newest — a Composer-authored chapter is no longer regenerated, and the
conflict warning finally means something.** Every model stage of
`compose_book_v2` (base compose, fluency, augment, re-voice) consults
`_book_edits.edited_chapter_keys` and passes an authored chapter through
untouched; `--force` still re-composes and warns first. The conflict signal was
structurally false — the Composer hashed the live `book.md` (introduction and
bridges included) while replay hashed the composed body from before either is
injected — so the pipeline now stamps `_system/composer-base.json` and the
Composer quotes that value back as `base_fingerprint`. The TS hash is deleted;
`anchor_key`/`anchorKey` is the only remaining mirror pair. New deterministic
pass `_honorifics.py` spells out the first honorific in the book and abbreviates
the rest. Eight audit findings closed alongside, including a seam de-dup that
deleted paragraphs with no record, a sidecar that discarded every prior edit on
a parse failure, and a superseded whole-book composer that clobbered `book.md`
when run. Site-side: `npm test` now reaches `src/` via a 40-line resolve hook
(`scripts/lib/ts-resolve-hook.mjs`, no new dependency), starting with
`book-md-write.ts` — the sole writer into `book.md`, previously untested.
Gates: pytest 1734, npm test 55, tsc clean, lint:views 0, eslint 0 errors,
smoke 32/32, ruff clean. Commit `0b52991`.

**Last updated:** 2026-07-19 8:20 AM EST (Supplications lane — PDF-only sibling)

**Newest — the Supplications category shipped as a standalone PDF-only lane.**
A fourth content bucket (`Supplications`) plus profile `islamic_supplication`
now produce a facing-column reading PDF (English left, Arabic/Urdu right) with
no episodes, audio, slides, or video. Built as a SIBLING of the podcast
pipeline, not a branch inside it: the ship gate hard-requires paired
`episodes/`, so the lane has its own driver (`scripts/podcast/supplication/`),
its own state file (`_system/supplication-state.json`), its own gates, its own
renderer (`render-supplication-pdf.mjs`), and its own stylesheet
(`supplication-print.css`). Every firewall file — orchestrator, `_progress`,
episode/ship gates, translation-edition composer, `book-print.css`,
`render-book-pdf.mjs`, `_augment_registry` — is byte-untouched, and an existing
Islamic book's PDF re-renders byte-identically (modulo PDF timestamps).
Site-side: four TS mirrors updated in one commit (`content-paths`, `live-index`,
the exhaustive `SHELF_META`, `PROFILE_TO_BUCKET`) plus a shelf accent; new shelf
renders with zero console errors. Integrity design: a unit's source text is
NEVER model-authored — models emit only line groupings and English, and Python
re-derives source from the immutable OCR record, so the verbatim guarantee is
structural. OCR diacritic fidelity was validated on a real vocalised Arabic scan
before building (1,435 tashkeel marks recovered, 1 invalid token in 968).
Gates: pytest 1642, astro 0 errors, lint:views 0, smoke 33/33, eslint 0 errors.

**Last updated:** 2026-07-18 2:20 PM EST (R2 hooks pass COMPLETE + audit fixes)

**Newest — all nine StudioEditor hooks extracted; post-chain audit clean.**
Hooks 4-9 landed one-per-commit (useStageApproval, useAiActions,
useTermCuration, useReplaceTool, useDenoiseTool, useAnnotations), each
byte-diff-verified + smoke 32/32 + browser-driven. StudioEditor
4605 → 2754 lines. Notable: the smoke gate caught a real TDZ constraint on
useAnnotations placement (StudioDecos reads actionsRef during useEditor's
synchronous first pass — hook must precede useEditor; composition order
documented in the file). repo-surgeon end-of-chain sweep: zero P0; its two
P1s + P2 fixed (Node snapshot generator now rebuilds the waves META array —
R0-R3 + Wave K render on the plan page; Wave K rekeyed to id:/name:; infra
librarian mirror no longer cites the deleted augmenter). R2 remaining tail
= R2f: JSX child-component splits + editor-coupled route envelope flips
toward ≤600. R4 go/no-go evidence gathered (277 sys.path files, 0 true
collisions left, the two phases/ import roots confirmed — but run_wave.py
is the R5 deletion candidate, so R5-first may dissolve R4's flagship bug);
decision with Asif. Gates: pytest 1658, astro 0, eslint 0 err, smoke 32/32.

**Last updated:** 2026-07-18 12:35 PM EST (Clean-code hardening R2+R3 tranche)

**Newest — R2+R3 executed on Asif's approval (option A), 16 commits pushed.**
R3 (pipeline) substantially complete: both basename collisions gone
(`_agent_invocations` rename + dead `knowledge/augmenter.py` deleted), +72
tests for the 5 untested critical modules (1 real bug fixed in
`_citation_verify` — unreachable 'failed' branch), framing registry (Spec 1)
completed, `_azure.py` split (824→500 + 4 siblings), `_translation_edition`
(1056→576) + `_slide_authoring` (999→569) split along genuine seams,
`intake_book` split DECLINED with recorded reasoning, stage-order drift fixed
(`_stage_gate` was missing the live `literary` stage), audit deferrals all
resolved. DR-005 grandfather list burned 24→21. Callable-DI sweep = recorded
remainder (R3h), sequenced with R4's go/no-go. R2 (site) in progress:
Pass 1 fully done (constants/types/markers/pickers extracted; 21/23 editor
fetches on apiFetch), renderers merged (61-file byte-diff, 0 mismatches),
both fat frontmatters extracted (`library-view.ts`, `studio-shelves.ts`),
CSS layered (`theme-*`/`studio-editor-*`), hooks 3/9 landed one-per-commit
with live browser verification (`useEditorPrefs`, `useAutosaveDraft`,
`useSectionDepth` — the exemplars for the remaining six: useStageApproval,
useAiActions, useTermCuration, useReplaceTool, useDenoiseTool,
useAnnotations). eslint gained `react-hooks/refs` ratchet-warn (compiler
analyzes extracted hooks but bailed on the giant component). All gates
green: pytest 1658 (post-dead-code delta), astro check 0, eslint 0 errors,
prettier clean, lint:views 0/0, smoke 32/32. NOTE: one leftover
`stash@{0}` from an agent's baseline check (superseded snapshot JSONs only —
safe to drop). R4 packaging go/no-go + R5 wave-engine decision await Asif.

---

**Last updated:** 2026-07-18 9:45 AM EST (Clean-code hardening R0+R1 executed)

**Newest — clean-code hardening plan, R0+R1 tranche shipped (7 commits on
`develop`, pushed).** R0: Ruff gate + whole-tree format baseline (pipeline,
`1c26f42`); ESLint+Prettier gates (site, `936291e`); enforceable DR-005
line-count gate with 24-file shrink-only grandfather list + lint wiring into
pre-commit/CI/Makefile (`7fd115c`). R1: Studio renames — `reader/poc/` →
`studio/editor/`, `StudioPoc`→`StudioEditor` (+ CSS class family),
`corpus-mock/`→`corpus/`, `corpus-mock-sample.ts`→`corpus-fallback.ts`,
css pairs (`0bddb02`); `src/lib/api-fetch.ts` shared typed client, 35 call
sites across 21 files migrated, `ai/etymology`+`ai/english-term` flipped to
the strict envelope, apiOk/apiError gained a headers param (`7a5cbb1`).
StudioEditor's 23 fetches + 9 editor-coupled envelope routes deferred to R2
BY DESIGN. Roadmap: `waves_refactor:` block in plan.yaml (R0-R5; R2-R5
pending_approval) + snapshots (`b7a722f`); the Node snapshot generator now
auto-discovers `waves_*` keys (was hardcoded — mirror-parity fix). Gates all
green: pytest 1592, astro check 0, eslint 0 errors, lint:views 0/0, smoke
32/32, browser drive of editor + composer clean. NOTE: machine-policy myth
corrected repo-wide — this is a personal machine, `npm install` works
(`f16aa70`). R2 (editor decomposition), R3-R5 await Asif's approval.

---

**Last updated:** 2026-07-18 5:40 AM EST (Repo audit remediation — groups 1-3)

**Newest — full repo audit + safe-batch remediation.** Report:
`docs/assessment/repo-audit-2026-07-18.md`. Three commits on `develop`
(`b42e700` security, `fa328d9` dead-code, `b606936` edge-drift). Site impact:
removed a 30-file dead island (the superseded chapter-reader UI + 6 uncalled
API endpoints + `SpendChart`); added `sites`/`explainers` to `content-paths.ts`
to match Python; corrected the `editorial.ts` mirror docstring. Gates green
(`astro check` 0 errors, `lint:views` clean). Also (options A+B, pushed):
fixed the pre-existing `test_etymology.py::test_build_pipeline_keeps_only_gated`
flake (test-isolation — stubbed the global corpus loaders; suite 1592 pass / 0
fail); repaired `.codex/hooks.json` (foreign path → repo-relative `.claude/hooks/`);
canonicalized the `docs-updater` agent spec (infra + `.github` mirror) and rebuilt
`infra/_README.md` to 23 agents. Remaining deferrals: WC8 staging trio (live
stage-order mirror), `knowledge/augmenter.py`, `classify_slides.py`, StudioPoc
`poc/` rename + split, wave-engine fate. See `docs/assessment/repo-audit-2026-07-18.md`.

---

**Prior — interactive Etymology AI action on the Book Composer (PDF) page.** _(2026-07-17 2:08 PM EST)_
Commit `d203599` on `develop` (follows the `c85f458`/`03f1d1d` corpus-augmentation
pipeline work same session). Highlight a word in the Book Composer prose editor →
click **Etymology** in the Refinement panel → one Gemini Flash call returns TWO
reviewed outputs shown in a `.cx-ety-card`: (1) a compact **transliterated inline
insert** (`gratitude (shukr, from the root sha-ka-ra — also shakir, mashkur)`) that
REPLACES the highlighted word in the reading-edition prose and autosaves to
`book.md` → so it flows into the generated PDF; and (2) a richer **chapter-aware
companion note** in **voweled Arabic script** (شُكْر · ش-ك-ر · شَاكِر with an example
· مَشْكُور) filed to the Companion Panel as a new `etymology` note-kind, explaining
each derivative with an example in the KSESSIONS/KQUR teaching voice. New
`POST /api/ai/etymology` (two-way English↔Arabic; local KSESSIONS/KQUR root-grounded
then Gemini Flash; inline stays Latin-only, companion is Arabic-with-diacritics —
the two script rules are locked separately in the prompt). Files: `api/ai/etymology.ts`
(new), `scripts/book-composer.ts`, `styles/book-composer.css`, `companion/registry.ts`.
Gemini 2.5 Flash needs `thinkingBudget: 0` or thinking tokens starve the JSON output
(caused a first-pass "unparseable output" — the documented fix). Gated: `astro check`
+ `lint:views` clean, `site-health-sentinel` PASS (32 routes, desktop+mobile, focus
+ Arabic contrast verified), `html-view-challenger` Level 2 conformant (fixed 2
REQ-048 a11y MUSTs: focus-visible on the new buttons + label↔input associations).
Compose route is light-only by design (its Light/Sepia/Dark toggle is the editor
paper, not a page theme). Podcast/PDF batch etymology (`_etymology.py`, 12 seed atoms)
remains the automated peer path; the interactive Studio button is the human-in-loop
creator.

**Earlier — Composer header redesign, Layout mode retired, autosave made shared infrastructure.**
Commit `f1c2936` on `develop`, pushed (follows `13d34c3`/`7018dea`, the Phase 3 Preview
work below, same session). Driven by live feedback on the shipped Preview screenshots —
Asif didn't like the large vertical pill stack in Compose's header. (1) **Header row**:
Preview/LIVE Session/Reading edition/Edit & Enrich moved from a tall vertical stack beside
the title to a compact horizontal row of small rectangular buttons above it, scoped to
Compose only (new `.cx-hdr-btn`/`.cx-header-actions` classes — the shared `.lib-studio-link`
pill other Studio pages use is untouched). This surfaced a REAL bug worth remembering:
reusing `.lib-hero-main` (`flex: 1 1 24rem`, tuned for its normal ROW-direction layout)
inside the new COLUMN-direction header made the 24rem flex-basis apply to HEIGHT instead of
width, padding the block out with ~330px of blank space below its actual content — fixed
with a scoped `flex: 0 1 auto` override. General lesson: flex-basis silently changes axis
meaning when a shared class's container direction changes; check computed `flexBasis`, not
just visual inspection, when a reused flex child looks oversized/undersized in a new home.
(2) **Reading edition removed, LIVE Session pushed far right**: the top-row "Reading edition"
button is gone (redundant with Companion Tool, below); LIVE Session moved to the row's far
right edge (`margin-left: auto`), separated from Preview/Edit & Enrich. (3) **Layout mode
retired** (explicit confirmation via AskUserQuestion after flagging the regression): the
Layout/Edit toggle is gone, Edit is now the sole permanent mode, and the "Layout" button's
old slot is a "Companion Tool" link to the reading edition instead. Figure placement/resize
has no UI home in Compose until Phase 4 (Edit-canvas merge, still queued — unaffected
otherwise). (4) **New `scripts/autosave.ts`**: factored the prose editor's existing
debounced-save pattern (single-flight, trailing re-save, Editing…/Saving…/Saved/Couldn't-save
states) into a shared, reusable module per Asif's explicit ask ("a data structure that can do
this globally in the app") — the figure-layout save (previously a manual "Save layout"
button, now fully autosaved) is the second consumer, and the prose editor was refactored onto
the SAME module rather than left duplicated. Status pill gained icons — spinning loader while
saving, a checkmark that pops in on save, warning + inline Retry on failure, respects
`prefers-reduced-motion`. Verified live end-to-end: placing a figure autosaved with a real
`PUT /api/studio/visual-layout` 200 and the pill reaching "Saved". One process note: while
testing the remove-a-figure path, nearly clicked the palette's delete-artifact-from-disk
button (not an unplace control — Layout's own remove-placement UI is gone too); caught it at
the confirmation dialog and cancelled before anything was destroyed — worth remembering when
testing this area again, since there is currently no non-destructive way to unplace a figure.
Gates: `astro check` / `lint:views` / `npm run build` / `npm run smoke` (32/32) all clean.

**Newest — Phase 3 Preview: live page-image render, zoom, Generate PDF moved off Compose.**
Commit `13d34c3` on `develop`, pushed. Shipped in a materially different shape than the
original Phase 3 plan (`~/.claude/plans/a-no-this-is-mossy-comet.md`) after two dead ends,
both discovered mid-build, not in planning: (1) live in-browser pagination via vendored
Paged.js hung/crashed on this environment's Chromium on every real test — including a
trivial two-paragraph, zero-stylesheet case with no book content involved — an unresolved
Paged.js↔modern-Chromium gap (Chromium only gained native paged-media support, print-only,
in v131; Paged.js's last stable release predates that); (2) an intermediate design embedding
the canonical book.pdf in an `<iframe>` was byte-perfect but wrong for "scroll the whole book
on the page" (a native PDF viewer owns its own internal scroll region) and only ever showed
the last-published file, not live edits — which is what Asif actually asked for once he saw
it ("this should NOT be the actual PDF... I want to see how the PDF will render based on the
changes I make in Compose").
**Landed design:** `/studio/<slug>/preview` renders LIVE from whatever is currently saved in
`book.md`/`visual-layout.json`/`citation-style.json` — a scratch PDF via the exact same
`render-book-pdf.mjs` engine the real PDF uses (auto-detected staleness vs. those three
source files, regenerated only when needed), rasterized page-by-page with `pdftoppm` and
cached under `book/_preview-cache/` (gitignored), then stacked as plain `<img>` elements in
normal document flow so the browser's ONE scrollbar carries the whole book — no boxed/nested
scroll region. A sticky Zoom slider (30-90% of the container, hard-capped at 90% per Asif's
ask) controls page width client-side, persisted to `localStorage`. The HTML-assembly logic
shared by the PDF renderer and Preview is factored out of `render-book-pdf.mjs` into
`scripts/lib/book-html.mjs` (single source of truth — REQ-SC-022 — verified byte-for-byte
regression-safe against the prior renderer via an A/B PDF diff on a real 117-page book before
landing). Compose's Output tab is REMOVED; "Save layout" moved next to the Layout/Edit mode
toggle; "Generate PDF" moved to Preview behind a themed `confirmDialog()` (never a native
`confirm()`) — it still writes the canonical `book/book.pdf` via the unchanged
`/api/studio/generate-book-pdf` endpoint, now the ONLY thing that touches that file. Two
sizing bugs caught and fixed mid-session, both worth remembering: (a) a page-image `max-width`
in `rem` silently rendered ~1.2x larger than intended — this site's `html` font-size is
`19.2px` (REQ-010 reading floor), not the standard `16px`, so `rem` sizing on raster/layout
widths needs a plain `px` value or an explicit note; (b) "too zoomed in" from Asif meant "too
large/magnified," not "too small" — the opposite of my first read; when a size complaint is
ambiguous, use a fixed reference in the user's own screenshot (here: the browser's own chrome,
which doesn't scale with page zoom) to measure the actual direction before changing anything.
Gates: `astro check` / `lint:views` / `npm run build` / `npm run smoke` (32/32 routes) all
clean; `preview-fidelity-challenger` (the Phase-0 parity agent) was never installed as a
blocking gate — parity between Preview and the PDF is now true by construction (same
renderer), so the page-structure-diff machinery it was meant to run is moot. Not yet done:
Phase 4 (Edit-canvas merge, Layout's figure controls folding into Edit) — unaffected by this
work, still queued next per the parent plan's risk ordering. A `repo-surgeon --scope podcast`
post-merge audit is due per standing convention before the next merge/push to `develop`.

Book Composer UX trio (autosave, reading-edition link, themed dialog).
Local commit on `develop` (not yet pushed). Files: `compose.astro`, `book-composer.ts`,
`book-composer.css`, new `confirm-dialog.ts`. (1) Composer header gains an "Open reading
edition" link → `/studio/<slug>/book`, and the misleading "Read" mode toggle is renamed
"Layout" (it's the figure-placement + preview surface, NOT a reader — repurposing it was
rejected as a regression). (2) The prose editor now AUTOSAVES: debounced (~1.2s) silent
PUT to `/api/studio/book-md`, single-flight + trailing re-save, a status pill (Editing… →
Saving… → Saved <time> → Couldn't save + Retry); the manual "Save prose"/"Cancel" buttons
are removed. Because the page holds the original server render in memory, LEAVING an edited
chapter (to Layout or another chapter) reloads once to re-render — and that reload now
PRESERVES the chapter + Edit mode (fixes the old always-reset-to-chapter-1 quirk) via
`sessionStorage` (`cx-restore-chapter` / `cx-restore-edit`). (3) New vanilla promise-based
`confirmDialog()` (`.cx-confirm-*`, `--c-*` tokens, focus trap, Esc/backdrop cancel, focus
restore, danger variant) replaces the native `confirm()` on the discard-edits + delete-
artifact paths; with autosave the discard prompt only fires on a genuine save FAILURE.
Gates: html-view-challenger PASS (full AA; added dialog `aria-describedby` per its one
SHOULD), site-health-sentinel PASS (no defects; confirmed the scrim already dims the nav).
Verified in chromium with the save endpoint MOCKED — book.md never mutated. Follow-up
DONE: the last native `window.alert()` (delete-FAILURE path) now uses a themed one-button
`noticeDialog()` (role=alertdialog, aria-describedby, danger); the now-implemented
`_workspace/plan/composer-ux-plan.md` was removed. Broader Studio redesign Phase 3
(Preview/Paged.js — needs a one-file download OK) + Phase 4 (Edit-canvas merge) remain.

**LIVE Session reworked: single-scroll reader + passage-level Companion.**
Local commit on `develop` (not yet pushed). Supersedes the Phase-2.5 pagination below.
`/studio/<slug>/live` is no longer paginated — it now stacks every chapter as its own
numbered paper "sheet" down ONE window scrollbar (no inner scrollbars): centered reading
toolbar, balanced margins, ~70ch measure, and a sticky right Companion. The Companion is
now PASSAGE-level: a scroll-spy shows exactly ONE card — the note for the sentence you're
reading — and highlights that verbatim sentence in YELLOW (`.lsv-hl.is-active`, per-paper
`--lsv-mark`); non-active passages are invisible; no inner companion scroll. Data: added a
verbatim `quote` field to companion notes (`types.ts`/`store.server.ts`; distinct from the
`anchor` card-title label); pre-filled 27 real chapter sentences (verified verbatim in
book.md) across the 8 M&D chapters; 5 illustration-only notes intentionally have no quote.
Editor: the Companion note form (`CompanionPanel.tsx`) gained a "Capture passage" control
(select prose → stored as `quote`), the `anchor` field is relabeled "Card title", and note
cards show a yellow passage pill (`CompanionCard.tsx`). Verified in real chromium (reader
highlight + editor capture + API persist round-trip); `astro check` 0 errors, `lint:views`
clean. Gates: BOTH PASS. site-health-sentinel PASS (fixed one mobile defect — the
"Contents" button clipped at ~360-390px; `flex-wrap:wrap` on `.lsv-topbar-left`).
html-view-challenger PASS on DoD + theme after fixes: a keyboard MUST (the Capture button
was mouse-only → now onClick, keyboard-accessible), 2 aria SHOULDs (hint `role=status`;
dropped the verbose scroll-driven live-region on `#lsv-explain-body`), and tokenizing the
highlighter into one shared `--reader-mark`/`--reader-mark-edge` pair (in book-reader.css)
referenced by BOTH the reader highlight and the editor pill (no `--c-*` theme change). Fix
commit follows `d97c1cf`. Known pre-existing debt: HEAD stores note em-dashes escaped
(`—`) while the store writes them literal — left as-is.

**Earlier — Phase 2.5: LIVE Session was a Kindle-style e-reader (now superseded above).**
Commits `757957e` + `64c0422` on `develop`. `/studio/<slug>/live` now paginates the book into
screen-sized pages (CSS multi-column + translateX) turned one at a time (flip buttons,
Arrow/Page keys, swipe); a ResizeObserver re-paginates on layout/font/resize and reveals
after a stable measure (no pre-font flash). Adds a reading toolbar (font, size stepper,
paper Light/Sepia/Dark — same reading-paper colours as the composer), a TOC drawer that
jumps to any chapter, justified body + left-aligned accent headings, tighter spacing,
Arabic scaled 1.4x, and note-anchor highlighting (verbatim best-effort). Gated:
html-view-challenger PASS Cortex L1 + SC-CLEAN, site-health-sentinel PASS (fixed a
mobile large-font heading clip + note-card keyboard a11y). Remaining: Phase 3 Preview
(needs a one-file Paged.js download OK) and Phase 4 Edit-canvas merge.



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
