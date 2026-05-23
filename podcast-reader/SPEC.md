# Podcast Reader — Specification

A local-first, single-user reading-and-review companion for podcast-factory worktree content. Built to make dense scholarly chapter-contracts scannable, navigable, and reviewable — with comments that flow back into Claude Code for execution.

**Status:** design locked 2026-05-23, Phase 0 in progress.
**Project root:** `~/PROJECTS/podcast-factory/podcast-reader/`
**v1 pilot scope:** restricted to the book `kitab-al-riyad`. Other books (`asaas-al-taveel`, etc.) and other library categories are deferred until the pilot validates the UX.

---

## Purpose

You write podcast episode contracts in `chapter-contracts/*.yml` files across multiple worktree branches in `~/PROJECTS/podcast-factory/worktrees/`. Each contract is a dense scholarly artifact with Quran citations, hadith references, Arabic transliterations, and multi-paragraph `key_tensions` sections. You need to:

1. **Read** them comfortably in a typography-tuned reading view, with persistent font preferences.
2. **Scan** them quickly to find Quran/Hadith refs without reading every paragraph.
3. **Navigate** between refs by keyboard (next/prev Quran ref, next/prev hadith).
4. **Search** within a book by default, broadening when needed.
5. **Comment** on specific sentences/paragraphs to flag changes — comments persist on disk and feed back into Claude Code for execution.

This is a **review-and-edit companion**, not a study reader.

## Non-goals (v1)

- Mobile/responsive layout (desktop-first).
- RTL Arabic-primary layout (English with Arabic spans is sufficient).
- Multi-user, auth, hosting (localhost only).
- Verse-text expansion on Quran ref hover (jump-link only).
- Hadith data layer with grading metadata (citation-only).
- Annotations beyond comments (no highlighting/bookmarks).

---

## Architecture

```
Astro (Vite) + Tailwind + React islands
├─ Live glob from ~/PROJECTS/podcast-factory/worktrees/*/content/podcast/library/books/
├─ Chapter-contract YAML as primary content surface
├─ refined-english.md / english-transcript.md as "view source" secondary
├─ Pagefind for search (current-book scope default)
├─ On-disk JSON for prefs: ~/.config/podcast-reader/prefs.json
└─ Sidecar JSON for comments: <contract>.yml.review.json
```

**Why Astro:** ships near-zero JS by default; React islands hydrate only for interactivity (toolbar, gutter glyphs, comment layer, search palette, density rail). Content-first ergonomics. Pagefind drops in cleanly.

**Why React islands (not Svelte):** larger ecosystem for shadcn/ui-style components, more familiar if extending later. Svelte would also work; the choice is reversible.

---

## Folder structure

```
podcast-reader/
├── SPEC.md                        # this file
├── README.md                      # entry point, links to SPEC.md
├── package.json
├── astro.config.mjs
├── tailwind.config.js
├── tsconfig.json
├── public/                        # static assets (fonts, icons)
├── docs/                          # design notes, screenshots
└── src/
    ├── content/
    │   └── config.ts              # Astro content collection schemas
    ├── pages/
    │   ├── index.astro            # worktree + book picker
    │   ├── [worktree]/
    │   │   ├── index.astro        # books in this worktree
    │   │   └── [book]/
    │   │       ├── index.astro    # chapters in this book
    │   │       └── [chapter].astro  # the reading page
    │   └── api/
    │       ├── prefs.ts           # GET/POST ~/.config/podcast-reader/prefs.json
    │       ├── comments/[...path].ts  # GET/POST sidecar *.review.json
    │       └── content/[...path].ts   # serve markdown/yaml from worktrees
    ├── components/
    │   ├── layout/
    │   │   ├── ThreePane.astro
    │   │   ├── TocSidebar.tsx     # island
    │   │   ├── DensityRail.tsx    # island
    │   │   └── Toolbar.tsx        # island — font/theme/scope
    │   ├── reader/
    │   │   ├── ContractView.astro       # primary chapter-contract render
    │   │   ├── SourceView.astro         # markdown source toggle
    │   │   ├── GutterGlyphs.tsx         # island — left-margin ref icons
    │   │   ├── CommentLayer.tsx         # island — selection → comment
    │   │   ├── RefNavigation.tsx        # island — n/N/h/H keyboard nav
    │   │   └── HighlightRenderer.tsx    # island — regex-based ref highlighting
    │   └── search/
    │       └── SearchPalette.tsx        # cmd+K island, Pagefind-backed
    ├── lib/
    │   ├── worktree-glob.ts       # discover worktrees + books + chapters
    │   ├── contract-parser.ts     # YAML → structured render model
    │   ├── ref-categories/        # pluggable ref-category registry (see §Marking strategy)
    │   │   ├── types.ts           # RefCategory, RefMatch, DetectContext, ReaderContext
    │   │   ├── index.ts           # registry: collect + validate + expose enabled categories
    │   │   └── builtin/
    │   │       ├── quran.ts
    │   │       ├── hadith.ts
    │   │       ├── arabic-translit.ts
    │   │       └── arabic-native.ts
    │   ├── highlight-renderer.ts  # iterates registry, wraps matches in data-ref-* spans
    │   ├── anchor.ts              # fingerprint creation + fuzzy matching
    │   ├── prefs.ts               # client + server prefs management (incl. category overrides)
    │   └── cc-prompt.ts           # paste-ready Claude Code prompt generator
    └── styles/
        └── global.css
```

