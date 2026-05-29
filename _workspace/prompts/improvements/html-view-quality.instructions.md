---
applyTo: "**/*.html"
title: "HTML View Quality Standard"
version: "2.0.0"
status: "stable"
authority: "Maintained by the host organization's design-governance owner"
license: "Use freely within your organization; preserve attribution to this standard."
supersedes: "1.0.0"
---

# HTML View Quality Standard

> A portable, theme-agnostic, organization-agnostic craft and governance contract for AI-generated (or human-generated) long-form HTML views — walkthroughs, analyses, deep-design artifacts, cheatsheets, demos, decision records, reference pages, and any single-purpose HTML page meant to be read top-to-bottom and presented to a human stakeholder.

This standard governs **two things**:

1. **Craft** — how the view renders, reads, scales, and earns trust as an artifact (§1–§5, §7–§9).
2. **Content integrity & disagreement governance** — how the view represents facts, interpretations, decisions, dissent, and conflicting sources without distorting them (§6).

It deliberately defines **no view types, no required section lists, and no narrative templates.** *What* a view communicates is the host project's concern. *How* it renders, reads, sounds, and earns trust is governed here.

---

## How to use this spec

Place this document inside any project as `.github/instructions/html-view-quality.instructions.md` (editor AI assistants), as a `SKILL.md` inside a skills folder, or paste it into any AI coding agent's project context. Every rule is numbered (`REQ-NNN`) and tagged with an enforcement tier:

- **MUST** — hard requirement. The generator MUST satisfy it; the reviewer MUST reject a view that violates it. A view that breaks a MUST is non-conformant and must not ship.
- **SHOULD** — strong default. Skip only with a stated reason captured in a code comment near the deviation. Reviewers must challenge unexplained deviations.
- **MAY** — permitted variation. Apply when it improves the specific view; skip silently when it does not.

All theme-specific values shown inline are **illustrative examples**, not mandates. Substitute your project's own theme via the **Theme Adapter Contract** (§9). Two fully worked example themes — a dark "glass" theme and a light corporate theme — are provided in Appendices C and D so you can see one valid set of values; do not copy them verbatim into a project whose brand differs.

> **Stable identifiers.** `REQ-NNN` numbers are immutable once published (REQ-074). New rules are appended with new numbers; existing numbers are never renumbered or reused. Section numbers (`§N`) may be reorganized across major versions, so cite rules by `REQ-NNN`, not by section.

---

## §1 Page Architecture

The skeleton every conformant view follows. The intent is **vertical scrollability without limit**, a single focused page, no carousels, no tabs, no accordions that hide primary content.

### REQ-001 [MUST] Document shell order

Every page is laid out as exactly this top-to-bottom sequence:

```html
<body>
  <a class="skip-link" href="#main">Skip to content</a>  <!-- 0: skip link (REQ-071) -->
  <header class="page-header">…</header>      <!-- 1: page header, NOT sticky -->
  <nav class="jump-nav">…</nav>               <!-- 2: STICKY jump nav -->
  <main id="main" class="container">          <!-- 3: scrollable content -->
    <section class="glass-panel" id="s01-…">…</section>
    <section class="glass-panel" id="s02-…">…</section>
    …
    <aside class="related-pages">…</aside>    <!-- 4: cross-reference cards (optional) -->
  </main>
  <footer>…</footer>                          <!-- 5: footer -->
  <a class="back-top-btn" href="#">↑</a>      <!-- 6: floating back-to-top -->
</body>
```

No landmark may be reordered. The page header is NOT sticky. The jump nav IS sticky. The footer is always the last visible content. Back-to-top is a fixed-position floating element, not in document flow.

### REQ-002 [MUST] No height clamp anywhere

NO `max-height`, NO `max-block-size`, NO `overflow: hidden` or `overflow: auto` may be applied to `html`, `body`, `main`, `.container`, or any top-level `<section>`. The page MUST grow vertically as content requires.

The ONLY permitted horizontal-scroll escape hatches are:

- `overflow-x: auto` on `.diagram-container` (so wide SVGs scroll horizontally without breaking page width)
- `overflow-x: auto` on `.table-container` (so wide tables scroll — see REQ-052)
- `overflow: auto` on `<pre>` code blocks

The ONLY permitted `max-height` is on tooltip / popover elements.

Violation example (forbidden):
```css
/* ❌ FORBIDDEN — clamps the page */
.glass-panel { max-height: 600px; overflow-y: auto; }
main { height: 100vh; overflow: scroll; }
```

### REQ-003 [MUST] Container width contract

Every primary content container uses:
```css
.container { width: 90%; max-width: 1400px; margin: 0 auto; padding: 0; }
```
The page header and the jump nav share the same width contract so they align vertically with body content. Paragraphs inside sections inherit container width — they MUST NOT have their own `max-width`.

> **Field note:** capping paragraph `max-width` (e.g. to 800px) is a recurring regression — it makes body copy visually drift left of its section heading, because the heading fills the container while the paragraph does not. Keep line-length comfort at the *container* level (REQ-016), never at the paragraph level.

### REQ-004 [MUST] Section element + id + section number

Every body section uses `<section>` (not `<div>`), has a unique `id` (lowercase kebab-case, prefixed `s01-`, `s02-`, … in document order), and the section heading carries the section number as a visually distinct marker:

```html
<section id="s03-worked-example" class="glass-panel">
  <h2><span class="num">03</span> The worked example</h2>
  …
</section>
```

The numeric marker pattern is required so the sticky jump nav, the page outline, and the eye-scan all line up. Numbering is two-digit zero-padded.

### REQ-005 [MUST] Scroll behavior

```css
html { scroll-behavior: smooth; }
section[id] { scroll-margin-top: 60px; }   /* ≥ sticky jump-nav height + 8px */
```

`scroll-margin-top` MUST be at least the sticky nav height plus 8px. Without this, anchor jumps hide the section heading behind the sticky nav.

### REQ-006 [SHOULD] Breadcrumb strip

A breadcrumb strip MAY sit between the page header and the jump nav for navigable hierarchies (e.g. `Home › Reports › Q3 Review`). Use `<nav aria-label="breadcrumb">`, styled as compact mono text at 0.72rem. Skip it on standalone single-page artifacts.

### REQ-007 [MUST] file:// protocol compatibility

Every view MUST open correctly when double-clicked from the file system (no local server). This means:

- No `fetch()`, no `XMLHttpRequest`, no dynamic `import()`, no service workers
- All JavaScript inline in `<script>` blocks (no external `.js` files, except optionally a shared design-system CSS file referenced relatively)
- All SVGs inline (see §4)
- All images either base64 data URIs OR relative paths to files that ship alongside the view
- The ONLY tolerated external dependency is a web-font `<link>` (e.g. Google Fonts) — and even that SHOULD have a system-font fallback so the page degrades gracefully offline

### REQ-008 [SHOULD] Schema.org JSON-LD header

Inject a `<script type="application/ld+json">` block in `<head>` declaring `@type: TechArticle` with `headline`, `description`, `author`, `datePublished`, `dateModified`, and `keywords`. This gives the view machine-readable provenance for downstream tooling (search, indexers, automated reviewers).

### REQ-009 [MUST] Single-purpose page

One view = one purpose. Do not combine "the walkthrough AND the cheatsheet AND the analysis" in a single HTML file. If you have three purposes, ship three views. The acceptable *scale* of a single view is large — reference views routinely range from tens to a couple hundred KB and scroll for many screens — but the *purpose* is singular.

---

## §2 Typography

Typography rules are the most-violated and the highest-leverage. They decide whether a stakeholder can read the view comfortably on a laptop, or projected on a wall in a meeting room. Treat every rule here as hard-won.

### REQ-010 [MUST] Reading-text minimum

ALL prose intended for reading is **1.2rem minimum** at default browser zoom. This applies to `<p>`, `<li>`, `<td>`, `<th>`, `<dd>`, `<dt>`, `<blockquote>`, `<figcaption>`, `<label>`, and any class used for narrative copy (`.callout`, `.qa-a`, `.qa-q`, `.gloss`, `.section-description`).

```css
p, li, td, th, dd, dt, blockquote, figcaption, label,
.callout, .qa-a, .qa-q, .gloss, .section-description {
  font-size: 1.2rem;
  line-height: 1.75;
}
body { font-size: 1.2rem; }
```

EXEMPT (these are UI chrome, not reading content):
- Chips, badges, pills (0.72–0.85rem mono)
- Breadcrumb segments (0.72rem mono)
- Jump-nav buttons (0.72–0.78rem mono)
- Table column headers in mono uppercase (0.72rem)
- Metadata tags above headings (0.72rem mono)

The 1.2rem floor exists because senior stakeholders read these documents projected on a wall. 1rem (16px) at six feet is unreadable; 1.2rem (≈19.2px) is the empirically-tested floor.

### REQ-011 [MUST] Heading scale

```
h1: page title only — 1.85rem, display font, 700 weight, gradient text treatment
h2: section heading — 1.4–1.65rem, display font, 700 weight, accent color
h3: subsection     — 1.2–1.25rem, display font, 600 weight, secondary text color
h4: minor heading  — 1.05rem, display font, 600 weight, accent-secondary color
```

There is exactly ONE `<h1>` per page (the title in the header). Do not use `<h1>` elsewhere. Do not skip heading levels — `<h2>` then `<h4>` is forbidden.

