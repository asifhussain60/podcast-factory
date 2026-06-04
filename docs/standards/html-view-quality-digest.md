---
name: html-view-quality-digest
title: "HTML View Quality — MUST digest (one screen)"
purpose: >
  The always-in-context short card. Lists ONLY the MUST-tier rules, one line each,
  cited by REQ-NNN. This is what the prompt hook and the skill reference for cheap
  recall; read the full standard (docs/standards/html-view-quality.md) ONLY when you
  need a rule's exact wording, examples, or its SHOULD/MAY siblings.
source_of_truth: "docs/standards/html-view-quality.md"
applies_to: "Podcast Factory Astro Site (plan-dashboard/)"
---

# HTML View Quality — MUST digest

> Hard rules only. Full text, SHOULDs, MAYs, examples, and theme appendices live in
> [the standard](html-view-quality.md). Cite findings by `REQ-NNN`, never by section.
> **Repo conflict rule:** content + SVG lean Cortex; delivery mechanics follow the repo
> DoD (external CSS/JS only, ZERO inline styling); never change the colour theme.

## Repo DoD (hard — overrides Cortex's "inline JS/CSS" guidance)
- **D-DoD** ZERO inline styling: no `style=` attrs, no inline `<style>`/`<script>` bodies in `.astro`/`.tsx`. All CSS/JS external.
- **D-THEME** Never change `theme.css` colour values; add Cortex-token aliases only (Pattern B).
- **D-DIAGRAM** Diagrams vertical (top→bottom), uncapped (no height clamp on SVG containers), varied (no two adjacent views lead with the same archetype). Mermaid → build-time inline SVG, never client-rendered.

## Page architecture
- **REQ-001** Shell order: skip-link → header (not sticky) → sticky jump-nav → main → footer → back-to-top. (Shared Astro layout owns it.)
- **REQ-002** No height clamp on html/body/main/.container/section. Only `.diagram-container`, `.table-container`, `<pre>` may scroll.
- **REQ-003** Container `width:90%; max-width:1400px; margin:0 auto`; no `max-width` on body prose.
- **REQ-004** Every `<section>` is a `<section>` with unique kebab `id` (`s01-…`) + two-digit number marker in its `<h2>`.
- **REQ-005** `scroll-behavior:smooth`; `scroll-margin-top` ≥ sticky-nav height + 8px.
- **REQ-007** Opens via `file://` — no fetch/XHR/dynamic import/service worker. *(On this site: external JS modules via Astro instead — DoD wins over "inline JS".)*
- **REQ-009** One view = one purpose.

## Typography
- **REQ-010** Reading text ≥ 1.2rem on all prose elements (p, li, td, th, dd, dt, blockquote, figcaption, label, callouts).
- **REQ-011** Exactly one `<h1>`; never skip heading levels.
- **REQ-012** Three font roles only (`--font-sans/--font-display/--font-mono`); no decorative fonts in body.
- **REQ-013** Page `<h1>` uses the two-stop gradient text treatment (single-accent → `--text-primary`→`--accent-primary`).
- **REQ-014** Inline `<code>`/`.mono`: mono font, tinted bg, accent foreground, small radius.
- **REQ-015** Lists: `padding-inline-start ≥ 1.75rem`, `list-style-position: outside`; real `<ol>` numbering.
- **REQ-052** Wide tables wrapped in scrollable `.table-container` (`role="region"`, `tabindex="0"`).

## Colour & surface
- **REQ-017** All Theme-Adapter tokens resolve in `:root` (via aliases onto `--c-*`).
- **REQ-018** At most two accents (the four semantic colours counted separately).

## SVG craft & selection
- **REQ-056** Right form first: table for tabular, `<ol>/<ul>` for flat lists, `<dl>` for definitions — never drawn in SVG.
- **REQ-058** Honest charts: zero baseline, labelled axes, no 3-D/truncation/dual-axis, colourblind-safe.
- **REQ-021** Inline `<svg>` only — no `<img src=*.svg>`/`<object>`/`<embed>`.
- **REQ-022** Accessibility triple: `role="img"` + `aria-labelledby` + child `<title>` and `<desc>`.
- **REQ-023** Wrap every SVG in `<figure class="diagram-container">` + `<figcaption>` (insight, not a repeat of `<desc>`).
- **REQ-024** `viewBox` only; no `width`/`height` attrs on `<svg>`.
- **REQ-026** SVG `<text>` uses the three theme font families.
- **REQ-027** SVG colours map to theme tokens / semantic colours (hex must equal the token value).
- **REQ-029** Density cap by audience tier (L1=5 nodes/8 edges … L4=20/36); over cap → split (REQ-060).
- **REQ-030** One SVG answers exactly one question, declared in its `<title>`.
- **REQ-059** Colour is never the sole carrier — pair with label/shape/icon/pattern.
- **REQ-062** SVG text is live `<text>`/`<tspan>`, never outlined paths.

## Content & tone
- **REQ-035** Coffee test: first viewport ≤ 200 words, zero unexplained jargon, what + why before how.
- **REQ-036** Conversational voice ("you"/"we"), not third-person passive.
- **REQ-037** Gloss each domain term in plain English at first use, then use it directly.
- **REQ-038** Numbered section markers imply reading order; don't number a non-sequential index.

## Content integrity & governance
- **REQ-063** Separate fact / interpretation / recommendation — visually and grammatically.
- **REQ-064** Decisions as full records: context, options, decision, rationale, trade-offs.
- **REQ-065** Surface disagreement / minority views, attributed and steel-manned — never flatten.
- **REQ-067** Conflicting sources: state the precedence rule AND show the superseded value.
- **REQ-070** Every cited source carries a date + provenance (mark `undated` if so).

## Navigation & chrome
- **REQ-044** Sticky jump nav with active-section highlight (IntersectionObserver).
- **REQ-045** Back-to-top button, fades in after one viewport of scroll.

## Accessibility & standards
- **REQ-048** WCAG 2.1 AA: contrast ≥ 4.5:1 (large ≥ 3:1); visible focus; keyboard-reachable.
- **REQ-049** Semantic landmarks + correct heading order; `<table>` only for data; `<button>`/`<a>` not `<div onclick>`.
- **REQ-051** Responsive at 360 / 768 / 1200px.
- **REQ-071** Skip-to-content link, focus-revealed.
- **REQ-072** `<html lang>` set.

---

*Conformance: a view ships at Level 1 (all MUSTs above) minimum; gate through the
`html-view-challenger` agent. The lint gate (`npm run lint:views`) enforces the
mechanical MUSTs deterministically — see the full standard §11.*