---

## Locked design decisions (eight)

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Stack | Astro + Tailwind + React islands | Content-first, ships ~0 JS, Pagefind-ready |
| 2 | Content source | Live glob across all worktrees, branch picker in UI | Hot-reload as you edit source, no ingestion step |
| 3 | Marking strategy | **Pluggable category registry**, regex-detector default; v1 ships Quran/Hadith/Arabic | Audit found zero existing markers. Etymology and future categories plug in via the registry without touching the rendering, navigation, search, or comment systems. See §Extensibility. |
| 4 | Layout | Three-pane (TOC \| reading column \| density rail), desktop-first | Gutter glyphs and scrollbar density need fixed columns |
| 5 | Prefs storage | On-disk JSON via `/api/prefs` endpoint | Survives browser clears, sync-able across machines |
| 6 | Search | Pagefind, current-book scope by default, opt-in broadening | Static index, fully local, sub-100ms, filter chips for ref categories |
| 7 | Marker behavior | Navigation-focused: jump-next/prev, ref index, scroll-to | Aligned to review intent, not study. No verse-text expansion in v1. |
| 8 | Comments | Sidecar JSON `<contract>.yml.review.json`, fingerprint anchoring with line-range fallback | Hypothesis-style, survives source edits; Claude Code reads from disk |

---

## Content model

### Primary surface: chapter-contract YAML

Each `chapter-contracts/<slug>.yml` renders as a chapter page with sections derived from these YAML keys:

- `title`, `episode_number`, `chapter_ref`, `slug` → page header
- `audience` → intro section (long prose paragraph)
- `key_tensions[]` → numbered body sections, each rendered as prose
- `anchor_passages[]` → structured list at end (book/verse + attribution)
- `show_notes` → epilogue section
- `tone_constraints`, `length_target`, `host_dynamic` → metadata sidebar (collapsible)

All prose sections run through the regex-based ref highlighter (see below).

### Secondary surface: source markdown

Reachable via a "View source" toggle in the toolbar — renders the corresponding `refined-english.md` or `english-transcript.md` in the same reading column. No special highlighting (these files are plain prose).

### Discovery + dual navigation (chapters AND episodes)

A book has TWO related axes the reader surfaces:

- **Source chapters** — files in `<book>/chapters/ch<NN>-<slug>.txt` (or sections within `refined-english.md`). These are the raw book chapters as they exist in the source manuscript.
- **Episodes** — files in `<book>/chapter-contracts/<slug>.yml`. These are podcast episodes, each numbered (`episode_number: 11`) and each referencing a source chapter (`source_chapter_ref: 9`). One source chapter can produce multiple episodes; episodes are the primary read surface.

The book index page (`/<worktree>/<book>/`) presents both axes side-by-side: a "Source chapters" list on one side, an "Episodes" list on the other, with cross-links between them (an episode card shows which source chapter it adapts; a source chapter card shows which episodes derive from it).

Live glob walks `~/PROJECTS/podcast-factory/worktrees/*/content/podcast/library/books/<book>/`. The worktree name (e.g. `book-kar`, `book-asaas`, `book-islr`, `main`) becomes the first URL segment. The book slug is the second.