### REQ-012 [MUST] Font role system

Three font roles. The host project picks the actual families.

| Role | Token | Used for |
|---|---|---|
| Body / reading | `--font-sans` | All prose, lists, tables |
| Display / headings | `--font-display` | h1–h4, page titles, section headings, large numbers |
| Mono / code | `--font-mono` | Code, file paths, command names, chips, badges, section numbers, hash/identifier values |

A view MUST NOT use more than 3 font families. Decorative or script fonts are forbidden in body content (allowed only inside SVG illustrations when intentional).

### REQ-013 [MUST] Gradient title treatment for page H1

The page `<h1>` uses a two-stop gradient applied as text fill. This is the single visual signature that identifies the document as a "view" rather than a generic web page.

```css
.page-title {
  font-family: var(--font-display);
  font-size: 1.85rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}
```

If the host theme has only ONE accent color (common in corporate themes), fall back to a gradient from `--text-primary` to `--accent-primary`. Do not fabricate a second accent.

### REQ-014 [MUST] Inline code / mono treatment

Inline code and mono identifiers (`<code>`, `.mono` spans) MUST get the mono font, a subtle dark background (10–35% alpha), small horizontal padding, a 4px radius, a coloured foreground (the primary accent), and a slightly smaller size relative to surrounding prose:

```css
code, .mono {
  font-family: var(--font-mono);
  font-size: 0.86em;
  background: rgba(0,0,0,0.35);
  padding: 0.05em 0.4em;
  border-radius: 4px;
  color: var(--accent-primary);
}
```

On light themes, swap the background to a low-alpha *tint of the accent or a light grey* (e.g. `rgba(15,23,42,0.06)`) so the chip stays readable.

### REQ-015 [MUST] List rendering standard

A universal `* { margin: 0; padding: 0; }` reset strips default list indentation and collapses markers into the text. Every view MUST restore predictable list rendering:

```css
ol, ul {
  padding-inline-start: 2.25rem;    /* MUST be ≥ 1.75rem */
  margin-block: 0.85rem 1.1rem;
  list-style-position: outside;     /* MUST be outside, not inside */
}
ol ol, ol ul, ul ol, ul ul {
  padding-inline-start: 1.75rem;
  margin-block: 0.4rem;
}
li { margin-block: 0.45rem; padding-inline-start: 0.25rem; }
li > p:first-child { margin-block-start: 0; }
li > p:last-child  { margin-block-end: 0; }
```

Ordered lists MUST use `<ol>` with native decimal numbering — do NOT fake numbering with text inside `<li>`. Number alignment and wrapped-line indentation depend on `list-style-position: outside`.

### REQ-016 [SHOULD] Line-length comfort

For body prose, eye comfort suggests ~80 characters per line. Because of REQ-003 (90% width, max 1400px), this happens naturally at 1.2rem on a wide container. Do NOT add `max-width` to paragraphs to artificially shorten lines — that breaks REQ-003.

### REQ-052 [MUST] Wide-table horizontal-scroll wrapper

Tables at the 1.2rem floor frequently exceed 360px on phones. Because REQ-002 forbids clamping sections, wide tables MUST be wrapped in a `.table-container` that owns the only permitted horizontal scroll:

```html
<div class="table-container" role="region" aria-label="…table name…" tabindex="0">
  <table>…</table>
</div>
```
```css
.table-container { overflow-x: auto; margin: 16px 0; }
.table-container table { width: 100%; border-collapse: collapse; }
```

The `tabindex="0"` + `role="region"` lets keyboard users scroll the table and screen readers announce it. Never solve table overflow by clamping the section or shrinking text below the 1.2rem floor.

### REQ-053 [SHOULD] Multi-line code-block treatment

`<pre>` blocks are exempt from the 1.2rem reading floor (code has its own comfort range) but MUST have a floor of their own and a horizontal scroll:

```css
pre {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  line-height: 1.55;
  background: var(--bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  overflow: auto;            /* permitted by REQ-002 */
}
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }
```

Do not syntax-highlight with more than the two accent colours plus the text ramp (keeps REQ-018 intact).

### REQ-054 [SHOULD] Long-token wrapping

File paths, URLs, and long identifiers in mono can break the layout on narrow viewports. Apply:

```css
code, .mono, td, a[href] { overflow-wrap: anywhere; }
```

### REQ-055 [SHOULD] Print stylesheet

Governance and decision-record views are routinely printed to PDF. Provide a `@media print` block that: removes the sticky nav and back-to-top button, expands any hover-only content, prints link URLs after their text, and forces background colours to print where they carry meaning.

```css
@media print {
  .jump-nav, .back-top-btn, .skip-link { display: none; }
  a[href]::after { content: " (" attr(href) ")"; font-size: 0.8em; color: #555; }
  .glass-panel { break-inside: avoid; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
```

---

## §3 Color & Surface

### REQ-017 [MUST] Theme Adapter Contract — required tokens

The host project's CSS MUST define these named custom properties. The spec names them; values are the host theme's choice:

```css
:root {
  /* Background surfaces */
  --bg-primary:    /* page background */;
  --bg-secondary:  /* secondary surface (banner, footer) */;
  --bg-tertiary:   /* third-level surface */;
  --bg-card:       /* opaque card background */;
  --bg-glass:      /* translucent panel background (alpha ~0.60–0.85) */;

  /* Text colours — four-step ramp */
  --text-primary:    /* maximum-contrast body text */;
  --text-secondary:  /* slightly lower-contrast body text */;
  --text-tertiary:   /* metadata, captions */;
  --text-muted:      /* timestamps, version tags, low-priority chrome */;

  /* Accent system — two accents */
  --accent-primary:        /* dominant accent — h2 colour, links, icons */;
  --accent-secondary:      /* second accent — gradients & h4 only */;
  --accent-primary-dim:    /* alpha ~0.12–0.15 variant for backgrounds */;
  --accent-secondary-dim:  /* alpha ~0.12–0.15 variant for backgrounds */;

  /* Semantic colours */
  --color-success: /* green family */;
  --color-warning: /* amber family */;
  --color-error:   /* red family */;

  /* Surface "glass" treatment (or solid card fallback if not glassmorphic) */
  --glass-bg:             /* standard panel background */;
  --glass-border:         /* standard panel border (alpha ~0.10) */;
  --glass-border-hover:   /* on hover */;
  --glass-border-accent:  /* accent-tinted border for highlighted panels */;

  /* Font roles */
  --font-sans:    /* body */;
  --font-display: /* headings */;
  --font-mono:    /* code & UI chrome */;

  /* Radii */
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 24px;

  /* Transition */
  --transition-glass: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
```

A non-glassmorphic theme MAY map `--glass-bg` to a solid card colour, `--glass-border` to a 1px solid border, and skip `backdrop-filter` entirely — the contract names stay the same, the implementation differs.

### REQ-018 [MUST] Accent restraint — at most 2 accents

A view MUST use at most TWO accent colours (`--accent-primary`, `--accent-secondary`). The four semantic colours (success / warning / error / info) are counted separately. Adding a third decorative accent fragments the visual hierarchy.

### REQ-019 [SHOULD] Alternating section tinting

When a view has 6+ sections, alternate the section background between `--bg-card` (opaque) and `--glass-bg` (translucent) so the eye can track section boundaries while scrolling. Both surfaces share the same border treatment.

### REQ-020 [SHOULD] Semantic colour mapping

Use the four semantic colours for meaning, not decoration:
- `--color-success` → pass states, "done", positive metrics
- `--color-warning` → caution, deferred work, beginner flags
- `--color-error` → fail states, blockers, regressions
- `--accent-primary-dim` → informational / neutral highlights

Do not use red for a decorative border, green for a section title, or amber as a heading colour. Reserve them for meaning.

---

## §4 SVG Craft & Diagram Selection — the highest-leverage rules

SVG is the make-or-break craft surface of a long-form view. A view with two excellent diagrams reads as a high-trust artifact; a view with six low-density or mis-chosen diagrams reads as filler. §4 covers **craft** (REQ-021–034, 059–062) and **selection** (REQ-056–058, 060–061) — choosing the right visual form for the job is as important as drawing it well.

### REQ-056 [MUST] Choose the right visual form before drawing

Before creating an SVG, decide whether SVG is even the correct form. SVG is for **spatial, relational, temporal, or structural** content. It is the *wrong* tool for content that is fundamentally tabular or enumerable.

| If the content is… | Use… | Not… |
|---|---|---|
| A comparison of options across criteria | `<table>` (REQ-052) | a grid drawn in SVG |
| A list of steps with no branching | `<ol>` | a single-track "flow" SVG |
| A set of definitions | `<dl>` | labelled boxes in SVG |
| A spatial layout, hand-off, state change, or quantity comparison | inline `<svg>` | a wall of prose |

A table or list drawn inside an SVG is an accessibility trap (unselectable, unsearchable, unreadable by assistive tech beyond the `<desc>`) and a maintenance trap. **When in doubt, prefer semantic HTML.** Reserve SVG for what only a picture can show.

### REQ-057 [SHOULD] Diagram-type selection matrix (intent → archetype)

Match the diagram archetype to the *communicative question* you are answering. (See Appendix E for the expanded quick-reference.)

