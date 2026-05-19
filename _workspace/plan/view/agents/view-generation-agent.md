---
name: view-generation-agent
description: Repeatable spec for generating a new visual planning view under `_workspace/plan/view/`. Produces self-contained HTML that opens over file:// with no build step, shares the workspace theme, and stays within the approved folder structure.
version: 1.0
applies_to: _workspace/plan/view/**
---

# View Generation Agent

A reusable process for producing additional visual planning views (e.g. a new
capability surface, a new initiative dashboard, a new stakeholder-facing summary)
without re-deriving conventions or creating folder sprawl.

This agent is **deterministic** in form (where files land, which assets they
share, which interaction patterns are allowed) and **flexible** in content
(diagrams, copy, structure within a page can vary per topic).

---

## Purpose

Generate a new HTML view that:

1. Explains a planning topic visually to a **non-technical** audience.
2. Lives entirely under `_workspace/plan/view/` and reuses the shared theme.
3. Opens directly from disk via `file://` — no server, no build, no package
   manager.
4. Renders identically across browsers and prints cleanly.

If your task does not match these criteria, do not use this agent — write
markdown or a one-off tool instead.

---

## Scope

**In scope.** New `.html` views under `_workspace/plan/view/`, additions to the
shared `theme.css` (only if the addition is reusable across views), small
helpers in `view-common.js` (only if reusable).

**Out of scope.** Editing files under `scripts/podcast/**`, `scripts/memoir/**`,
`content/**`, `docs/**`, or any file outside `_workspace/plan/view/`. If a view
needs to surface data from elsewhere, copy a snapshot into the HTML — never
import or fetch at runtime.

---

## Inputs required

Before generating a view, collect:

| Input               | Why it matters                                          |
|---------------------|---------------------------------------------------------|
| **Topic name**      | Becomes the page title and the slug.                    |
| **Audience**        | Non-technical default; flag if technical reviewers too. |
| **Goal**            | One sentence: what should the reader walk away knowing? |
| **Key data**        | The 3–8 concrete facts the view must present.           |
| **Required diagrams** | List of diagram types needed (mind-map, flowchart, etc.). |
| **Linked views**    | Other views in this folder this view should link to.    |

If any input is missing, stop and ask. Do not invent content.

---

## Output folder rules

Every generated view lands under:

```
_workspace/plan/view/
├── <slug>.html              ← the new view
├── assets/css/theme.css     ← shared, edit only if reusable
└── assets/js/view-common.js ← shared, edit only if reusable
```

**Forbidden.**

- New CSS or JS files outside `assets/css/` and `assets/js/`.
- Per-view CSS files. Reuse `theme.css`; if your view needs unique styles,
  inline them in a `<style>` block in the `<head>`.
- Any directory other than `assets/` and `agents/` inside `view/`.
- Local vendored libraries unless explicitly approved.

---

## Naming conventions

- Filename: `<kebab-case-topic>.html` (e.g. `quality-system.html`,
  `corpus-progress.html`).
- Page `<title>`: `Topic Name — Brief Subtitle`.
- Section ids: `kebab-case`, unique within a page.
- SVG diagram ids: `<topic-slug>-<diagram-type>` (e.g. `quality-flow`).
- Tab panel ids: `tab-<short-name>`.

---

## Theme requirements

Every view **must**:

1. Link to `assets/css/theme.css` in `<head>`.
2. Use the shared `<header class="site-header">` and `<footer class="site-footer">`
   markup (copy from an existing view).
3. Use `<a class="skip-link" href="#main">` as the first body element.
4. Wrap content in `<main id="main"><div class="container">…</div></main>`.
5. Use semantic CSS classes from the theme — `.card`, `.callout`, `.badge`,
   `.tabs`, `.accordion`, `.diagram`, `.checklist`, `.stat`, `.btn`.
6. Use the `.grid` system rather than custom column layouts.
7. Add per-view styling **only** as a `<style>` block in the head, scoped tightly
   to that page. If a style is needed twice, promote it to `theme.css`.

---

## Diagram requirements

A view **must** include at least two diagrams when its purpose is to explain
something visually. Diagrams must:

1. Be **inline SVG** — no `<img>` references to external images.
2. Use the `.diagram` container with a `.diagram-title` and a `.caption`.
3. Use CSS classes (`node-bg`, `node-label`, `edge`, `arrowhead`) so dark/light
   modes work automatically.
4. Include `role="img"` and an `aria-label` summarizing the content.
5. Be drawable in a maximum of two `viewBox` widths — `1100` or `1140` — for
   visual consistency.
6. Avoid runtime layout dependencies. Coordinates are static.

D3.js is **permitted** only with a graceful fallback. If you load D3 from a CDN,
your `<noscript>` and the static SVG underneath must convey the same data.
Default to plain inline SVG.

---

## Accessibility requirements

Each view must:

1. Provide a skip-link as the first focusable element.
2. Use a logical heading hierarchy — exactly one `<h1>`, then `<h2>`/`<h3>`.
3. Mark every interactive control with the right ARIA role and state
   (`role="tab"`, `aria-selected`, `aria-controls`, `aria-expanded`).
4. Ensure all text meets WCAG AA contrast at the theme defaults (the shared
   palette already does — don't override colors per view).
5. Use `<details>`/`<summary>` for accordions (keyboard-accessible by default).
6. Include `alt`-equivalent text for every SVG via `aria-label` or a sibling
   `.caption`.
7. Work with keyboard alone — Tab to controls, Enter/Space to activate, arrow
   keys for tab groups.
8. Render legibly with media queries for both dark and light schemes.
9. Print cleanly — the theme already handles this; don't add print-hostile
   overrides.
10. Be responsive down to 720px width without horizontal scroll (except
    diagrams, which may scroll inside their container).

---

## Interaction requirements

**Allowed**

- Tabs (`role="tablist"`, `role="tab"`, `role="tabpanel"`).
- Accordions (`<details>`/`<summary>`).
- Expand/collapse-all buttons (`data-details-toggle="open|close"`).
- Internal anchors.
- Hover states.
- Diagram toggles (e.g. show/hide a layer) implemented as accordions or tabs.

**Not allowed**

- Navigating away from the view to a non-local URL for required content.
- External CSS or JS fetches (CDN OK only for a non-essential progressive
  enhancement with a working fallback).
- Modal dialogs that trap focus without a tested escape.
- Custom font hosting — use system fonts via the theme's `--font-sans`.
- Animations that don't respect `prefers-reduced-motion`.

---

## File containment rules

Before you write a file, confirm its destination:

| File                                       | Must live at                                  |
|--------------------------------------------|-----------------------------------------------|
| New view HTML                              | `_workspace/plan/view/<slug>.html`            |
| Shared theme update (only if reusable)     | `_workspace/plan/view/assets/css/theme.css`   |
| Shared JS update (only if reusable)        | `_workspace/plan/view/assets/js/view-common.js` |
| Agent spec update                          | `_workspace/plan/view/agents/view-generation-agent.md` (this file) |

Any other location is a violation.

---

## Acceptance criteria

A generated view is acceptable when:

- [ ] The view opens cleanly via `file://` in Safari, Chrome, and Firefox.
- [ ] All navigation links use relative paths and resolve.
- [ ] The view shares the theme — no duplicated colors, type, or spacing tokens.
- [ ] At least two inline-SVG diagrams are present (if the view is explanatory).
- [ ] All interactive controls are keyboard-accessible and ARIA-correct.
- [ ] The page renders without horizontal scroll at 720px viewport width.
- [ ] Print preview is legible (use the theme's `@media print`).
- [ ] No external runtime dependencies are required to display the content.
- [ ] Folder structure is unchanged (no new top-level dirs under `view/`).
- [ ] The header nav lists every sibling view in the same order.
- [ ] The `<title>` and meta description match the topic.
- [ ] Captions explain every diagram in one or two sentences.

A generated view is **not** acceptable if:

- It requires a local server, build step, or package install.
- It scatters CSS/JS outside the approved folder.
- Diagrams are purely decorative — they must convey the page's information.
- Any view link points to an external resource for required content.
- The header navigation drifts from the other views in the folder.

---

## Repeatable execution checklist

Follow this order when producing a new view:

1. **Confirm the inputs.** Title, audience, goal, key data, required diagrams,
   linked views. Stop and ask if any are missing.
2. **Confirm the slug** — kebab-case, unique under `view/`.
3. **Copy the page skeleton** from an existing view (header, footer, main
   wrapper, skip-link, script include).
4. **Update the nav** in the new file to include every sibling view in
   the same order; set `aria-current="page"` for the active one.
5. **Lay out the page** — hero, then sections in priority order.
6. **Draft the diagrams.** Pick types from the catalog below. Inline as SVG with
   the theme's CSS classes. Add captions.
7. **Cross-check accessibility.** Skip-link present? Heading hierarchy logical?
   Tabs and accordions reachable by keyboard? `aria-label`s on diagrams?
8. **Test rendering.** Open via `file://`. Resize to ~720px width. Toggle dark
   and light. Print preview.
9. **Update the landing page.** Add a new nav card to `index.html` linking to
   the new view. Add a nav-bar link in every sibling view's `.nav-primary`.
10. **Self-audit against acceptance criteria** above. Fix anything that fails.

---

## Diagram catalog

Pick at least two when authoring a new explanatory view:

| Type                  | When to use                                  |
|-----------------------|----------------------------------------------|
| Mind map              | Show domain decomposition or scope.          |
| End-to-end flowchart  | Show a linear pipeline.                      |
| Data flow             | Show sources → working state → outputs.      |
| Lifecycle             | Show a cyclic process with steps.            |
| Stacked bar           | Show grouped counts (phases per wave, etc.). |
| Risk/quality matrix   | Show likelihood × impact with controls.      |
| Maturity timeline     | Show capability progression across waves.    |
| HITL flow             | Show where humans review.                    |
| Control matrix        | Two-column "fixed vs steered" — what we own vs. what's out of our hands. |

If you need a new diagram type, propose adding it to this catalog rather than
inventing a one-off.

---

## What to do when something is unclear

Two rules:

1. **If the input is missing, ask.** Do not fabricate data, diagrams, or claims.
2. **If a convention is missing, copy from the most-recently-edited sibling
   view** — that's the reference implementation until this spec is updated.

Edits to this spec are themselves under change control: append a "Revision log"
entry below with the date and a one-line rationale.

---

## Revision log

- **2026-05-19** — Initial spec. Captures the structure introduced when
  `podcast-capabilities.html`, `acceptance-criteria.html`, and a redesigned
  `index.html` were authored alongside `theme.css` and `view-common.js`.