**v1 scope:** `kitab-al-riyad` only. Other books (`asaas-al-taveel`, etc.) and library categories (`letters/`, `articles/`, `lectures/`, `interviews/`, `documents/`, `archetypes/`) are deferred. The pilot exists to validate the reading + scanning + comment UX on real content before broadening surface area.

---

## Marking strategy — pluggable category registry

The reader does NOT hard-code Quran/Hadith/Arabic as fixed concepts. They are **the first three entries in a category registry** that anything downstream (highlighter, gutter glyphs, density rail, TOC counts, keyboard nav, search filter chips, comment surfaces) reads from. Adding a new category (etymology, dates, place-names, manuscript-folio refs — whatever you decide later) means registering one new entry. No other code changes.

### The registry interface

```typescript
// src/lib/ref-categories/types.ts
export interface RefCategory {
  id: string;                          // 'quran', 'hadith', 'arabic', 'etymology', ...
  label: string;                       // human-readable: 'Quran'
  glyph: string;                       // gutter icon: '📖'
  colorToken: string;                  // Tailwind color: 'blue' / 'amber' / 'green' / 'purple' / ...
  typography: RefTypography;           // per-category font assignment (see below)
  shortcuts: { next: string; prev: string };  // e.g. { next: 'n', prev: 'N' } — configurable in prefs
  enabledByDefault: boolean;
  detect: (text: string, context: DetectContext) => RefMatch[];
  // optional: action invoked when user clicks a matched span
  onActivate?: (match: RefMatch, context: ReaderContext) => void | Promise<void>;
}

export interface RefTypography {
  fontFamily: string;                  // CSS font-family stack
  fontWeight?: number;                 // 400, 500, 600, 700
  fontStyle?: 'normal' | 'italic';
  letterSpacing?: string;              // e.g. '0.01em'
  smallCaps?: boolean;
}

export interface RefMatch {
  start: number;          // char offset in source text
  end: number;            // char offset
  value: string;          // e.g. '54:49' for Quran, root letters for etymology
  attrs?: Record<string, string>;  // becomes data-* attrs on the span
}
```

### How the registry is consumed

- **HighlightRenderer** iterates registered+enabled categories, runs each `detect`, wraps matches in `<span data-ref-type="{id}" data-ref-value="{value}" class="ref-{id}">…</span>`. Tint color comes from `colorToken` mapped through Tailwind's palette — no per-category CSS files.
- **GutterGlyphs** reads `data-ref-type` from rendered DOM, renders `glyph` aligned to each match's line.
- **DensityRail** colors scrollbar ticks by `colorToken`.
- **RefNavigation** binds each category's `shortcuts.next`/`.prev` keys dynamically; if shortcuts conflict (after etymology adds a key), the registry validates at startup and surfaces a console warning + falls back to numbered shortcuts (`1n`/`2n`/`3n`).
- **Toolbar filter chips** render one chip per category from the registry — never a hard-coded list.
- **TOC counts** render "§3 — 12 📖 · 5 📜 · 23 ع" by iterating the registry, not by hard-coded labels.
- **Pagefind search filter chips** derive from the registry as well, filtering on the `data-ref-type` attribute.
- **User prefs** can disable categories, rebind shortcuts, override `colorToken` — all via `~/.config/podcast-reader/prefs.json` under a `categories` key.

### v1 registrations (`src/lib/ref-categories/builtin/`)

| File | id | label | glyph | color | Font (family / weight / style) | Detector summary |
|---|---|---|---|---|---|---|
| `quran.ts` | `quran` | Quran | 📖 | blue | EB Garamond / 600 / normal | Regex: `\b(?:Quran\|Q\.?)\s+\d+:\d+(?:[–-]\d+)?\b` |
| `hadith.ts` | `hadith` | Hadith | 📜 | amber | EB Garamond / 400 / italic | Heuristic: italicized phrase following "Prophetic word" / "Prophet ﷺ" / "the Prophet" within ~50 chars |
| `arabic-translit.ts` | `arabic` | Arabic | ع | green | Gentium Plus / 400 / italic | Regex: `\*[a-zʿʾā-ūḥṣḍṭẓ' -]{2,40}\*` (italicized Latin with diacritics or apostrophes) |
| `arabic-native.ts` | `arabic-native` | (renders inline) | — | — | Amiri / 400 / normal | Unicode `[؀-ۿ]+`; no glyph, just font swap |

**Font rationale (each category gets a distinct visual treatment):**