| The question you are answering | Recommended archetype | viewBox shape |
|---|---|---|
| "In what order do events happen over time?" | Timeline / annotated milestone strip | wide |
| "Who hands off to whom, and when?" | Sequence diagram (vertical lifelines) or swimlane | tall / wide-banded |
| "How do the parts contain or layer?" | Layered / nested architecture | tall-ish |
| "What are the states and the transitions between them?" | State machine | square-ish |
| "Which path does a decision take?" | Flowchart / decision tree | tall or wide |
| "Where are the gates and what do they enforce?" | Pipeline with gate markers | wide |
| "How do these quantities compare?" | Bar / column chart (REQ-058) | wide |
| "What is the part-to-whole across categories?" | Stacked bar | wide |
| "What depends on what?" | Directed dependency graph | square-ish |
| "How are responsibilities split among roles?" | Swimlane with actor colours (REQ-028) | wide-banded |

Avoid forcing a vertical sequence into a horizontal viewBox; the diagram reads best when its viewBox matches its dominant content axis.

### REQ-058 [MUST] Data-visualization integrity

When an SVG encodes quantitative data, it MUST be honest:

- **Bar/column charts start at a zero baseline.** No truncated axes that exaggerate differences.
- **Axes are labelled** with units; ticks are legible at the 1.2rem-equivalent scale.
- **No 3-D effects, no perspective, no shadows that distort magnitude.**
- **No dual y-axes** that imply a correlation the data does not support.
- **Palette is colourblind-safe** and pairs colour with a second cue (REQ-059).
- **Avoid pie/donut charts beyond 2–3 slices** — bars compare more accurately; if you must, label each slice with its value directly.
- **Round honestly** and state the source and date of the data in the `<figcaption>` (ties to REQ-070).

A chart that distorts data fails this MUST regardless of how polished it looks.

### REQ-021 [MUST] Inline SVG only — no external references

Every SVG is an inline `<svg>` element embedded directly in the HTML. FORBIDDEN:

```html
<!-- ❌ ALL FORBIDDEN -->
<img src="diagram.svg"> <object data="diagram.svg"></object>
<embed src="diagram.svg"> <iframe src="diagram.svg"></iframe>
<div style="background: url('diagram.svg')"></div>
```

Reasons: `file://` breaks external SVG loads in some browsers; external SVGs can't read the page's CSS custom properties; and external SVGs aren't searchable, screen-reader-indexable, or diffable as part of the view.

### REQ-022 [MUST] Accessibility triple

Every SVG MUST carry all three of:

1. `role="img"` on the `<svg>`
2. `aria-labelledby="title-id desc-id"` referencing two child element IDs
3. A `<title id="…">` AND a `<desc id="…">` as the first two children of the `<svg>`

```html
<svg viewBox="0 0 1100 380" role="img"
     aria-labelledby="svg-timeline-title svg-timeline-desc">
  <title id="svg-timeline-title">Release pipeline — eleven-step timeline with role lanes</title>
  <desc id="svg-timeline-desc">Annotated horizontal timeline. Three role bands span the steps:
    discovery (steps 1–5), a three-reviewer gate (step 6), and build (steps 7–11). Each step is
    labelled with the artifact produced at that step.</desc>
  <!-- rest of SVG -->
</svg>
```

The `<title>` is one sentence — the SVG's name. The `<desc>` is 2–4 sentences — what a screen-reader user needs to understand the content without seeing it. Both are MANDATORY.

### REQ-023 [MUST] Figure + figcaption wrapper

Every SVG is wrapped in a `<figure class="diagram-container">` with a `<figcaption class="diagram-caption">` below it. The figcaption is **not** redundant with the `<desc>`: the `<desc>` describes the *picture* (for screen readers); the `<figcaption>` explains the *insight* the picture delivers (for sighted readers).

```html
<figure class="diagram-container">
  <svg viewBox="0 0 1100 640" role="img" aria-labelledby="svg-arch-title svg-arch-desc">
    <title id="svg-arch-title">…</title>
    <desc id="svg-arch-desc">…</desc>
    <!-- diagram content -->
  </svg>
  <figcaption class="diagram-caption">
    Discovery is what teams often call "refinement"; build is "implementation." Between them sit
    three independent reviewers, and underneath everything sits the permanent record.
  </figcaption>
</figure>
```

```css
.diagram-container {
  max-width: 100%; margin: 24px auto; padding: 24px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); overflow-x: auto;
}
.diagram-container svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
.diagram-caption {
  font-size: 1.0rem; line-height: 1.55; color: var(--text-secondary);
  text-align: center; margin: 1rem auto 0; font-style: italic; max-width: 900px;
}
```

### REQ-024 [MUST] viewBox + responsive sizing

Every SVG MUST declare a `viewBox`. Width/height attributes on `<svg>` are FORBIDDEN at the markup level — sizing is controlled by container CSS (`max-width: 100%; height: auto`).

```html
<svg viewBox="0 0 1100 380" role="img" …>                 <!-- ✅ correct -->
<svg width="1100" height="380" viewBox="0 0 1100 380">     <!-- ❌ breaks responsive scaling -->
```

### REQ-025 [SHOULD] viewBox aspect ratio per diagram intent

| Diagram type | viewBox shape | Example dims |
|---|---|---|
| Timeline / horizontal flow | wide | `0 0 1100 380` |
| Sequence diagram (vertical lifelines) | tall | `0 0 720 1560` |
| Layered architecture (stacked tiers) | tall-ish | `0 0 1100 640` |
| State machine / graph | square-ish | `0 0 800 800` |
| Quick-reference card / legend | compact | `0 0 600 300` |

### REQ-026 [MUST] SVG fonts reference theme tokens

Text inside SVGs uses the same three font families as the page:

```html
<text font-family="…sans token…" font-size="14">…</text>          <!-- body annotations -->
<text font-family="…mono token…" font-size="11" font-weight="700">…</text>   <!-- identifiers/numbers -->
<text font-family="…display token…" font-size="16" font-weight="700">…</text> <!-- labels/headers -->
```

SVG font sizes are in user units, not rem — pick sizes proportional to the viewBox (typically 11–16 for body, 16–20 for headers, 24+ for emphasised numbers).

### REQ-027 [MUST] SVG colours use semantic intent, not random hex

