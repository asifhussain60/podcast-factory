# Handoff — Book Composer right-panel work (2026-07-21)

Paste the block below into a fresh Claude Code session in `~/PROJECTS/podcast-factory`.

---

## Prompt

I'm continuing work on the Book Composer's right-hand drawer in the Podcast Factory
Astro Site (`plan-dashboard/`). A previous session left the working tree dirty and
UNCOMMITTED — start by reading `_workspace/plan/composer-panel-handoff.md` and
`git status` before changing anything.

Follow the repo's standing rules: the Cortex HTML View Quality Standard applies to
everything under `plan-dashboard/`, and the work is not done until BOTH
`html-view-challenger` (static conformance) and `site-health-sentinel` (runtime +
visual QA) have run. **Those two agents have never run on any of this session's
work** — they are the outstanding gate on the whole change set.

### What already exists (do not rebuild)

The drawer is ONE panel with three surfaces — Tools (four icon tabs: Artifacts,
Refinement, Citations, Details), Companion notes, and the AI Scholar — chosen by a
floating button row at bottom-right, with the site's back-to-top control rightmost.
Key files:

- `src/pages/studio/[slug]/compose.astro` — markup: `.composer-grid[data-panel]`,
  `.composer-panel#cx-drawer`, three `.cx-surface` blocks, `.cx-fabs` button row
- `src/scripts/book-composer.ts` — drawer state machine (`SURFACES`, `setPanel`),
  persisted to `localStorage` key `cx-composer-panel`
- `src/scripts/panel-text-size.ts` — the −/+ text-size stepper. Writes
  `--panel-fs` (content) and derives `--panel-fs-title` (= content + 2px). One
  `localStorage` key `pf-panel-fs`, range 11–24, **default 15**
- `src/styles/book-composer.css` — `.composer-panel` declares BOTH panel tokens;
  `.cx-surface` only consumes them. **Do not re-declare `--panel-fs` on a
  surface** — a custom property declared on the consumer beats one inherited from
  an ancestor, which silently pins the text while the stepper's readout moves.
- Panel type scale: content `--panel-fs`, headings `--panel-fs-title`. Exempt by
  design and commented as such: icon glyphs (`.cx-tab`, `.cx-icon-btn`,
  `.gcp-launcher`) and the Citations type-specimen (`.bs-preview`, `.cx-cite-list`).
  A REQ-010 exception for these panels is recorded in `html-view-lint.config.json`.

Two traps that cost time last session, both worth knowing:
1. **The site's root font-size is 19.2px, not 16px.** `1rem` equals the reading
   floor, so any rem-based panel size lands a tier too high. Panel sizes are px.
2. **A React effect with `[]` deps runs against the FIRST render.** Panels whose
   first render is a "Loading…" shell must key the effect on loaded state or the
   mount silently no-ops.

### Four tasks

**1. Fix the overlapping tab labels — replace the inline reveal with a real popup.**
`.cx-tab-label` currently goes from clipped to `position: static` on
hover/focus/active, which widens that tab and collides with its neighbours (see
`.cx-tab-label` and `.cx-tab` in `book-composer.css`). Remove the inline reveal.
Build a proper hover/focus tooltip: positioned, non-layout-affecting, appearing
below the icon, with a small delay in, none out, dismissible on Escape, and
`aria-describedby` wiring so the accessible name is not duplicated. It must not
clip inside `.cx-surface` (which is `overflow: hidden`) — check that before
choosing an approach. Keep the label text in the DOM for assistive tech.

**2. Font + size controls for Arabic and English, in one clean interface.**
Today the Arabic face is chosen by PROVENANCE, not by the user: `readQuranicRuns()`
in `scripts/lib/book-html.mjs` reads `_system/book-arabic-audit.json` and stamps
`is-quranic` on runs the audit resolved against the canonical mushaf;
`quote-typography.css` then switches `--q-ar-face` on that class alone. Qur'anic
runs get KFGQPC Uthmanic (vendored byte-for-byte from quran.com — its EULA permits
distribution but FORBIDS modification, so never subset or re-encode
`public/fonts/uthmanic-hafs/*`); everything else gets Scheherazade New.

The English translation face is already user-chosen: four self-hosted faces
(EB Garamond, Cormorant Garamond, Crimson Pro, Lora) selected in the Citations tab,
persisted as `translation_font` in `book/citation-style.json`, applied as a
`tr-<font>` body class.

Design ONE coherent control surface covering: Arabic face, English face, and text
size — and decide deliberately whether the Arabic face should become user-selectable
at all, or stay provenance-driven with the picker offering only the NON-Qur'anic
face. Discuss the design with Asif before building; per-view redesigns are agreed
one page at a time. Note the size stepper currently governs PANEL chrome, while the
font pickers govern BOOK content — do not conflate the two in one control without
making the distinction visible.

**3. Link Companion cards to the chapter text, both ways.**
Each Companion note stores a `quote` (the highlighted passage — see
`CompanionPanel.tsx` and `lib/reader/companion/types.ts`); it renders in the card as
the yellow pill. Two behaviours wanted:
- **Mark the passage in the chapter.** The reader surface already has a highlight
  token pair for exactly this — `--reader-mark` / `--reader-mark-edge` in
  `book-reader.css`, declared as the single source of truth for the passage
  highlighter, and the LIVE Session reader already marks a note's quoted passage
  when it appears verbatim. Reuse that; do not invent a second highlight.
- **Scroll-sync.** As the chapter scrolls, the card whose passage is in view rises
  to the top of the Companion panel. `IntersectionObserver` over the marked spans is
  the natural mechanism; `site-chrome.ts`'s `initJumpNav` is an existing example of
  the pattern in this repo. Beware: the chapter scrolls the WINDOW while the panel
  scrolls internally (`.cx-surface` owns its own scroll), so the observer root and
  the scroll target are different elements.

**4. Run the gates.**
`npx astro check`, `npm run lint:views`, `npm test`, `npm run smoke`, `npx eslint .`
(one pre-existing error in `astro.config.mjs` — `'process' is not defined` — is not
yours). Then `html-view-challenger` and `site-health-sentinel`. Nothing from the
previous session has been committed; ask Asif before committing.

### Also outstanding from the previous session

- **Four Arabic vowelling proposals are pending review** at
  `/studio/the-master-and-the-disciple/arabic-review`. Gemini proposed, the skeleton
  gate passed them, no human has decided. Nothing has been written to `book.md`.
  One proposal chose PASSIVE `يُخْلَقْ` where the source is ambiguous — that is the
  judgement the review step exists for.
- The full session record, including the reasoning behind the Arabic decisions, is
  in `~/.claude/plans/review-podcast-factory-astro-bright-creek.md`.