- **EB Garamond** for both Quran and Hadith — visually linked as "scriptural" content, but distinguished by weight (Quran semibold, Hadith italic regular). Garamond is a literary serif with a reverent, classical feel.
- **Gentium Plus** for Arabic transliterations — purpose-built for excellent diacritic rendering (ḥṣḍṭẓ ā ū ī ʿ ʾ), italic to feel "quoted".
- **Amiri** for native Arabic script — traditional naskh, ideal for Quranic phrases.
- **Source Serif 4** for body prose (the default reading text — registered implicitly via the page-level typography, not per-category).
- **Inter** for UI chrome.

Future categories declare their own font, e.g. **Vollkorn 400 normal** for an etymology category — visually distinct from the four above.

Native Arabic deliberately registers as a category with no glyph/shortcut — it only contributes the font-swap rendering. This validates the registry handles partial implementations cleanly (proof that the abstraction holds).

### User overrides

Users can override any category's `colorToken`, `typography`, or `shortcuts` in `~/.config/podcast-reader/prefs.json`:

```json
{
  "categories": {
    "quran": {
      "typography": { "fontFamily": "Cormorant Garamond", "fontWeight": 500 },
      "colorToken": "indigo"
    },
    "hadith": { "enabled": false }
  }
}
```

The Toolbar's "Display" section exposes a curated UI for the common overrides; advanced users edit JSON directly.

### Adding a category later — worked example: etymology

When you're ready to add etymology, you create one file `src/lib/ref-categories/builtin/etymology.ts`:

```typescript
import type { RefCategory } from '../types';

export const etymology: RefCategory = {
  id: 'etymology',
  label: 'Etymology',
  glyph: '🔍',
  colorToken: 'purple',
  shortcuts: { next: 'e', prev: 'E' },
  enabledByDefault: false,       // user opts in via prefs
  detect: (text) => {
    // v1 implementation: detect italicized Arabic transliterations
    // that match a known-root dictionary. Could be a bundled JSON of
    // common roots, or a fetch to a backing service.
    return findRootMatches(text);
  },
  onActivate: async (match, ctx) => {
    // click on an etymology-marked word opens the right rail
    // as a root-lookup panel (Lane's Lexicon excerpt, derived forms, etc.)
    await ctx.openRail({ kind: 'etymology', root: match.value });
  },
};
```

Then register it in `src/lib/ref-categories/index.ts` — that's it. The toolbar gets a new "🔍 Etymology" filter chip, the scrollbar rail gets purple ticks, search results filter on `data-ref-type="etymology"`, TOC counts include etymology, the `e`/`E` shortcuts work, and the click action opens a custom side panel — all from one file. **No edits to HighlightRenderer, GutterGlyphs, DensityRail, RefNavigation, Toolbar, TocSidebar, or SearchPalette.**

### Scrollbar density rail (right edge)
Thin column (~24px) showing colored ticks at each ref location, one color per category (via `colorToken`). Hover to preview the line. Click to scroll-to.

### TOC sidebar
For the current chapter, renders section-level ref counts dynamically from the registry: `§3 — 12 📖 · 5 📜 · 23 ع`. When etymology is added, the same section becomes `§3 — 12 📖 · 5 📜 · 23 ع · 7 🔍` with zero TOC code changes.

---

## Typography + theme

### Defaults
- Body prose: **Source Serif 4** (variable, OFL-licensed, bundled in `public/fonts/`)
- UI chrome: **Inter**
- Quran refs: **EB Garamond** 600 normal
- Hadith refs: **EB Garamond** 400 italic
- Arabic transliteration refs: **Gentium Plus** 400 italic
- Native Arabic script: **Amiri** 400 (with **Scheherazade New** as alternate)
- Size: 19px body, 1.7 line-height, max 70ch measure
- Themes: light + dark, toggle in toolbar

All fonts are OFL-licensed and bundled in `public/fonts/`. No external font CDN dependencies.

### User-adjustable (toolbar)
- Latin font: 3 curated choices (Source Serif 4, Iowan Old Style, Charter)
- Arabic font: 2 choices (Amiri, Scheherazade New)
- Size: slider 16–24px
- Line-height: slider 1.4–2.0
- Theme: light / dark

### Persistence
- Source of truth: `~/.config/podcast-reader/prefs.json`
- Read on SSR so no flash of default styles
- localStorage caches for instant client-side reads
- Saved on change (debounced 200ms) via `POST /api/prefs`