Colours inside SVGs MUST map to one of: the accent system, the four semantic colours, the text ramp, or an actor-system colour (REQ-028). Hard-coded hex is permitted inside the SVG (most renderers don't resolve CSS custom properties on `fill=`), but the hex MUST equal the value of the corresponding theme token. If the theme changes, regenerate the SVG hex to match.

Forbidden: three different greens in one diagram; rainbow gradients on flow arrows; colours not present in the theme palette.

### REQ-028 [SHOULD] Actor colour system for role-based diagrams

When a diagram depicts WHO does WHAT (workflows, sequence diagrams, swimlanes), assign each distinct actor type a dedicated colour from a small set and use it consistently across every diagram in the view. A view that depicts roles MUST include a small `.actor-legend` above the first relevant diagram (or sticky near it) so readers learn the mapping once. Colour MUST be paired with a label or shape (REQ-059) so the mapping survives for colourblind readers.

### REQ-029 [MUST] Density cap by audience level

| Audience tier | Max nodes | Max edges | Max distinct colours |
|---|---|---|---|
| L1 (executive) | 5 | 8 | 3 |
| L2 (manager / lead) | 8 | 14 | 4 |
| L3 (engineer / architect) | 14 | 24 | 5 |
| L4 (deep onboarding) | 20 | 36 | 6 |

If a diagram exceeds its cap, split it (REQ-060) rather than cramming. The five-entity maximum for L1 is non-negotiable — an executive cannot decode a 12-node graph in a five-minute briefing.

### REQ-030 [MUST] One SVG = one question

Each SVG answers exactly ONE question, declared in its `<title>`. If a diagram answers two questions, it is two diagrams. Well-formed titles: "What are the main actors and how do they interact?"; "What is the complete workflow from idea to production?"; "Where are the quality gates and what do they enforce?". Bad titles: "The architecture and how it relates to security and deployment" (three questions); "Everything that happens" (a topic, not a question).

### REQ-031 [SHOULD] Scoped, uniquely-IDed `<defs>` — including title/desc

Reusable SVG elements (arrowheads, markers, gradients, patterns) are declared in a `<defs>` block scoped to that SVG. When multiple SVGs share a page, suffix every ID — markers, gradients, **and the `<title>`/`<desc>` IDs** — with the SVG's purpose (`arrow-timeline`, `svg-arch-title`, `svg-arch-desc`) so IDs cannot collide. Colliding `id`s across SVGs silently break `aria-labelledby` and marker references.

```html
<svg viewBox="0 0 1100 280" role="img" aria-labelledby="svg-flow-title svg-flow-desc">
  <title id="svg-flow-title">…</title><desc id="svg-flow-desc">…</desc>
  <defs>
    <marker id="arrow-flow" viewBox="0 0 12 8" refX="11" refY="4"
            markerWidth="12" markerHeight="8" orient="auto">
      <polygon points="0 0, 12 4, 0 8" fill="#94a3b8"/>
    </marker>
  </defs>
  …
</svg>
```

### REQ-032 [SHOULD] Annotated, not decorative

A high-trust SVG carries text annotations: step numbers, status labels, filenames, version tags, the constraint being enforced, item counts per band. A "pretty" SVG with no labels fails this rule.

### REQ-033 [SHOULD] Two to four SVGs per view; five is the soft cap

Walkthroughs typically use 2–3 SVGs; analyses 2–4. More than 5 is a smell — usually the view is trying to be two views (split it) or some diagrams are filler (cut them). Adding diagrams to honour density caps (REQ-029, REQ-060) is correct, but only up to ~5.

### REQ-034 [MAY] CSS-driven SVG animation

Permitted when it adds information value (e.g. a pulsing dash along a flow arrow showing direction). MUST honour `prefers-reduced-motion`:

```css
.flow-animated { stroke-dasharray: 8 4; animation: flowPulse 1.2s linear infinite; }
@keyframes flowPulse { 0% { stroke-dashoffset: 20; } 100% { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .flow-animated { animation: none; } }
```

JS-driven SVG interactivity is permitted but MUST work via `file://` (no fetch, no module imports).

### REQ-059 [MUST] Redundant encoding — colour is never the sole carrier inside an SVG

Inside every colour-coded SVG, each encoded category MUST also carry a second cue: a text label, a shape, an icon, or a pattern (dash style, hatch). An actor diagram that distinguishes roles by hue alone fails colourblind readers and fails this MUST. Example: human = cyan **solid circle**, agent = purple **square**, pipeline = rose **diamond**, plus a one-word label on each.

### REQ-060 [SHOULD] Overview-then-detail pair instead of one dense diagram

When content exceeds the density cap for its audience (REQ-029), do not cram. Render two diagrams: an **overview** at the audience's tier (the shape of the whole), then a **detail** that zooms into one region. Caption the pair so the reader knows the detail is a magnification of the overview, not a separate system.

### REQ-061 [SHOULD] Direct labels over legends

Label data and nodes *in place* rather than forcing the reader to bounce between a legend and the diagram. Use a legend only when direct labels would overlap or when a shared key (e.g. the actor system, REQ-028) is reused across several diagrams.

### REQ-062 [MUST] Real text, never outlined paths

All text inside an SVG MUST be live `<text>` / `<tspan>` elements, never glyphs converted to `<path>` outlines. Outlined text is unsearchable, unselectable, invisible to assistive tech, breaks at scale, and cannot be translated or corrected without re-exporting the asset. If a diagram was produced by a vector tool that outlines fonts on export, restore real text before embedding. This is what keeps the annotations of REQ-032 actually useful.

---

## §5 Content & Tone

### REQ-035 [MUST] First-screen comprehension test ("the coffee test")

The first viewport-height of content (page header + the first section above the fold) MUST be readable by a non-technical senior stakeholder holding a coffee:

- **≤ 200 words** above the fold (including the subtitle, excluding the title and chips)
- **Zero unexplained jargon** — every domain term in the first viewport is either common English OR defined inline at first use
- **State the "what" and the "why" before the "how"** — the reader must know what the document is and why it exists without scrolling

The page title may use a domain term (it's a noun phrase, not a sentence to parse). The subtitle and first paragraph cannot.

### REQ-036 [MUST] Conversational voice

Prose uses second person ("you") and first-person plural ("we"), not third-person passive. The reader is being walked through something by a person, not reading a specification.

> Good: "When you open a pull request, the agent runs three reviewers in parallel. We chose this so review time doesn't grow with the number of reviewers."
>
> Bad: "Upon opening of a pull request, the system shall invoke three reviewer agents in parallel. This design was chosen to ensure review duration does not scale linearly with reviewer count."

Exceptions: data tables, code blocks, formal API references, and direct quotations keep their natural register.

### REQ-037 [MUST] Plain English at first use, then promote

Every domain term gets a plain-English gloss at first use; subsequent uses may use the vocabulary directly.

> "The build phase (an automated workflow that turns an approved plan into working code) starts when the discovery plan is approved. The build orchestrator then dispatches the first task to the planning agent."

Re-glossing every occurrence is condescending; never glossing is exclusionary. Glossing once is the standard.

### REQ-038 [MUST] Numbered section markers carry meaning

The `01`, `02`, `03` markers imply reading order. If your sections are NOT meant to be read in order (a reference index, an independent-question FAQ), do not number them — use unnumbered headings with a different visual marker.

### REQ-039 [SHOULD] Evidence citation pattern

When a view makes a claim that depends on source material (a transcript, a config file, code, a measurement), link directly to the source. Use the mono `<code>` style for the link target and a natural-language phrase as the link text:

```html
<p>The decision on 2026-04-02
<a href="../sources/decision-2026-04-02.md"><code>sources/decision-2026-04-02.md</code></a>
moved us away from the top-down taxonomy.</p>
```

A claim without evidence is a smell — find the evidence or weaken the claim. (See REQ-070 for required date + provenance on the source, and §6 for how to handle sources that disagree.)

### REQ-040 [SHOULD] Audience badges and hint pop-overs

Mark an intentionally beginner-friendly (or intentionally advanced) section with a coloured badge near its heading. For terms whose definition would interrupt flow, use a keyboard-accessible inline hint pop-over:

```html
<h2><span class="num">02</span> Plain-English concepts <span class="beginner-badge">Beginner-friendly</span></h2>

<span class="term hint" tabindex="0">Version control<span class="hint-pop">
  A history book for your code. Every change is a labelled snapshot you can revisit.
</span></span>
```

Hint pop-overs MUST be keyboard-accessible (`tabindex="0"`) and dismissable on blur.

### REQ-041 [SHOULD] Callout patterns

Three flavours, each a tinted background with a left accent border:

```html
<div class="callout callout-info">…</div>   <!-- neutral / context -->
<div class="callout callout-tip">…</div>    <!-- helpful aside -->
<div class="callout callout-warn">…</div>   <!-- caution -->
```

Callouts are short (1–3 sentences). Long content belongs in a section, not a callout. (Decision records and dissent use their own dedicated patterns — see REQ-064/065.)

### REQ-042 [SHOULD] [PAUSE] markers for live-presented views

For views presented live (briefings, walkthroughs), insert `[PAUSE — ask for questions]` markers in italic at natural discussion points. They signal to the presenter where to stop and to the silent reader where the natural breath-points are.

### REQ-043 [SHOULD] Metadata chips below the page title

The page header carries a row of meta chips communicating audience, source, date, and outcome:

```html
<div class="meta-chips">
  <span class="meta-chip audience">L1–L2 · Beginner</span>
  <span class="meta-chip repo">org/repo</span>
  <span class="meta-chip date">2026-05-12</span>
  <span class="meta-chip result">29/29 checks passing</span>
</div>
```

Four chips is typical; six is the upper limit. Chip background colour conveys meaning (success family for positive outcomes, warning for cautions, neutral accent for context).

---

## §6 Content Integrity & Disagreement Governance

This is the section that makes a view *trustworthy*, not merely *attractive*. A view often records analysis, reconciles conflicting sources, or captures a decision that not everyone agreed with. The rules below govern how that content is represented so the view neither launders disagreement into false consensus nor presents opinion as fact.

### REQ-063 [MUST] Separate fact, interpretation, and recommendation

Within any analytical or decision content, the three registers must be visually and grammatically distinguishable, never blended into one undifferentiated paragraph:

- **Fact** — what the sources say happened or what was measured. Cited (REQ-039, REQ-070).
- **Interpretation** — what the author infers from the facts. Marked as inference ("this suggests…", "we read this as…").
- **Recommendation** — what the author proposes doing about it. Marked as a proposal, not a foregone conclusion.

A reader must be able to accept the facts while disagreeing with the interpretation. Collapsing the three is the single most common way a view loses credibility with an expert audience.

### REQ-064 [MUST] Decision-record pattern

When a view records a decision, it MUST present, in this order: **Context** (what prompted the decision), **Options considered** (at least the chosen one and one rejected alternative), **Decision** (what was chosen), **Rationale** (why), and **Consequences / trade-offs** (what this costs). A bare "we decided X" with no alternatives and no trade-off is non-conformant — it is an assertion, not a decision record.

```html
<section id="s05-decision-taxonomy" class="glass-panel">
  <h2><span class="num">05</span> Decision: bottom-up taxonomy</h2>
  <div class="decision-record">
    <p class="dr-context"><strong>Context.</strong> …</p>
    <p class="dr-options"><strong>Options.</strong> (A) top-down … (B) bottom-up … </p>
    <p class="dr-decision"><strong>Decision.</strong> We chose (B). </p>
    <p class="dr-rationale"><strong>Rationale.</strong> … </p>
    <p class="dr-consequences"><strong>Trade-offs.</strong> … </p>
  </div>
</section>
```

### REQ-065 [MUST] Represent disagreement and minority views explicitly — do not flatten

When sources, reviewers, or stakeholders disagreed, the view MUST surface that disagreement rather than smoothing it into a single voice. Attribute each position to its source, state the strongest version of each (steel-man, not straw-man), and — if a position lost — say *why* without erasing it. A dedicated pattern keeps dissent visible:

```html
<div class="dissent" role="note" aria-label="Recorded disagreement">
  <p class="dissent-position"><strong>Minority view (reviewer&nbsp;B).</strong>
     The strongest form of the opposing argument, in its own terms.</p>
  <p class="dissent-resolution"><strong>How it was resolved.</strong>
     Why the majority position prevailed, or that it remains open.</p>
</div>
```

Forbidden: presenting a contested decision as if it were unanimous; deleting a rejected position so only the winner survives; attributing a view to "the team" when the team was split.

### REQ-066 [SHOULD] Confidence labelling on contested or uncertain claims

Where a claim is uncertain, contested, or extrapolated, label its confidence so the reader can weight it. Use a small, consistent scale and pair it with text (REQ-059 applies to chips too):

```html
<span class="confidence high">High confidence</span>
<span class="confidence medium">Medium — single source</span>
<span class="confidence low">Low — inferred, unverified</span>
```

Do not decorate every sentence with a confidence chip; reserve them for claims where the reader's decision changes with the confidence level.

### REQ-067 [MUST] Source precedence when sources conflict — and show the superseded one

When two sources disagree on a fact, the view MUST (a) state which source takes precedence and the rule that decides it (e.g. "most recent dated source wins", "primary source over summary", "signed-off version over draft"), and (b) show the superseded value rather than silently dropping it:

> The throughput figure is **1,240/day** per the 2026-05-10 measurement, which supersedes the 900/day estimate in the 2026-04 planning note (more recent, measured rather than estimated).

Silently choosing one number and hiding the conflict is non-conformant — it destroys the reader's ability to audit the claim.

### REQ-068 [SHOULD] Visible regeneration changelog

When a view is regenerated after content changes (a disagreement resolved, a correction, new evidence), record it visibly — not only in the JSON-LD `dateModified`. A compact changelog near the footer lets a returning reader see what changed and trust that the view is current:

```html
<section id="s99-changelog" class="glass-panel">
  <h2><span class="num">99</span> Revision history</h2>
  <ul>
    <li><strong>2026-05-12</strong> — Reconciled the throughput conflict (REQ-067); added reviewer B's dissent.</li>
    <li><strong>2026-05-11</strong> — First generation.</li>
  </ul>
</section>
```

### REQ-069 [SHOULD] Reviewer / approval attribution

A governance view SHOULD record who reviewed or approved it and at what conformance level, so the claim in §13 is attributable rather than self-asserted:

```html
<footer>
  <p>Reviewed by <span class="reviewer">Design-Governance Owner</span> · 2026-05-12 ·
     Conformance: Level 2 — Recommended</p>
</footer>
```

### REQ-070 [MUST] Date + provenance on every cited source

Every evidence citation (REQ-039) MUST carry the source's date and enough provenance to locate it (path, document title, or stable identifier). A citation with no date cannot be weighed for freshness and cannot participate in source-precedence (REQ-067). Where a source is undated, mark it `undated` explicitly rather than omitting the field.

---

## §7 Navigation & Chrome

### REQ-044 [MUST] Sticky jump nav with active-section highlighting

The jump nav is `position: sticky; top: 0;`, sits immediately below the page header, and contains one anchor per body section in document order. An IntersectionObserver highlights the anchor whose section is in view (script in Appendix B). Without active highlighting the nav is dead weight; with it the reader always knows where they are.

```html
<nav class="jump-nav" aria-label="Sections">
  <a href="#s01-overview">01 Overview</a>
  <a href="#s02-concepts">02 Concepts</a>
  …
</nav>
```

### REQ-045 [MUST] Back-to-top floating button

A fixed-position back-to-top button sits lower-right, invisible at page top, fading in after one viewport of scroll (script in Appendix B):

```html
<a class="back-top-btn" href="#" aria-label="Back to top">↑</a>
```

### REQ-046 [SHOULD] Cross-reference cards at page end

If the view is part of a series, end with a grid of cross-reference cards. Each shows the destination's type, title, and a one-sentence description. To avoid competing with section `<h2>`s in the document outline, the aside's heading SHOULD be an `<h2>` placed inside the `<aside>` landmark (which scopes it).

```html
<aside class="related-pages">
  <h2>Related views</h2>
  <div class="cross-ref-grid">
    <a class="cross-ref" href="…">
      <span class="cross-ref-type">Analysis</span>
      <span class="cross-ref-title">Architect's synthesis</span>
      <span class="cross-ref-desc">The full verdict with evidence from the run.</span>
    </a>
    …
  </div>
</aside>
```

### REQ-047 [SHOULD] Footer with provenance

The footer carries generation metadata: when the view was generated, by what skill/agent (when applicable), source-of-truth paths, conformance level, and attribution. Text-only, dimmed, centred.

```html
<footer>
  <p>Generated 2026-05-12 from <code>plan.md</code>. Source: <code>reports/q3-review/</code>.</p>
  <p>HTML View Quality Standard v2.0.0 — Level 2 Recommended</p>
</footer>
```

---

## §8 Accessibility & Standards

### REQ-048 [MUST] WCAG 2.1 AA targets

- Text contrast ≥ 4.5:1 against its background (large text ≥ 3:1)
- Every interactive element keyboard-reachable; never `tabindex="-1"` on interactive content
- Every interactive element has a visible focus indicator (do not `outline: none` without replacing it — see REQ-073)
- Every image / SVG has alt text (REQ-022 for SVGs)
- Form controls (if any) have associated `<label>` elements
- Colour is never the sole carrier of meaning — pair it with text, icon, or shape (REQ-059 for SVGs)

### REQ-049 [MUST] Semantic HTML

- `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>` for landmarks
- `<h1>`–`<h4>` in correct order
- `<ul>`/`<ol>`/`<li>` for lists (never fake lists with sibling `<div>`s)
- `<table>` only for tabular data; never for layout
- `<button>` for actions, `<a>` for navigation; never `<div onclick>`

### REQ-050 [SHOULD] Respect prefers-reduced-motion

Wrap every animation in a `@media (prefers-reduced-motion: reduce)` guard that disables or shortens it. Users with vestibular disorders depend on this.

### REQ-051 [MUST] Responsive at 360px, 768px, 1200px

The view MUST render correctly at 360px (phone — text wraps, single column, sticky nav scrolls horizontally), 768px (tablet — single column, grids collapse), and 1200px+ (desktop / projector — full layout per REQ-003).

```css
@media (max-width: 768px) {
  .container { width: 95%; }
  .banner-grid, .label-grid, .cross-ref-grid { grid-template-columns: 1fr; }
  .jump-nav-inner { overflow-x: auto; }
}
```

### REQ-071 [MUST] Skip-to-content link

The first focusable element is a skip link that jumps past the sticky nav to `<main>`. It is visually hidden until focused:

```css
.skip-link {
  position: absolute; left: -9999px; top: 0; z-index: 300;
  background: var(--accent-primary); color: var(--bg-primary);
  padding: 8px 16px; border-radius: var(--radius-sm);
}
.skip-link:focus { left: 8px; top: 8px; }
```

### REQ-072 [MUST] Document language attribute

The `<html>` element MUST declare its language: `<html lang="en">` (or the document's actual language). This is a baseline WCAG requirement and affects screen-reader pronunciation.

### REQ-073 [SHOULD] Visible focus indicator via :focus-visible

Provide a consistent, visible focus ring rather than relying on (or removing) the browser default:

```css
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

---

## §9 Theme Adapter Contract — plug in your own theme

This spec is theme-agnostic. The contract: **define the named CSS custom properties from REQ-017 in your stylesheet, with values that fit your theme.** The rules then bind to those names.

### Pattern A — Greenfield project

Copy the token list from REQ-017 into your `:root`, pick values that fit your brand, ship a single `assets/css/your-design.css`, and `<link>` it in every view.

### Pattern B — Existing design system (Tailwind, Bootstrap, Material, custom)

Add a thin adapter layer mapping the spec's required tokens to your existing tokens, then `<link>` your design system first and the adapter second:

```css
:root {
  --bg-primary:       var(--your-bg);
  --text-primary:     var(--your-text);
  --accent-primary:   var(--your-brand-primary);
  --accent-secondary: var(--your-brand-secondary);
  --font-sans:        var(--your-body-font);
  --font-display:     var(--your-heading-font);
  --font-mono:        var(--your-mono-font);
  /* …map every REQ-017 token… */
}
```

### Pattern C — Light corporate theme

Same as A or B, with: light `--bg-primary` and dark `--text-primary`; `--glass-bg` as a near-opaque card (alpha ~0.95) with `backdrop-filter` omitted; the gradient title (REQ-013) using two darker accents that stay readable on light; darker `--glass-border` (alpha ~0.15). The rules in §1–§8 are unchanged; only the values flip. (See Appendix D for a full worked example.)

### What you MUST NOT do in your adapter

- **Rename** the required tokens. The spec references `--text-primary` by name; if you map it to `--your-content-fg`, generators won't find it.
- **Drop** required tokens. Every REQ-017 token must resolve to a value, even with a sensible fallback.
- **Override the typography minimums** in REQ-010. The 1.2rem floor is theme-independent.

---

## §10 Self-Audit Checklist

Run before declaring a view conformant. Every unchecked MUST is a blocker.

### Page architecture
- [ ] REQ-001 Shell order: skip-link → header → sticky nav → main → footer → back-top
- [ ] REQ-002 No max-height / overflow clamp on body, main, container, or sections
- [ ] REQ-003 Container `width: 90%; max-width: 1400px; margin: 0 auto`; no `max-width` on body prose
- [ ] REQ-004 Every `<section>` has a unique `id` and a two-digit number marker in its `<h2>`
- [ ] REQ-005 `scroll-behavior: smooth`; `scroll-margin-top` ≥ nav height + 8px
- [ ] REQ-007 No fetch / XHR / dynamic imports / service workers; opens via `file://`
- [ ] REQ-008 Schema.org `TechArticle` JSON-LD in `<head>`
- [ ] REQ-009 Single-purpose page

### Typography
- [ ] REQ-010 Reading text ≥ 1.2rem on all body-prose elements
- [ ] REQ-011 Exactly one `<h1>`; no skipped heading levels
- [ ] REQ-012 Three font roles only; no decorative fonts in body
- [ ] REQ-013 Page H1 uses gradient text treatment
- [ ] REQ-014 Inline `<code>` styled (mono, tinted background, accent foreground)
- [ ] REQ-015 Lists have `padding-inline-start ≥ 1.75rem` and `list-style-position: outside`
- [ ] REQ-052 Wide tables wrapped in scrollable `.table-container`
- [ ] REQ-053 `<pre>` blocks styled with mono floor and `overflow: auto`
- [ ] REQ-054 Long tokens wrap (`overflow-wrap: anywhere`)
- [ ] REQ-055 `@media print` block present

### Color & surface
- [ ] REQ-017 All Theme Adapter Contract tokens defined in `:root`
- [ ] REQ-018 At most two accents (excluding the four semantic colours)
- [ ] REQ-019 Sections alternate surface when count ≥ 6
- [ ] REQ-020 Semantic colours used only for meaning

### SVG craft & selection
- [ ] REQ-056 Visual form chosen correctly (SVG vs table vs list)
- [ ] REQ-057 Diagram archetype matches the communicative question
- [ ] REQ-058 Charts are honest (zero baseline, labelled axes, no 3-D/truncation, colourblind-safe)
- [ ] REQ-021 Every SVG inline; zero `<img src="*.svg">`/`<object>`/`<embed>`
- [ ] REQ-022 Every SVG has `role="img"`, `aria-labelledby`, child `<title>` + `<desc>`
- [ ] REQ-023 Every SVG wrapped in `<figure class="diagram-container">` with `<figcaption>`
- [ ] REQ-024 Every SVG has a `viewBox`; zero `width`/`height` attrs on `<svg>`
- [ ] REQ-025 viewBox aspect ratio matches reading axis
- [ ] REQ-026 SVG `<text>` references the three theme font families
- [ ] REQ-027 SVG colours map to theme tokens / semantic colours
- [ ] REQ-028 Actor-colour legend present when diagrams depict roles
- [ ] REQ-029 SVG density inside the cap for the audience tier
- [ ] REQ-030 Each SVG answers exactly one declared question (in its `<title>`)
- [ ] REQ-031 Scoped `<defs>`; unique IDs for markers AND `<title>`/`<desc>` across SVGs
- [ ] REQ-033 View has 2–4 SVGs (soft cap 5)
- [ ] REQ-059 Colour never the sole carrier inside an SVG
- [ ] REQ-060 Over-dense content split into overview + detail
- [ ] REQ-061 Direct labels preferred over legends
- [ ] REQ-062 SVG text is live `<text>`, never outlined paths

### Content & tone
- [ ] REQ-035 First viewport ≤ 200 words, zero unexplained jargon, what + why before how
- [ ] REQ-036 Conversational voice — "you" / "we"
- [ ] REQ-037 Domain terms glossed at first use, then used directly
- [ ] REQ-038 Section numbers imply reading order; document is sequential
- [ ] REQ-039 Claims that need evidence link to source
- [ ] REQ-041 Callouts are short (1–3 sentences)
- [ ] REQ-043 Page header carries 3–6 meta chips

### Content integrity & disagreement governance
- [ ] REQ-063 Fact, interpretation, and recommendation visually/grammatically separated
- [ ] REQ-064 Decisions presented as full records (context, options, decision, rationale, trade-offs)
- [ ] REQ-065 Disagreement / minority views surfaced and attributed, not flattened
- [ ] REQ-066 Contested / uncertain claims carry confidence labels
- [ ] REQ-067 Conflicting sources reconciled with a stated precedence rule; superseded value shown
- [ ] REQ-068 Visible revision history present when the view has been regenerated
- [ ] REQ-069 Reviewer / approval attribution recorded
- [ ] REQ-070 Every cited source carries a date + provenance

### Navigation & chrome
- [ ] REQ-044 Sticky jump nav with active-section highlight
- [ ] REQ-045 Back-to-top button appears after one viewport of scroll
- [ ] REQ-046 Cross-reference cards if part of a series
- [ ] REQ-047 Footer carries generation metadata + attribution

### Accessibility & standards
- [ ] REQ-048 WCAG 2.1 AA: contrast ≥ 4.5:1; visible focus
- [ ] REQ-049 Semantic landmarks
- [ ] REQ-050 `prefers-reduced-motion` disables animation
- [ ] REQ-051 Responsive at 360 / 768 / 1200px
- [ ] REQ-071 Skip-to-content link present and focus-revealed
- [ ] REQ-072 `<html lang>` set
- [ ] REQ-073 `:focus-visible` ring defined

---

## §11 Automated Conformance Check

The §10 checklist is for humans; the checks below catch the mechanical failures before review. Run them from the directory containing your views. They are heuristics — a clean run does not prove conformance, but a dirty run proves non-conformance.

```bash
# Set the directory holding the views
DIR="./views"

echo "== REQ-002: no height clamp (expect zero matches) =="
grep -lE 'max-height|height:\s*100vh|overflow:\s*(hidden|scroll)' "$DIR"/*.html

echo "== REQ-021: no external SVG references (expect zero) =="
grep -lE '<img[^>]+\.svg|<object[^>]+\.svg|<embed[^>]+\.svg' "$DIR"/*.html

echo "== REQ-022: every SVG has the accessibility triple =="
for f in "$DIR"/*.html; do
  svg=$(grep -c '<svg' "$f"); role=$(grep -c 'role="img"' "$f")
  lab=$(grep -c 'aria-labelledby' "$f"); ttl=$(grep -c '<title' "$f")
  printf '%s  svg=%s role=%s labelledby=%s title=%s\n' "$(basename "$f")" "$svg" "$role" "$lab" "$ttl"
done

echo "== REQ-024: no width/height attrs on <svg> (expect zero) =="
grep -lE '<svg[^>]+\b(width|height)=' "$DIR"/*.html

echo "== REQ-033: SVG count per view (target 2–4, soft cap 5) =="
for f in "$DIR"/*.html; do printf '%s: ' "$(basename "$f")"; grep -c '<svg' "$f"; done

echo "== REQ-010: 1.2rem reading floor declared =="
grep -c 'font-size:\s*1\.2rem' "$DIR"/*.html

echo "== REQ-071 / REQ-072: skip link and lang attribute =="
grep -L 'class="skip-link"' "$DIR"/*.html       # files MISSING the skip link
grep -L '<html[^>]*\blang=' "$DIR"/*.html         # files MISSING lang
```

Wire these into CI (a failing grep becomes a non-zero exit) to make MUST-tier mechanical rules un-mergeable when violated.

---

## §12 Watch-Outs for the Consuming Generator

Implicit knowledge a generator will routinely get wrong. Read before generating.

1. **No view types means infer the narrative arc.** This spec defines no view types, section lists, or templates. When asked for a "walkthrough" / "analysis" / "cheatsheet", infer the arc from the request. Default to a plain-English-first explainer with numbered sequential sections; switch to a denser, evidence-heavy register only when the user explicitly asks for a technical reference or deep-dive.
2. **The 1.2rem floor is not theme-negotiable.** You will be tempted to inherit the host's 1rem body size. Don't — re-assert the floor in the view's inline `<style>` (REQ-010). If the host stylesheet objects, the host stylesheet is wrong for stakeholder-facing artifacts.
3. **Single-accent themes need a gradient fallback.** If the theme has only `--accent-primary`, use a `--text-primary`→`--accent-primary` gradient for the title. Never invent a second accent (breaks REQ-018).
4. **Cheatsheet ≠ dense.** The density cap (REQ-029) still applies to "quick references". Compact means short, not crammed; add a second SVG (REQ-060) rather than violating density.
5. **`var(--token)` doesn't always resolve inside SVGs.** Options: (1) hard-code the hex matching the token (most reliable, REQ-027); (2) a `<style>` element inside the `<svg>` using child selectors; (3) `fill="currentColor"` for monochrome icons. Use (1) for complex multi-colour diagrams.
6. **SVG width/height attributes break responsive scaling.** Use `viewBox` only (REQ-024).
7. **file:// breaks more than you think.** ES module imports, `fetch()`, service workers, and non-font CDNs all misbehave when the file is double-clicked. Test by opening via `file://` before declaring done.
8. **The coffee test fails silently.** You can satisfy every other rule and still fail REQ-035. After drafting the first section, re-read it as if you have no domain knowledge; any term you can't immediately parse is a fail — gloss or remove it.
9. **Conversational ≠ unprofessional.** REQ-036's "you/we" is the register of a senior engineer explaining a system to a colleague — confident, direct, evidence-anchored — not slang, jokes, or marketing.
10. **Section numbering implies reading order.** If sections aren't sequential (a reference index, an independent-question FAQ), don't number them (REQ-038).
11. **Don't fabricate evidence.** REQ-039/REQ-070 mean link to *real*, dated sources. If you can't find one, weaken the claim. A broken or invented citation is worse than no citation.
12. **Don't flatten disagreement into consensus.** §6's biggest failure mode: a model "tidies up" conflicting sources into one confident voice. Surface the conflict (REQ-065), state the precedence rule (REQ-067), and keep the rejected position visible. False consensus is a credibility-destroying defect, not a stylistic choice.
13. **Don't blend fact, inference, and recommendation.** REQ-063. Mark inferences as inferences and proposals as proposals; a reader must be able to accept your facts and still reject your conclusion.
14. **When the host has multiple stylesheet generations**, pick the newer (check file date or declared version), adapt that one to §9, and document the choice in the footer. Don't honour both at once.
15. **The example themes are EXAMPLES.** Appendices C and D show two valid token sets. They are not the answer for your project. Copying a dark-glass theme into a light corporate brand produces an unreadable view.
16. **Prefer HTML over SVG for tabular/list content** (REQ-056). Drawing a table in SVG is the most common a11y own-goal.

---

## §13 Conformance Levels & Labelling

- **Level 1 — Conformant:** satisfies ALL MUST rules.
- **Level 2 — Recommended:** also satisfies ALL SHOULD rules.
- **Level 3 — Exemplary:** satisfies every rule including MAYs.

Declare the level in the footer, and — for governance views — attribute the reviewer (REQ-069):

```html
<footer>
  <p>HTML View Quality Standard v2.0.0 — Level 2 Recommended ·
     Reviewed by Design-Governance Owner · 2026-05-12</p>
</footer>
```

Reviewers verify the claim against §10/§11. False conformance claims are a credibility hit; under-claim if uncertain.

---

## §14 Spec Governance

The standard governs itself by the same discipline it asks of views.

### REQ-074 [MUST] Immutable REQ IDs

`REQ-NNN` identifiers are immutable once published. New rules are **appended** with the next free number; existing numbers are never renumbered, reused, or repurposed. A retired rule is marked `[DEPRECATED in vX.Y.Z — see REQ-MMM]` and kept in place so external citations never dangle. Section numbers (`§N`) may be reorganized across major versions, so always cite by `REQ-NNN`.

### Versioning

The standard uses semantic versioning. PATCH = clarifications and typo fixes; MINOR = new SHOULD/MAY rules or non-breaking additions; MAJOR = new MUST rules or a reorganization that changes conformance. Record the change in the document's revision note and bump the version in the frontmatter and the footer string.

---

## Appendix A — Reference Stylesheet Skeleton

A minimal stylesheet (token names per REQ-017, values per the host project) satisfying REQ-001 through REQ-073.

```css
/* === Theme Adapter Contract (host project fills these) === */
:root {
  --bg-primary: /* host */; --bg-secondary: /* host */; --bg-tertiary: /* host */;
  --bg-card: /* host */; --bg-glass: /* host */;
  --text-primary: /* host */; --text-secondary: /* host */;
  --text-tertiary: /* host */; --text-muted: /* host */;
  --accent-primary: /* host */; --accent-secondary: /* host */;
  --accent-primary-dim: /* host */; --accent-secondary-dim: /* host */;
  --color-success: /* host */; --color-warning: /* host */; --color-error: /* host */;
  --glass-bg: /* host */; --glass-border: /* host */;
  --glass-border-hover: /* host */; --glass-border-accent: /* host */;
  --font-sans: /* host */; --font-display: /* host */; --font-mono: /* host */;
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 24px;
  --transition-glass: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* === Reset === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font-sans); font-size: 1.2rem; line-height: 1.75;
  background: var(--bg-primary); color: var(--text-primary); min-height: 100vh;
}

/* === Reading-text floor (REQ-010) === */
p, li, td, th, dd, dt, blockquote, figcaption, label,
.callout, .qa-a, .qa-q, .gloss, .section-description { font-size: 1.2rem; line-height: 1.75; }

/* === Long-token wrapping (REQ-054) === */
code, .mono, td, a[href] { overflow-wrap: anywhere; }

/* === Lists (REQ-015) === */
ol, ul { padding-inline-start: 2.25rem; margin-block: 0.85rem 1.1rem; list-style-position: outside; }
ol ol, ol ul, ul ol, ul ul { padding-inline-start: 1.75rem; margin-block: 0.4rem; }
li { margin-block: 0.45rem; padding-inline-start: 0.25rem; }

/* === Container (REQ-003) === */
.container { width: 90%; max-width: 1400px; margin: 0 auto; padding: 0; }

/* === Skip link (REQ-071) === */
.skip-link { position: absolute; left: -9999px; top: 0; z-index: 300;
  background: var(--accent-primary); color: var(--bg-primary);
  padding: 8px 16px; border-radius: var(--radius-sm); }
.skip-link:focus { left: 8px; top: 8px; }

/* === Page header (REQ-001) === */
.page-header { padding: 32px 0 24px; border-bottom: 1px solid var(--glass-border); }
.page-title { font-family: var(--font-display); font-size: 1.85rem; font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; line-height: 1.2; }

/* === Sticky jump nav (REQ-044) === */
.jump-nav { position: sticky; top: 0; z-index: 100; background: var(--bg-primary);
  backdrop-filter: blur(12px); padding: 10px 0; border-bottom: 1px solid var(--glass-border); }
.jump-nav a { font-family: var(--font-mono); font-size: 0.78rem; padding: 6px 14px;
  border-radius: 20px; color: var(--text-tertiary); text-decoration: none;
  border: 1px solid transparent; transition: all 0.2s; }
.jump-nav a:hover, .jump-nav a.active { color: var(--accent-primary);
  border-color: var(--glass-border-accent); background: var(--accent-primary-dim); }

/* === Sections (REQ-004) === */
section[id] { scroll-margin-top: 60px; }
.glass-panel { background: var(--glass-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); padding: 28px; margin-bottom: 20px; backdrop-filter: blur(12px); }
.glass-panel h2 { font-family: var(--font-display); font-size: 1.4rem; font-weight: 700;
  color: var(--accent-primary); margin-bottom: 16px;
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.glass-panel h2 .num { font-family: var(--font-mono); font-size: 0.78rem;
  color: var(--text-tertiary); background: var(--accent-primary-dim);
  padding: 3px 10px; border-radius: 12px; letter-spacing: 0.08em; }

/* === Inline code (REQ-014) === */
code, .mono { font-family: var(--font-mono); font-size: 0.86em;
  background: rgba(0,0,0,0.35); padding: 0.05em 0.4em; border-radius: 4px; color: var(--accent-primary); }

/* === Code blocks (REQ-053) === */
pre { font-family: var(--font-mono); font-size: 0.95rem; line-height: 1.55;
  background: var(--bg-card); border: 1px solid var(--glass-border);
  border-radius: var(--radius-md); padding: 16px 18px; overflow: auto; }
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }

/* === Tables (REQ-052) === */
.table-container { overflow-x: auto; margin: 16px 0; }
.table-container table { width: 100%; border-collapse: collapse; }

/* === Diagram container (REQ-023) === */
.diagram-container { max-width: 100%; margin: 24px auto; padding: 24px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); overflow-x: auto; }
.diagram-container svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
.diagram-caption { font-size: 1rem; line-height: 1.55; color: var(--text-secondary);
  text-align: center; margin: 1rem auto 0; font-style: italic; max-width: 900px; }

/* === Callouts (REQ-041) === */
.callout { padding: 14px 18px; border-radius: var(--radius-sm); margin: 12px 0;
  font-size: 1.2rem; line-height: 1.6; border-left: 3px solid; }
.callout-info { background: var(--accent-primary-dim); border-color: var(--accent-primary); }
.callout-tip  { background: rgba(16,185,129,0.06); border-color: var(--color-success); }
.callout-warn { background: rgba(245,158,11,0.06); border-color: var(--color-warning); }

/* === Decision record & dissent (REQ-064 / REQ-065) === */
.decision-record { border-left: 3px solid var(--accent-secondary); padding: 10px 18px; margin: 12px 0; }
.dissent { background: var(--color-warning); background: rgba(245,158,11,0.08);
  border: 1px solid var(--color-warning); border-radius: var(--radius-sm); padding: 14px 18px; margin: 12px 0; }
.confidence { font-family: var(--font-mono); font-size: 0.78rem; padding: 3px 10px; border-radius: 12px; }
.confidence.high   { background: rgba(16,185,129,0.15); color: var(--color-success); }
.confidence.medium { background: var(--accent-primary-dim); color: var(--accent-primary); }
.confidence.low    { background: rgba(245,158,11,0.15); color: var(--color-warning); }

/* === Back-to-top (REQ-045) === */
.back-top-btn { position: fixed; bottom: 32px; right: 32px; width: 44px; height: 44px;
  border-radius: 50%; background: var(--glass-bg); border: 1px solid var(--glass-border);
  color: var(--accent-primary); font-size: 20px; display: flex; align-items: center;
  justify-content: center; text-decoration: none; z-index: 200; opacity: 0;
  pointer-events: none; transition: var(--transition-glass); }
.back-top-btn.visible { opacity: 1; pointer-events: auto; }

/* === Footer (REQ-047) === */
footer { background: var(--bg-card); border-top: 1px solid var(--glass-border);
  padding: 24px 0; margin-top: 40px; text-align: center; color: var(--text-muted); font-size: 0.85rem; }

/* === Focus (REQ-073) === */
:focus-visible { outline: 2px solid var(--accent-primary); outline-offset: 2px; border-radius: var(--radius-sm); }

/* === Reduced motion (REQ-050) === */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}

/* === Responsive (REQ-051) === */
@media (max-width: 768px) {
  .container { width: 95%; }
  .banner-grid, .label-grid, .cross-ref-grid { grid-template-columns: 1fr; }
  .jump-nav-inner { overflow-x: auto; }
}

/* === Print (REQ-055) === */
@media print {
  .jump-nav, .back-top-btn, .skip-link { display: none; }
  a[href]::after { content: " (" attr(href) ")"; font-size: 0.8em; color: #555; }
  .glass-panel { break-inside: avoid; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
```

---

## Appendix B — Minimum-viable JavaScript

Inline at the end of `<body>`. All `file://`-compatible (REQ-007).

```html
<script>
  // REQ-044 — sticky jump nav active-section highlighting
  (function () {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        const link = document.querySelector('nav.jump-nav a[href="#' + e.target.id + '"]');
        if (link && e.isIntersecting) {
          document.querySelectorAll('nav.jump-nav a').forEach(a => a.classList.remove('active'));
          link.classList.add('active');
        }
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    document.querySelectorAll('section[id]').forEach(s => obs.observe(s));
  })();

  // REQ-045 — back-to-top button visibility
  (function () {
    const btn = document.querySelector('.back-top-btn');
    if (!btn) return;
    window.addEventListener('scroll', () => {
      btn.classList.toggle('visible', window.scrollY > window.innerHeight);
    });
  })();
</script>
```

---

## Appendix C — Example Theme 1: Dark Glass (illustrative only)

> One complete, worked set of values for the Theme Adapter Contract. **This is an EXAMPLE.** Do NOT copy it verbatim — substitute your own theme's values. If your project is light-themed or corporate-themed, see Appendix D. The spec's rules (§1–§8) apply unchanged; only the values flip.

A dark glassmorphism treatment: translucent panels over a dark mesh background, `backdrop-filter: blur()` on every panel; deep-navy backgrounds with cyan + purple accents; a sans/display/mono font trio.

```css
:root {
  /* Background surfaces */
  --bg-primary:   #0a0e27;  --bg-secondary: #1a1f3a;  --bg-tertiary: #242a4a;
  --bg-card:      rgba(26, 31, 58, 0.85);
  --bg-glass:     rgba(26, 31, 58, 0.60);

  /* Text ramp */
  --text-primary: #f1f5f9; --text-secondary: #cbd5e1; --text-tertiary: #94a3b8; --text-muted: #64748b;

  /* Accents (two) */
  --accent-primary: #00d4ff; --accent-secondary: #7b61ff;
  --accent-primary-dim: rgba(0, 212, 255, 0.15); --accent-secondary-dim: rgba(123, 97, 255, 0.15);

  /* Semantic */
  --color-success: #10b981; --color-warning: #f59e0b; --color-error: #ef4444;

  /* Glass surface */
  --glass-bg: rgba(26, 31, 58, 0.70); --glass-border: rgba(255, 255, 255, 0.10);
  --glass-border-hover: rgba(255, 255, 255, 0.20); --glass-border-accent: rgba(0, 212, 255, 0.30);

  /* Fonts */
  --font-sans:    'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: 'Space Grotesk', var(--font-sans);
  --font-mono:    'JetBrains Mono', 'SF Mono', monospace;

  /* Radii + transition */
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 24px;
  --transition-glass: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Optional signature mesh background (MAY tier) */
body {
  background: var(--bg-primary);
  background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.03) 1px, transparent 0);
  background-size: 24px 24px;
}
body::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 30px 30px;
}
```

**Actor system example (for role diagrams, REQ-028).** Four canonical actor colours, each paired with a shape per REQ-059:

```css
:root {
  --actor-a: var(--accent-primary);    /* cyan  — e.g. human / manual action  → solid circle */
  --actor-b: var(--accent-secondary);  /* purple — e.g. automated agent        → square        */
  --actor-c: #f43f5e;                  /* rose  — e.g. pipeline / CI           → diamond       */
  --actor-d: var(--color-warning);     /* amber — e.g. system events / labels  → triangle      */
}
.actor-legend { display: flex; flex-wrap: wrap; gap: 14px; padding: 10px 16px;
  background: rgba(10,14,39,0.85); border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm); margin-bottom: 16px; font-size: 0.78rem; }
.actor-legend-item { display: flex; align-items: center; gap: 6px; color: var(--text-secondary); }
.actor-legend-dot  { width: 10px; height: 10px; border: 2px solid; }
```

---

## Appendix D — Example Theme 2: Light Corporate (illustrative only)

> The same Theme Adapter Contract with a light corporate brand. The token NAMES stay; the VALUES flip. `backdrop-filter` is dropped (it muddies panels on white).

```css
:root {
  /* Light backgrounds */
  --bg-primary: #ffffff; --bg-secondary: #f8fafc; --bg-tertiary: #f1f5f9;
  --bg-card: rgba(255, 255, 255, 0.95); --bg-glass: rgba(255, 255, 255, 0.85);

  /* Dark text ramp */
  --text-primary: #0f172a; --text-secondary: #334155; --text-tertiary: #64748b; --text-muted: #94a3b8;

  /* Brand accents — choose two from your palette */
  --accent-primary: #1d4ed8; --accent-secondary: #7c3aed;
  --accent-primary-dim: rgba(29, 78, 216, 0.10); --accent-secondary-dim: rgba(124, 58, 237, 0.10);

  /* Semantic (slightly darker for contrast on light) */
  --color-success: #047857; --color-warning: #b45309; --color-error: #b91c1c;

  /* "Glass" becomes near-opaque cards */
  --glass-bg: rgba(255, 255, 255, 0.95); --glass-border: rgba(15, 23, 42, 0.12);
  --glass-border-hover: rgba(15, 23, 42, 0.22); --glass-border-accent: rgba(29, 78, 216, 0.30);

  /* Fonts — keep the role system, switch families to your brand */
  --font-sans: 'Source Sans 3', system-ui, sans-serif;
  --font-display: 'Source Serif 4', Georgia, serif;
  --font-mono: 'Source Code Pro', monospace;

  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 24px;
  --transition-glass: all 0.3s ease;
}

/* Drop backdrop-filter on light themes */
.glass-panel, .jump-nav { backdrop-filter: none; -webkit-backdrop-filter: none; }
/* Re-tint inline code so it stays readable on white (REQ-014) */
code, .mono { background: rgba(15,23,42,0.06); }
```

---

## Appendix E — Diagram Selection Quick Reference

A one-screen aid for REQ-056 → REQ-058. Read top to bottom: first decide *whether* a picture is warranted, then *which* picture.

**Step 1 — Should this be a diagram at all?**
- Tabular comparison across criteria → `<table>` (REQ-052). Stop.
- A flat list of items or steps with no branching → `<ol>`/`<ul>`. Stop.
- Definitions → `<dl>`. Stop.
- Spatial / temporal / relational / state / quantity structure → continue to Step 2.

**Step 2 — Which archetype?**

| Communicative question | Archetype | viewBox | Notes |
|---|---|---|---|
| Order of events over time | Annotated timeline | wide | Label each milestone in place (REQ-061) |
| Hand-offs between roles | Sequence diagram / swimlane | tall or banded | Actor colours + shapes (REQ-028, REQ-059) |
| Containment / layering | Layered architecture | tall-ish | Outer→inner or top→bottom tiers |
| States and transitions | State machine | square-ish | One start state, labelled edges |
| A branching decision | Flowchart / decision tree | tall or wide | Diamonds for decisions, one path per outcome |
| Gates in a process | Pipeline with gate markers | wide | Mark what each gate enforces (REQ-032) |
| Compare quantities | Bar / column chart | wide | Zero baseline, labelled axes (REQ-058) |
| Part-to-whole across categories | Stacked bar | wide | Avoid pie beyond 2–3 slices |
| Dependencies | Directed graph | square-ish | Watch the density cap (REQ-029) |
| Split of responsibilities | Swimlane | banded | One lane per role |

**Step 3 — Honesty & accessibility gates (apply to every diagram):**
- One question per diagram, declared in `<title>` (REQ-030)
- Within the audience density cap; split into overview + detail if over (REQ-029, REQ-060)
- Colour paired with a second cue everywhere (REQ-059)
- Charts start at zero, label axes, no 3-D/truncation, colourblind-safe (REQ-058)
- Accessibility triple + figure/figcaption + viewBox-only sizing (REQ-022/023/024)

---

## Appendix F — Provenance & adaptation note

This standard distills durable craft and governance patterns observed across production long-form HTML views and their generating pipelines. It is intentionally stripped of any project-specific theme, domain content, repository layout, or organizational identity so it can drop into any project unchanged.

To adopt it: (1) read this document end to end; (2) define your theme via the Theme Adapter Contract (§9), using Appendix C or D as a model, not a copy; (3) generate views from your own content using the rules; (4) validate against §10 and run §11; (5) record disagreements and decisions per §6 rather than smoothing them away.

---

**End of HTML View Quality Standard v2.0.0**
