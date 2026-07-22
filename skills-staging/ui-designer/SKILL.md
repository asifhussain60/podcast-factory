---
name: ui-designer
description: >
  Visual-design system authority for the Podcast Factory Astro Site (directory
  plan-dashboard/). Load this WHENEVER you create or restyle any page, view,
  component, card, stat block, or diagram, or make any typographic, spacing,
  color, or visual-balance decision on the site. It locks the type system
  (Fraunces display serif + Inter body/UI sans, self-hosted, token-driven), the
  editorial-modern component language (restrained cards, quiet accents, generous
  whitespace), and the visual-balance rules — WITHOUT ever changing the locked
  --c-* color palette. It is the aesthetic layer that sits ON TOP of the Cortex
  HTML View Quality Standard (skills-staging/html-view-quality): Cortex governs
  delivery mechanics and accessibility; this skill governs taste. Blend both.
  Invoke for: 'design this page', 'make it look good', 'ui designer', 'restyle',
  'redesign the blocks', 'pick fonts', 'improve the visual design', 'high quality
  design', or any surface work under plan-dashboard/.
---

# UI Designer — Podcast Factory Astro Site design system

This skill is the single source of taste for the site. It exists so every
surface reads as ONE considered product — editorial-modern, in the spirit of
Stripe Press and MIT Press: restrained warm palette, confident serif display,
clean sans body, strong hierarchy, generous whitespace, minimal ornament.

It does **not** replace the Cortex HTML View Quality Standard
(`docs/standards/html-view-quality.md`, enforced by the `html-view-challenger`
agent and `npm run lint:views`). Cortex is the floor: external CSS/JS only, zero
inline styling, accessibility triple on SVGs, uncapped vertical diagrams, reading
floor, etc. **This skill is the ceiling: it decides how the conformant thing
actually looks.** When they touch the same pixel, satisfy both — content + SVG
lean Cortex, delivery mechanics follow the styling DoD, and the aesthetic
decisions below win on look.

---

## 0. The two hard locks (never violate silently)

1. **The color palette is LOCKED.** Use ONLY the existing `--c-*` tokens defined
   in `src/styles/theme-tokens.css`. Never introduce a new hex value, never
   change an existing one, never hardcode a color in a page or component. Color
   comes from tokens; the warm parchment / deep-ink / green-gold-blue accent
   system stays byte-identical. (Changing the palette is an explicit,
   Asif-approved override — not a design liberty.)

2. **Zero inline styling.** No `style=` attributes, no inline `<style>` bodies,
   no inline `<script>` bodies. All styling lives in `src/styles/*.css`. This is
   also a Cortex MUST — it is repeated here because it is the most common way a
   good design decays.

---

## 1. Type system (LOCKED 2026-07-18)

Two typefaces, three roles, all self-hosted under `public/fonts/`, all driven by
tokens in `theme-tokens.css`. Never name a font family directly in a page or
component — always go through a `--font-*` token.

| Role | Token | Family | Use |
|---|---|---|---|
| Display | `--font-display` | **Fraunces** (variable, wght) | Page/hero titles, section `<h2>` numerals, big stat numerals, pull quotes. Expressive, literary, warm. |
| Body / UI | `--font-body`, `--font-sans`, `--font-ui` | **Inter** (variable, wght) | All body copy, labels, chips, nav, tables, buttons. Clean, neutral, legible. |
| Mono | `--font-mono` | system mono stack | Code, CLI, keys. Unchanged. |
| Arabic / Urdu | `--font-urdu`, Amiri | as-is | Scripture faces. Unchanged. |

**Why Fraunces + Inter.** Fraunces carries the "centuries of scholarship" voice —
a modern serif with optical warmth and character that a system serif can't fake.
Inter is the quietest, most legible modern UI sans; it never competes with the
display face. The contrast between an expressive serif and a neutral sans is the
whole editorial-modern move.

**Display-face rules (Fraunces).**
- Use for `<h1>`/hero, section headings, big numerals — NOT for body or long runs.
- Weight 340–460 for large display (Fraunces gets heavy fast); 560–640 for
  smaller headings/labels-as-display.
- Tighten tracking on large sizes: `letter-spacing: -0.015em` at h1/hero,
  `-0.01em` at h2. Never track display OUT.
- Italic Fraunces (self-hosted italic file) is the accent for a single emphasized
  word in a title (e.g. an italicized noun) — use sparingly, one per title.
- `line-height` tight on display: `1.05–1.15`.

**Body-face rules (Inter).**
- Body `--fs-base` (1.2rem floor) at `--lh-base` (1.65), weight 400.
- Labels/eyebrows/chips: uppercase, `letter-spacing: 0.06–0.08em`, weight 600–700,
  `--fs-label`/`--fs-sm`. Uppercase tracking belongs to the SANS, never the serif.