---

## Comment system

### Sidecar JSON schema

```json
{
  "version": 1,
  "contractPath": "worktrees/book-kar/content/podcast/library/books/kitab-al-riyad/chapter-contracts/qada-and-qadar-fate-and-destiny.yml",
  "comments": [
    {
      "id": "c_01HXYZ...",
      "anchor": {
        "selectedText": "destiny is estimation, decree is detail",
        "prefix": "...al-Islah had argued: ",
        "suffix": ", because the prior is...",
        "lineHint": 47,
        "yamlPath": "key_tensions[0]"
      },
      "comment": "rewrite — too verbose, halve it",
      "status": "open",
      "createdAt": "2026-05-23T19:00:00Z",
      "updatedAt": "2026-05-23T19:00:00Z",
      "addressedNote": null
    }
  ]
}
```

- File path: same dir as the contract, suffix `.review.json` (e.g. `qada-and-qadar-fate-and-destiny.yml.review.json`).
- `anchor.selectedText` + `prefix` + `suffix` is the Hypothesis-style fingerprint (~30 chars context each side).
- `anchor.yamlPath` is the YAML key path so the slash command knows which field to edit.
- `lineHint` is the line-range fallback when fingerprint matching fails.
- `addressedNote` is written by the slash command after applying the change.

### Lifecycle
- `open` → just created, awaiting action
- `addressed` → slash command applied the change
- `dismissed` → user closed without action

### Reader UX
- Select text → floating "+ Comment" button appears
- Click → modal with textarea + Save
- Saved comments appear in right rail (collapsible panel) and as a small dot in the gutter at the anchor line
- Click a comment in the rail → scrolls to + highlights the anchored span
- Status filter chips: Open / Addressed / Dismissed / All
- "Copy Claude prompt" button → puts ready-to-paste prompt on clipboard for all open comments

### .gitignore requirement
`*.review.json` should be added to `.gitignore` in each worktree to prevent accidental commits. The reader can add this automatically when it first writes a sidecar in a worktree that doesn't have the rule (or warn).

---

## Claude Code handoff

### Path A — paste-ready prompt
Toolbar button generates:
```
Apply the following review comments to <contract-path>. After each, update the
sidecar review.json (<sidecar-path>) to mark the comment as addressed with a
one-line note about the change made.

1. [key_tensions[0], anchored at "destiny is estimation, decree is detail"]
   "rewrite — too verbose, halve it"

2. [show_notes, anchored at "..."]
   "..."
```
You paste into Claude Code. Full control to edit the prompt before executing.

### Path B — `/podcast-review-apply` slash command (separate skill)
Lives in `~/.claude/skills/podcast-review-apply/SKILL.md`. Invoked as `/podcast-review-apply <contract-path>` (or `<book-slug>` for all chapters). Reads sidecar JSONs, resolves anchors via fingerprint, applies edits to the YAML contract using yaml-aware editing (preserves comments and formatting), updates status with `addressedNote`. Built as a separate task (Phase 6) after the reader is usable.

---

## Search (Pagefind)

- Index built per dev-server start (rebuilds on file change in dev mode)
- Scope picker: `current chapter` / `current book` (default) / `all worktrees`
- Filter chips: All / Quran / Hadith / Arabic — filters by `data-ref-*` attributes
- Cmd+K opens palette anywhere
- Excerpt-centric results: match-context paragraph + book/chapter breadcrumb + ref-glyph context
- Enter jumps to hit, scrolls to + pulses the matched phrase

---

## Implementation phases

