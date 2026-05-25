# Podcast-reader polish + AI reading layer — 2026-05-25

**Status:** PROPOSED v2 — second-pass audit added 2026-05-25 after Asif provided a clearer screenshot.
**Branch:** `book/the-master-and-the-disciple` (per CLAUDE.md branch policy; merges to `develop` as part of the book's publish wave).
**Estimated execution:** ~3.5 working days from approval (Phase 1 grew by ~half a day because the second audit found markdown-parser gaps).
**Author:** Claude (Sonnet) — planning session 2026-05-25.

**Visual mockup:** see [view/podcast-reader-mockup.html](view/podcast-reader-mockup.html) — a hardcoded preview of the post-Phase-1+2 chapter view.

---

## Context

Asif reviewed the chapter view at `localhost:4321/develop/the-master-and-the-disciple/chapter/ch02-…` and noted:

1. The Arabic toggle does nothing visible.
2. Paragraph spacing (`<p>` margin-bottom) is missing.
3. He wants visual reading enhancements for long scholarly chapters, leveraging an AI layer (he proposed Google's Gemini API).
4. He wants a reader-settings panel matching the journal repo's reader — font family, font size, colors, dark/light toggle.
5. He asked: "Is this the latest code? Check other branches."

### Branch check (answered)

🟢 `HEAD` on `book/the-master-and-the-disciple` matches `origin/develop` for `podcast-reader/` (zero diff). No newer reader work elsewhere:
- `origin/main` is behind by ~3,400 lines (expected — production lags).
- `origin/feature/kashkole-translation` is identical to HEAD for `podcast-reader/`.
- `origin/develop` is identical to HEAD for `podcast-reader/`.

This is the latest code.

### Bug diagnoses (answered)

🔴 **Arabic overlay** — `ArabicToggle.tsx` flips `<body data-arabic="on">`, and the chapter HTML carries `<span class="ar-overlay" data-script="حُجَّة">Hujjah</span>` for every glossary hit (verified — `content/drafts/the-master-and-the-disciple/_system/glossary.yml` has 40+ entries with Arabic script), but `global.css` has **zero rules** for `.ar-overlay` or `body[data-arabic="on"]`. The toggle works; the CSS to render the script never made it in. Roughly 10 lines of CSS to fix.

🔴 **Paragraph margin** — `ContractView.astro` contains a comment claiming `.prose-body` rules were "moved to global.css so they apply on chapter pages too." Grep confirms the move never happened. `.prose-body` has no rules at all. Roughly 10 more lines of CSS.

🟡 **Light/Dark toggle** already exists in the left sidebar header. The missing piece vs the journal viewer is the broader settings panel that bundles font/size/width/theme.

---

## Second-pass audit findings (2026-05-25)

After Asif provided a clearer screenshot, a second pass surfaced more issues. These are now integrated into Phase 1 (the visual ones) and a new Phase 1.4 (markdown parser gaps). Listed here as a reviewable inventory.

### Layout

1. **Reading column too narrow vs Reference Controls bar.** `.reading-column` constrains body to `--reading-measure: 70ch` (~830px at 19px), but the Reference Controls bar fills `max-w-5xl` (~1024px). The mismatch makes the body feel cramped under a wide header. **Asif's call:** body should match the bar width. **Trade-off flagged:** 70ch is the typographic sweet spot; ~95ch (matching the bar) is past comfortable for serif reading. The settings panel (Phase 2) will let users dial it back.
2. **No mobile view.** `lg:flex` on the TOC sidebar means everything below 1024px gets no sidebar and the chapter view is desktop-only. Phase 2 settings panel adds a bottom-sheet pattern; same drawer pattern should host the TOC on mobile.
3. **Right rail "density rail · Phase 2" placeholder** shows in dev as visible empty noise. Hide until populated (or absorb into Phase 3's right-rail Ask sidebar).

### Typography and prose

4. **Heading hierarchy not visually distinguished.** `## Where this chapter picks up` in the source markdown emits `<h2>` correctly, but `.prose-body h2` has no CSS, so Tailwind Preflight resets it to body size. Same for h3. Result: section headings look like plain paragraphs in the rendered view.
5. **No paragraph margin.** (Confirmed bug, already in plan.)
6. **Italics are very subtle.** Body italics carry semantic weight (the author marks key concepts like "outer of the call" or "architecture of creation itself") but at body-text weight they barely register. Consider a slightly different visual treatment — color, slight emphasis, or font swap to EB Garamond italic.
7. **Long h1 title wraps awkwardly mid-phrase.** "The Architecture of Creation: Will, Command, / and the Seven" — adding `text-wrap: balance` (now broadly supported) gives a cleaner break.
8. **Drop-cap missing.** (Already in plan.)
9. **First paragraph runs directly into title.** Title block has `mb-8` but the body still feels close because the title's leading is tight. A small top margin on `.prose-body > p:first-child` (or the drop-cap itself providing the visual gap) fixes it.

### Markdown rendering gaps (new — Phase 1.4)

10. **Blockquotes not supported.** The custom `markdown.ts` parser has no `>` handler. Ch02 contains at least two blockquotes (the Path of Eloquence sermon and the Quran citation). They render as plain paragraphs starting with `&gt;`.
11. **Lists not supported.** No `-` / `*` / `1.` handling. Any chapter with bullets breaks silently.
12. **Horizontal rule not supported.** No `---` handling.
13. **Links not supported.** `[text](url)` renders as literal text. Less critical for scholarly prose but a latent gap.

### Chrome and controls

14. **"Show Arabic" button truncated to "Show A…" in some viewports.** Header layout is tight; the breadcrumb on the left can push the toggle off-screen. Move the toggle into the settings panel (Phase 2) and replace the header pill with the "Aa" trigger.
15. **Legend "?" button is fixed top-right** and overlaps the "Show Arabic" pill in narrow viewports. Coordinate both into a single icon row inside the header.
16. **Light/Dark button label is "Light" + sun icon** showing the *current* state. UX convention shows the state you'd switch *to*. Either flip the label to "Dark" + moon, or replace with a stateless icon-only button. Phase 2 absorbs this entirely.
17. **Copy chapter button is up top.** It's most useful after reading. Move into a small floating bottom-bar (Phase 2) alongside other reader actions.
18. **No scroll-to-top.** Long chapters with no quick way back. Add a small floating button.
19. **No reading progress indicator.** Long chapters with no sense of position. Add a thin top-bar progress sliver (CSS `scroll-driven animations` — broadly supported now).
20. **No chapter-internal mini-TOC.** Chapter has 5+ `<h2>` sections that aren't navigable from anywhere. Add a chapter-internal TOC in the right rail (above the Phase 3 Ask sidebar).

### Footer nav

21. **Prev/next chapter links are plain text** at the bottom. Style as actual cards with chapter titles + arrows.

---

## Recommendation summary

**Three pushbacks before execution:**

1. The Arabic toggle and paragraph margin are bugs, not features. ~30 lines of CSS combined. Ship them in the first commit regardless of the rest.
2. **AI provider split: Gemini for fast inline calls (term definitions, TTS), Claude for nuanced work (section summaries, ask-the-book).** Your pipeline already runs Claude over this exact content with doctrinal context; routing the deeper queries to Claude reuses that competence. Gemini-only is acceptable but reduces nuance on Ismaili doctrine.
3. **Sequence: bug fixes → settings panel → AI.** The AI panel needs the settings chrome (popover/sheet pattern, persisted state, theming variables) as scaffolding. Building AI first means rebuilding the surrounding UX twice.

---

## Phase 1 — Bug fixes and prose polish

**Estimate:** ~1 day (grew from half a day after the second-pass audit added markdown-parser gaps and layout fixes).
**Files touched:** `podcast-reader/src/styles/global.css`, `podcast-reader/src/lib/markdown.ts`, `podcast-reader/src/pages/[worktree]/[book]/chapter/[chapter].astro`, `podcast-reader/src/components/layout/ThreePane.astro`.

### 1.1 Arabic overlay CSS

Add CSS gated on `body[data-arabic="on"]` that renders the `data-script` attribute next to each `.ar-overlay` span using the `--font-arabic-naskh` stack already loaded at the top of `global.css` (Amiri + Scheherazade New + Noto Naskh Arabic):

```css
.ar-overlay::after {
  content: "";
}
body[data-arabic="on"] .ar-overlay::after {
  content: " " attr(data-script);
  font-family: var(--font-arabic-naskh);
  font-size: 1.05em;
  font-style: normal;
  font-weight: 500;
  color: var(--color-arabic);
  unicode-bidi: isolate;
  direction: rtl;
  padding-left: 0.15em;
  letter-spacing: 0.01em;
}
/* Suppress inside Quranic refs — EB Garamond on .ref-quran fights the script. */
body[data-arabic="on"] .ref-quran .ar-overlay::after {
  content: "";
}
/* Dark mode contrast */
[data-theme="dark"] body[data-arabic="on"] .ar-overlay::after {
  color: var(--color-gold);
}
```

**Edge cases verified:**
- `unicode-bidi: isolate` prevents the RTL glyphs from breaking the surrounding LTR line (the existing `.se-prose .ar` rule uses the same pattern).
- Suppression inside `.ref-quran` avoids the EB Garamond font conflict.
- Dark-mode contrast handled.

### 1.2 Paragraph margin and prose rhythm

Add `.prose-body` rules in `global.css`:

```css
.prose-body p {
  margin: 0 0 1.1em;
}
.prose-body p:last-child {
  margin-bottom: 0;
}
.prose-body h2 {
  font-family: var(--font-body);
  font-size: 1.45em;
  font-weight: 600;
  margin: 2em 0 0.6em;
  line-height: 1.3;
  color: var(--color-ink);
  letter-spacing: -0.005em;
}
.prose-body h3 {
  font-family: var(--font-body);
  font-size: 1.2em;
  font-weight: 600;
  margin: 1.6em 0 0.4em;
  line-height: 1.35;
  color: var(--color-ink);
}
.prose-body blockquote {
  border-left: 3px solid var(--color-gold-deep);
  padding: 0.2em 0 0.2em 1em;
  margin: 1.2em 0;
  font-style: italic;
  color: var(--color-ink-secondary);
}
.prose-body blockquote p {
  margin: 0.3em 0;
}
.prose-body em {
  font-style: italic;
}
.prose-body strong {
  font-weight: 600;
}
.prose-body hr {
  border: none;
  border-top: 1px solid var(--color-rule-default);
  margin: 1.5em 0;
}
```

### 1.3 Two polish touches

```css
/* Subtle drop-cap on the first paragraph */
.prose-body > p:first-child::first-letter {
  font-family: var(--font-ref-quran); /* EB Garamond */
  font-size: 3.2em;
  float: left;
  line-height: 0.9;
  padding: 0.05em 0.08em 0 0;
  color: var(--color-gold-deep);
  font-weight: 500;
}
/* Thin gold rule below chapter title */
/* (Apply by adding <hr class="gold-hairline" /> after the title in [chapter].astro) */
```

### 1.4 Reading column width

Asif requested: body content should span the same width as the Reference Controls bar. Change `--reading-measure` from `70ch` to `none` (or `100%`) on the chapter page only, so it inherits `max-w-5xl` from the parent `<main>`. Keep 70ch as the default for OTHER prose surfaces (contracts, drafts) that don't have a bounding container.

```css
/* In global.css */
.reading-column--wide {
  max-width: none;
}
```

```astro
<!-- In [chapter].astro -->
<article class="reading-column reading-column--wide mx-auto">
```

Trade-off noted in audit: 70ch is the typographic optimum. Phase 2's settings panel lets users dial back to 70ch / 80ch / wide.

### 1.5 Heading hierarchy

Add `.prose-body h1`, `.prose-body h2`, `.prose-body h3` rules (already covered in §1.2 above but called out explicitly since these turned out to be the biggest visual bug — section headings render as plain text today because Tailwind Preflight reset them and no rule replaced the reset).

### 1.6 Header chrome tidy-up

- Move the "Show Arabic" toggle out of the header into the Phase 2 settings panel. Replace with an "Aa" trigger.
- Collapse the Legend "?" button into the same icon row inside the header so they don't fight for the same top-right pixel.
- Remove the right-rail placeholder ("density rail · Phase 2") when no rail content is mounted; Phase 3's Ask sidebar replaces it.

### 1.7 Header rhythm

Add `text-wrap: balance` to the chapter title h1 so long titles break cleanly:

```css
.prose-body h1, header h1 {
  text-wrap: balance;
}
```

Add a small leading-spacer between the header block and the body (`.prose-body > p:first-child { margin-top: 0.4em; }`) so the body doesn't crash into the title rule.

### 1.8 Reading progress sliver

Thin top-bar showing scroll progress through the chapter. CSS scroll-driven animations:

```css
@supports (animation-timeline: scroll()) {
  .reading-progress {
    position: fixed; top: 0; left: 0; right: 0; height: 2px;
    background: var(--color-gold-deep);
    transform-origin: 0 50%;
    animation: progress-grow linear; animation-timeline: scroll(root);
  }
  @keyframes progress-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
}
```

No JS, no library. Adds 8 lines.

### 1.9 Markdown parser gaps (new sub-phase)

Extend `podcast-reader/src/lib/markdown.ts` to handle:

- **Blockquotes:** lines starting with `>` group into `<blockquote><p>…</p></blockquote>`. Multi-line blockquotes collect until a non-`>` line.
- **Lists:** `-` / `*` / `+` for `<ul>`, `1.` / `2.` for `<ol>`. Single-level only (no nesting) — sufficient for chapter prose.
- **Horizontal rule:** `---` or `***` on its own line → `<hr>`.
- **Links:** `[text](url)` → `<a>`. Anchor at the existing markdown parser's inline pass.

Each is ~10 lines. Together ~40 lines added to `markdown.ts`. Test against ch01 + ch02 + a synthetic chapter that includes all four constructs.

### 1.10 Phase 1 acceptance

- Pressing "Show Arabic" reveals Arabic script next to every glossary phonetic on the page (and the toggle moved into the Phase 2 settings panel — see §2.3).
- Paragraphs have visible vertical separation (~17px at default size).
- Section headings (`## ...`) render at clear visual hierarchy — distinct from body, hadith ribbons, and Quran refs.
- Chapter title has a gold hairline under it, balances cleanly when long, and the first paragraph starts with a drop-cap.
- Body content spans the same width as the Reference Controls bar.
- Blockquotes (`>` in source markdown) render as styled blockquote blocks. Lists, HR, and links also render correctly.
- A 2px gold reading-progress sliver tracks scroll position at the top of the viewport.
- Dark mode still readable for all of the above.

---

## Phase 2 — Reader settings panel

**Estimate:** ~1 day.
**Pattern:** iOS Reader / Instapaper "Aa" button. Single discoverable trigger; popover on desktop, bottom sheet on mobile. Persists to localStorage and applies via CSS custom properties on `<html>`.

### 2.1 Controls

| Control | Options | Default | CSS variable |
|---|---|---|---|
| Font family | Source Serif 4, EB Garamond, Iowan Old Style, Charter, Inter (sans) | Source Serif 4 | `--font-body` (override) |
| Font size | 16 / 18 / 19 / 21 / 23 px (5-stop slider) | 19px | `--reading-size` |
| Line height | Compact 1.5, Comfortable 1.7, Airy 1.9 | 1.7 | `--reading-line-height` |
| Reading width | Narrow 60ch, Medium 70ch, Wide 80ch, Full | 70ch | `--reading-measure` |
| Theme | Light, Sepia, Dark, High contrast | Light | `data-theme` attribute |
| Reset | Button | — | — |

### 2.2 Storage shape

```ts
// localStorage["podcast-reader:reader-settings"]
{
  schemaVersion: 1,
  font: "source-serif-4" | "eb-garamond" | "iowan" | "charter" | "inter",
  size: 16 | 18 | 19 | 21 | 23,
  lineHeight: 1.5 | 1.7 | 1.9,
  width: 60 | 70 | 80 | -1,  // -1 = Full
  theme: "light" | "sepia" | "dark" | "high-contrast"
}
```

Existing localStorage keys are preserved (`podcast-reader-theme`, `podcast-reader:arabic-overlay`) for backward compatibility — Phase 2 reads them on first load and migrates into the new blob.

### 2.3 UI placement

- **Replaces** the standalone `ThemeToggle.astro` in the left sidebar header with a single "Reader settings" link.
- **Adds** an "Aa" pill to the top header next to the existing Arabic toggle (so it's discoverable on the chapter view without expanding the sidebar).
- **Desktop:** clicking either trigger opens a 320×440 popover anchored to the trigger.
- **Mobile (< md / 768px):** bottom sheet with handle and tap-to-dismiss backdrop.
- **Keyboard:** `cmd+,` opens; `Escape` closes.

### 2.4 Themes

| Theme | Page bg | Ink color | Notes |
|---|---|---|---|
| Light | `oklch(98.2% 0.004 75)` (current) | `oklch(21% 0.012 60)` | No change |
| Sepia (new) | `oklch(95% 0.04 75)` warm cream | `oklch(28% 0.04 50)` sepia | Lighter than dark mode, warmer than light |
| Dark | `oklch(16% 0.02 250)` navy (current) | `oklch(94% 0.008 75)` cream | No change |
| High contrast (new) | Pure white (`#FFFFFF`) | Pure black (`#000000`) | Accessibility option |

### 2.5 Implementation

**New files:**
- `podcast-reader/src/components/reader/ReaderSettings.tsx` — popover/sheet React island.
- `podcast-reader/src/lib/reader-settings.ts` — defaults, storage shape, `applySettings(settings)` DOM function, migration from legacy keys.

**Edited files:**
- `podcast-reader/src/components/layout/ThemeScript.astro` — extend the early-load script to apply the full settings blob (not just theme) so there's no FOUC.
- `podcast-reader/src/components/layout/ThreePane.astro` — replace `<ThemeToggle />` with `<ReaderSettings client:load />` trigger; render the panel via portal-style absolute positioning.
- `podcast-reader/src/styles/global.css` — sepia and high-contrast theme blocks; bind `--reading-*` variables to the settings.
- `podcast-reader/src/components/layout/ThemeToggle.astro` — delete (absorbed into ReaderSettings).

**Behaviors committed without further asking:**
- Settings persist globally across all books — one reader, one preference. Per-book preferences add complexity for marginal value.
- Defaults match today's appearance so existing screenshots don't drift.
- Settings apply instantly on change (no Save button); changes that risk layout shift (font size, line height) animate over 150ms.
- Reset button restores defaults without confirmation prompt (it's recoverable via re-customization).

### 2.5b Other chrome added in Phase 2

To absorb the rest of the second-pass-audit chrome findings:

- **Floating bottom action bar** (right side, sticks above the viewport bottom): Copy chapter, Scroll-to-top, Open settings. Hides on scroll-down, shows on scroll-up.
- **Chapter-internal mini-TOC**: right rail (above the Phase 3 Ask sidebar) lists every `<h2>` in the current chapter as clickable anchors with active-section highlighting via `IntersectionObserver`. Collapsible.
- **Prev/next chapter cards** at the bottom: replace plain text with card-style buttons that show the next chapter's title in proper body font, with a small chapter-number badge.

### 2.6 Phase 2 acceptance

- "Aa" button in the header opens a settings popover (desktop) / bottom sheet (mobile).
- Changing any control updates the page live without reload.
- Settings persist across navigation and across browser sessions.
- Sepia and high-contrast themes work end-to-end including refs, glossary overlay, and code blocks.
- Existing Light/Dark localStorage key is migrated into the new schema on first load (no broken state for users who have already toggled dark mode).
- `cmd+,` opens the panel; `Escape` closes it.

---

## Phase 3 — AI reading layer

**Estimate:** ~1.5 days.
**Provider split:** Gemini Flash for fast inline (definitions, TTS). Claude Haiku for short nuanced calls (section summaries). Claude Sonnet for deeper conversations (ask-this-chapter). All optional; all behind explicit user action; no background calls.

### 3.1 Term-definition popover (Gemini Flash)

**Trigger:** Hover-and-pause (300ms) or click on any `.ar-overlay` glossary span (the same spans we fix in Phase 1).
**Payload:** 200ms popover showing phonetic + Arabic + 1-sentence English gloss. "Read more →" expands to a 3-sentence contextual definition.
**Model:** Gemini Flash for sub-second response.
**Cache:** localStorage key `podcast-reader:term-cache:<book-slug>` keyed by phonetic → definition object. Second visit is instant and free.
**Why Gemini here:** the bottleneck is latency, not nuance. Term definitions are factual / dictionary-level.

### 3.2 Section summarizer (Claude Haiku)

**Trigger:** A "✦" button in the left gutter of each `<h2>` and at the chapter title.
**Payload:** 2–3 sentence summary as a callout below the heading.
**Model:** Claude Haiku.
**Cache:** localStorage key `podcast-reader:section-summary:<book>:<chapter>:<section-hash>`. Section hash is the SHA-1 of the rendered text under that heading.
**Why Claude here:** doctrinal nuance matters. Gemini tends to flatten Ismaili specifics into generic Islam.

### 3.3 Ask-this-chapter sidebar (Claude Sonnet)

**Location:** Right rail (`ThreePane.astro` already has a `density rail · Phase 2` placeholder slot — literally waiting for this).
**Behavior:** User types a question in a small chat box. Claude Sonnet answers, grounded in the current chapter's full text. Citations are inline links back to anchors in the chapter. Conversation persists for the session; cleared on chapter change.
**Why Claude Sonnet:** longest context, best citation discipline, best nuance on scholarly text.

### 3.4 Read-aloud (Google Cloud TTS — Studio voices)

**Location:** Sticky bottom playback bar (collapsible).
**Controls:** Play/pause, speed (0.75x / 1x / 1.25x / 1.5x), voice picker (Studio voices — Neural2-G, etc.).
**Behavior:** Reads from current scroll position. Optional auto-scroll highlights the currently-spoken sentence. Phonetic Arabic terms get pronounced using the `audio_phonetic` field already in `glossary.yml` (e.g. "JAH-far ibn man-SOOR al-YAH-man") — we feed TTS the audio_phonetic instead of the written phonetic so prosody is right.
**Why Google here:** Studio voices are the best in the industry for English at this price point.

### 3.5 Implementation

**LLM routing.** Single `src/lib/ai-client.ts`:

```ts
export async function geminiFast(prompt: string, opts?): Promise<string>
export async function claudeHaiku(prompt: string, opts?): Promise<string>
export async function claudeSonnet(prompt: string, opts?): Promise<string>
export async function tts(text: string, voice: string): Promise<Blob>
```

Each function reads its API key from `localStorage["podcast-reader:api-keys"]`, calls the provider's HTTP API directly from the browser, and logs the call to a local debug console (no telemetry leaves the machine).

**API key storage.** First iteration: user pastes Gemini and Claude keys into a "Keys" tab in the settings panel; stored in localStorage. Acknowledged risk: keys are in cleartext in the browser. **Follow-up (out of scope here):** proxy through a Cloudflare Worker so keys live server-side. CLAUDE.md retired the previous Worker scaffold, so this needs its own decision.

**New files:**
- `src/components/reader/TermPopover.tsx`
- `src/components/reader/SectionSummarize.tsx`
- `src/components/reader/AskChapter.tsx`
- `src/components/reader/ReadAloud.tsx`
- `src/lib/ai-client.ts`
- `src/lib/ai-cache.ts` — localStorage cache helpers

**Edited files:**
- `src/pages/[worktree]/[book]/chapter/[chapter].astro` — wire the four islands in.
- `src/components/layout/ThreePane.astro` — expose the right-rail slot (already there as placeholder).
- `src/components/reader/ReaderSettings.tsx` — add "Keys" tab.

### 3.6 Cross-chapter discovery (deferred)

Considered: "Where else is X discussed across the book" via Gemini embeddings. Requires an embedding-and-store pipeline of its own — not a small addition. Flagged for **Phase 4** if Asif wants it later.

### 3.7 Phase 3 acceptance

- Hovering a glossary term shows a popover with definition within 1 second on cold cache, instant on warm cache.
- Clicking "✦" next to a heading produces a 2–3 sentence summary that's faithful to the section (sanity-check by Asif on the first three chapters).
- Right rail "Ask" answers a chapter-grounded question with at least one inline citation.
- Read-aloud plays from any point, correctly pronounces glossary terms via `audio_phonetic`, and respects speed changes mid-playback.
- No AI calls fire without explicit user action — verified via the local debug console.

---

## Scope deliberately excluded

These were considered and consciously left out:

| Feature | Why excluded |
|---|---|
| Highlighting / annotation persistence | Without an account system, highlights live only in localStorage on one machine. Either a real feature with a backend or nothing. |
| Reading progress + bookmarks | Same constraint. Local-only progress works but adds chrome for marginal value when chapters are short. |
| Speechify-style "boost" tinted reading | Gimmicky. The Phase 1+2 typography work makes it unnecessary. |
| Global semantic search across all books | A published-catalog feature, not a drafts feature. Belongs in the future `podcast-viewer/` app per CLAUDE.md. |
| Per-book reader settings | Added complexity for marginal value. One reader, one preference. |

---

## Open decisions (flagged, not blocking)

1. **Gemini API key location.** Where do you keep your Gemini key today? If it's in a `.env` somewhere I can read it in dev; production needs the Worker proxy follow-up.
2. **Claude API key.** Do you want me to add Claude routes (recommended for sections (3.2) and (3.3)) or stay Gemini-only? If Gemini-only, those features work but with weaker nuance on doctrinal content.
3. **Sepia palette.** I'll pick warm cream `oklch(95% 0.04 75)` with sepia ink `oklch(28% 0.04 50)` unless you have a specific palette in mind.
4. **Mobile breakpoint.** Bottom sheet kicks in below `md` (768px). Confirm this works for iPad reading.
5. **API key follow-up: Cloudflare Worker proxy.** CLAUDE.md retired the previous Worker scaffold. Decision needed on whether to re-introduce a small proxy for AI keys.

---

## Branch and merge policy

Per [CLAUDE.md](../../CLAUDE.md) §"Branch policy" (locked 2026-05-24):

- All work on `book/the-master-and-the-disciple`.
- Commit boundaries align with phase boundaries so Asif can review/halt between phases:
  - Commit 1: Phase 1 — bug fixes (`fix(podcast-reader): restore Arabic overlay CSS and prose-body margins`)
  - Commit 2: Phase 2 — settings panel (`feat(podcast-reader): reader-settings popover with font, size, width, theme controls`)
  - Commit 3: Phase 3 — AI reading layer (`feat(podcast-reader): AI reading layer (term popover, section summary, ask-chapter, read-aloud)`)
- Merge `book/the-master-and-the-disciple` → `develop` happens as part of the book's publish wave, not after each commit.
- No work goes directly to `develop`.

---

## Approval

Asif to indicate which of the following:

- **A. Approve all three phases.** Execute end-to-end over ~3 working days, all on `book/the-master-and-the-disciple`, with phase boundaries as commit boundaries.
- **B. Approve Phase 1 + 2 only.** Defer Phase 3 (AI) to a separate conversation after using the polished reader for a few days.
- **C. Approve Phase 1 only.** Ship the bug fixes; have a follow-up conversation about Phase 2 and 3 once Asif has seen the small fixes in place.
- **D. Revise the plan first.** Tell me which features to drop, swap, or add before any commitment.

Default recommendation: **A**, because the AI panel needs the settings-panel chrome as scaffolding — building AI first means rebuilding surrounding UX twice.