- Use `font-variant-numeric: tabular-nums` for any aligned numbers.

**Loading.** Global `@font-face` lives in `src/styles/fonts.css`, imported first
in `theme.css`. Variable woff2, `font-display: swap`. Do not add Google Fonts
`<link>` tags — self-host (matches the existing `public/fonts/` convention, keeps
the site self-contained and CSP-safe).

---

## 2. Color usage (palette unchanged; how you APPLY it is the design)

The palette is locked; taste is in restraint. The editorial-modern signature is
**color as accent, not as fill.**

- **Surfaces** are warm neutrals: `--c-bg` (page), `--c-bg-card` / `--c-bg-elev`
  (cards). The accent colors (`--c-green`, `--c-amber`, `--c-planner` blue,
  `--c-accent` terracotta, `--c-gold`) appear as **thin rules, small icon tiles,
  low-alpha tints, single numerals or short labels** — not as saturated
  full-bleed backgrounds behind white text.
- Tint with `color-mix(in oklab, var(--c-x) 10–16%, transparent)` for soft fills;
  keep text at `--c-ink` on tinted surfaces (never white-on-saturated for data).
- One accent per card, chosen for meaning (green = done/source, amber = human
  gate, blue = intelligence, terracotta = decisions). Don't rainbow a grid just
  to fill it.
- Borders: `--c-rule`. Shadows: `--shadow-card` (soft, low). Radius: `--r-md`/
  `--r-lg`. Never a hard drop shadow.

**Anti-pattern (what we are moving away from):** welded strips of saturated
gradient tiles with white text and animated sheen sweeps. That reads as a cheap
admin dashboard. Replace with separated, quiet cards (below).

---

## 3. Component language

### 3a. Stat / metric cards (the replacement for the "ugly blocks")
- **Separated cards** in a grid with a real gap — NOT one welded strip.
- Warm card surface (`--c-bg-card`), `1px --c-rule` border, `--shadow-card`.
- A single quiet accent per card: a **left accent bar** OR a **small tinted icon
  tile** (`color-mix` tint background + accent-colored icon), never a full fill.
- **Numeral in Fraunces display**, `--c-ink`, large, tabular-nums.
- Label in Inter, uppercase, muted (`--c-ink-muted`), tracked.
- Hover: a 1px border-color lift toward the accent + 1–2px rise; no sheen.
- Motion: at most a subtle staggered fade-in; must be wrapped by
  `@media (prefers-reduced-motion: reduce)` to disable.

### 3b. Content cards
- `--c-bg-card`, `--c-rule` border, `--r-lg`, `--shadow-card`, generous padding
  (`--sp-5`). Bold Inter lead-in or short Fraunces sub-head; muted body.
- Never more than one accent color inside a single card.

### 3c. Diagrams (mind maps, service maps, timelines)
- Inline SVG, `viewBox` only (no width/height attrs), vertical + uncapped
  (Cortex D-DIAGRAM). Accessibility triple: `role="img"` +
  `aria-labelledby` → `<title>`+`<desc>`, wrapped in `<figure>`+`<figcaption>`.
- Node fills = soft palette tints; node text = `--c-ink`; connectors = `--c-rule`
  or a muted accent. Labels in Inter; a diagram TITLE may use Fraunces.
- Legibility floor: no text below ~13px effective; group related nodes with
  whitespace, not boxes-in-boxes.
- Prefer the RIGHT form: a timeline/sequence is often clearer as a numbered
  vertical stepper (HTML + CSS) than as an SVG. Use SVG when spatial relationships
  carry meaning (a mind map, a service topology); use structured HTML (ol/dl) when
  the meaning is sequential.

### 3d. Rhythm & balance
- Vertical rhythm on the `--sp-*` scale; sections breathe (`--sp-6/7` between
  major sections). Whitespace is the primary design tool.
- Max line length for body ~68ch. Center long-form; left-align data.
- One idea per row. Resist filling every pixel.

---

## 4. Definition of done (gate every surface)

1. Palette unchanged (no new/edited hex; tokens only). **Zero inline styling.**
2. Type roles correct (Fraunces display, Inter body/UI) via tokens.
3. `npm run lint:views` clean; `astro check` clean.
4. `html-view-challenger` — static Cortex conformance (blocking MUSTs zero).
5. `site-health-sentinel` / `npm run smoke` — runtime + visual QA: boots the
   site, sweeps every route for console errors, then judges screenshots at
   desktop (~1440px) and mobile (~390px) in light AND dark for clipping,
   overflow, contrast, off-theme color, broken responsive layout. Converge; then
   delete throwaway screenshots.
6. Redesigns of EXISTING pages are shown to Asif one page at a time before they
   are called done (per the Cortex per-view rule). New pages ship with screenshot
   proof.