| Phase | Scope | Est. days | Demo-able at end |
|---|---|---|---|
| **0. Bootstrap** | `npm create astro`, Tailwind, TypeScript, baseline config; `package.json` scripts; minimal `index.astro` showing worktree list | 0.5 | localhost:4321 lists worktrees |
| **1. Three-pane viewer** | Worktree glob, routing `[worktree]/[book]/[chapter]`, contract YAML parser, ContractView component, three-pane layout shell | 1.5 | Click through worktree → book → chapter, read contract as styled prose |
| **2. Marking + scanning** | Ref-detector regexes, HighlightRenderer, GutterGlyphs, DensityRail, RefNavigation (n/N/h/H/a/A), TOC ref counts | 2.5 | Quran/Hadith/Arabic visible inline + gutter + scrollbar; jump by keyboard |
| **3. Typography + prefs** | Toolbar (font/size/line-height/theme), `/api/prefs` endpoint, prefs.json read on SSR, localStorage cache | 1.0 | Persistent typography that survives restart |
| **4. Comments + CC handoff** | Selection → comment modal, sidecar JSON read/write API, fingerprint anchor lib, right-rail comment list, "Copy Claude prompt" button | 2.5 | Full review loop: select → comment → save → copy CC prompt |
| **5. Search** | Pagefind integration, build hook, Cmd+K palette, scope picker, filter chips | 1.5 | Cmd+K finds anything in current book; broaden to all worktrees |
| **6. `/podcast-review-apply` skill** | New skill in `~/.claude/skills/podcast-review-apply/`, YAML-aware editing, anchor resolution, status updates | 0.5 | Closed loop: run skill → comments resolved with `addressedNote` populated |

**Total:** ~10 days focused work. Usable read-only viewer at end of Phase 1 (~2 days). Closed review-edit loop at end of Phase 4 (~7 days).

---

## Risks + things to watch

### v1 risks (called out before building)
- **Hadith detection heuristic is fragile.** Quran refs are mechanical; hadith refs depend on contextual phrasing ("Prophetic word", "Prophet ﷺ"). False-positive rate will be higher. Acceptable for v1 with a "report false positive" affordance, refine post-launch.
- **Italicized-Arabic detection will catch emphasized English words.** Phrases like `*important*` will get tinted green. Mitigations: minimum length (3+ chars), require at least one diacritic OR apostrophe, allow per-word dismissal stored alongside prefs.
- **Comment fingerprint fails when Claude edits the exact anchored span.** When the change *is* the rewrite, the comment can't find itself afterwards. Solution: slash command marks comments addressed *before* applying the edit, so fingerprint resolution only happens once.
- **Worktree path stability.** Reader assumes `~/PROJECTS/podcast-factory/worktrees/*/`. If this changes, the reader breaks. Make configurable via env var from day one.

### v2 considerations (out of scope for v1, registry-ready)
- **Etymology** (planned, registry-ready): new `RefCategory` registration in `src/lib/ref-categories/builtin/etymology.ts`. Detects Arabic transliterations matching known three-letter roots, surfaces a 🔍 gutter glyph, `e`/`E` keyboard nav, and on-click opens a root-lookup side panel (Lane's Lexicon excerpt, derived forms). Architecture supports it without touching any rendering/navigation/search/comment code — see §Marking strategy "Adding a category later" for the worked example.
- **Other future categories** the registry trivially handles: dates (`📅`, regex for AH/CE patterns), place-names, manuscript-folio refs, cross-book citations, named-entity refs (`👤` for figures like al-Kirmani, Imam Ali).
- Library categories beyond books: `letters/`, `articles/`, `lectures/`, `interviews/`, `documents/`, `archetypes/`.
- Cross-reference detection (when the same Quran ref appears across chapters).
- Cross-chapter ref index ("show all chapters citing Quran 2:255") — natural extension of the existing `data-ref-value` attribute.
- Highlights/bookmarks/personal annotations (separate from review comments).
- Hadith verse-text expansion (needs canonical data source).
- Quran verse-text expansion via Tanzil dataset — would attach as an `onActivate` handler on the existing Quran category, no new code paths.
- Export comments as standalone markdown summary.
- Mobile responsive.

---

## Open questions to revisit during build

- Should the slash command live in `~/.claude/skills/` (user-global) or in `podcast-factory/.claude/skills/` (project-local)? Defer until Phase 6.
- Should review.json sidecars include the YAML's modification timestamp at comment time, so we can detect "source was edited under us" and warn? Probably yes — add to schema as `anchor.sourceMtime`.
- Should the comment "Copy Claude prompt" also offer a "Copy as markdown checklist" variant for non-CC review workflows (e.g. paste into a notes app)? Cheap to add in Phase 4.
- **Keyboard shortcut collisions as categories grow**: once 5+ categories register, mnemonic single-letter shortcuts run out. Options: (a) numeric prefixes (`1n`/`2n`/`3n` for category-1-next, etc.), (b) generic `j`/`k` for "any next/prev ref" with the active filter chip determining scope, (c) user-rebindable shortcuts in prefs. v1 ships single-letter (n/h/a) + the registry validates uniqueness at startup; pick the long-term answer once etymology lands and we feel the friction.
