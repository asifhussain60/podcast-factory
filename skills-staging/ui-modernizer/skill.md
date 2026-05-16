---
name: ui-modernizer
description: "UI modernization skill for the journal app's ui-modernization branch. Invoke when the user says 'ui-modernizer', '/ui-modernizer', '@ui-modernizer', 'modernize ui', 'run ui phases', or 'continue ui modernization'. Executes the four-phase modernization plan: (1) Design System hygiene — retire --muted token, enforce opacity-on-text rule; (2) Architecture — split monolithic CSS; (3) Interactions — upgrade accordions to grid-template-rows; (4) Views — visual improvements. ALWAYS invokes ui-reviewer agent after each phase. Read-only by default — requires explicit 'apply' to make edits."
---

# ui-modernizer — UI Modernization Skill

Executes the four-phase modernization plan on the `ui-modernization` branch of the journal app.
After every phase, the `ui-reviewer` agent is invoked to audit the diff.

---

## SECTION 0 — CORTEX Compliance (read first)

This skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`).
Compliance tier: **SILVER (target)**. Per-skill compliance contract: [`cortex-compliance.md`](cortex-compliance.md).
Shared SECTION 0 contract: [`reference/skill-bootstrap.md`](../../reference/skill-bootstrap.md).

Before any action, read in order:
1. `reference/cortex-challenger-framework.md`
2. `reference/skill-bootstrap.md`
3. `skills-staging/ui-modernizer/cortex-compliance.md`
4. This file.

**Severity is P0–P3.** Legacy labels (MAJOR) have been mapped inline. The `cortex-compliance.md` mapping table is authoritative when in doubt.

**Run report:** `_workspace/challenger-reports/ui-modernizer-phase<N>-<run_id>.yml` per framework §3 schema.

---

## Decision log — locked decisions (do NOT override without updating framework.md first)

| Decision | Status | Reason |
|---|---|---|
| Shadow DOM for React islands | REJECTED | Global theme tokens (`var(--*)`) don't pierce shadow boundaries; would require explicit forwarding that undermines the token system |
| `:root`-free component CSS | LOCKED | Phase 2 design-system canon — theme tokens via `var()` only |
| `--muted` = alias for `--text-secondary` | CONFIRMED | Identical hex in all 9 themes — safe to retire |

---

## Phase 1 — Design System Hygiene

### 1a. Retire `--muted` token
- Replace every `var(--muted)` → `var(--text-secondary)` in `site/css/itinerary.css` (25 occurrences as of 2026-04-18).
- Remove `--muted:` declarations from all 9 theme files under `site/css/themes/`.
- Run `cd server && npm run validate-themes` — must pass.
- Rationale: `--muted` == `--text-secondary` exactly across all 9 themes (confirmed). The alias adds confusion without value.

### 1b. Opacity-on-text enforcement
- The rule: **never apply `opacity < 1` to an element whose primary color is a text token.**
  - ✗ `color: var(--text-secondary); opacity: 0.6` — the opacity halves perceived contrast that was carefully tuned.
  - ✓ `color: var(--text-muted)` — use a lower token instead.
- Add **check 9** to `server/scripts/validate-theme-parity.mjs`: scan component CSS for rule-sets that declare both a text-token `color` and `opacity < 1` in the same selector.
- Severity: **P1** (not P0) — some opacity usages on mixed elements are legitimate (loading skeletons, animations).

---

## Phase 2 — Architecture: CSS Split

Split `site/css/app.css` (3,469 lines) by extracting the chapter reader into a dedicated file.

### 2a. Extract `chapter-reader.css`
- **Source range — anchors, not line numbers:** extract from the comment `/* === BEGIN: Chapter reader === */` to `/* === END: Chapter reader === */`. If those anchors are not present in `app.css`, Stage 0 of this phase inserts them at semantically correct boundaries (detected via banner comments / h2-style section markers / rule grouping) and commits the anchor insertion separately, then extraction operates on anchors. **Never extract by raw line range — line numbers drift silently on hand-edits.** Historical range (for reference only): approximately lines 698–2163 of pre-anchor `app.css`.
- New file: `site/css/chapter-reader.css`.
- Update `site/index.html`: add `<link rel="stylesheet" href="css/chapter-reader.css">` after the `app.css` link.
- Update `server/scripts/validate-theme-parity.mjs` SCOPED_EXEMPT list only if needed (chapter reader contains no intentional hardcoded hex).
- No itinerary pages link `app.css` — no other HTML changes required.
- Run `npm run validate-themes` after split.

### 2b. Do NOT split `itinerary.css`
- Only one consumer HTML exists (`site/itineraries/itinerary.html` — generic, slug-driven template).
- The sections are already clearly delimited by banner comments.
- Risk/return doesn't justify split.

---

## Phase 3 — Interactions: Grid-Interpolation Accordion

Upgrade the **day-body accordion** in the itinerary from the `max-height: 3400px` approach to `grid-template-rows: 0fr → 1fr`.

### Why
- `max-height: 3400px` easing is asymmetric (fast open, slow close relative to content height).
- Grid-template-rows interpolation gives smooth, content-height-relative animation.
- Pattern is already established in `.event-body` (itinerary.css line 1027) and budget categories (line 1970).

### How
1. Wrap `.day-body` children in a `<div class="day-body-inner">` in both:
   - The JS renderer in `site/itineraries/itinerary.html` (now fully data-driven, no static day blocks)
2. Update `.day-body` CSS: remove `max-height` transitions, add `grid-template-rows: 0fr → 1fr`.
3. Add `.day-body-inner` rules: `min-height: 0; overflow: hidden; display: grid; grid-template-columns: 1fr; gap: 1.5rem;`.
4. Move padding-top from `.day-card.open .day-body` to `.day-card.open .day-body-inner`.

### Invariants to preserve
- `padding: 0 1.5rem` on `.day-body` (horizontal) stays.
- `padding: 1rem 1.5rem 1.5rem` open state → `padding-top: 1rem; padding-bottom: 1.5rem` on `.day-body-inner`.
- `.day-card.no-anim .day-body { transition: none !important; }` must extend to `.day-card.no-anim .day-body .day-body-inner { transition: none !important; }`.
- The Leaflet map (`#mapN`) must re-initialize when the day opens (already handled by `toggleCard()` JS).

### Established pattern
The inner-wrapper approach is the project standard for `grid-template-rows: 0fr/1fr` accordions with multiple children:
```css
.outer { display:grid; grid-template-rows:0fr; overflow:hidden; }
.outer-inner { min-height:0; overflow:hidden; }
.open .outer { grid-template-rows:1fr; }
```
All accordions in the repo should use this pattern (`.event-body`/`.event-body-inner`, `.day-body`/`.day-body-inner`).

---

## Phase 4 — Views: Visual Modernization

### 4a. Event cards — accent-driven chroma
- Already done 2026-04-17/18: borders, hover bloom, and expanded state use `var(--accent-a*)` tokens.
- Audit for any remaining hardcoded rgba in `.event-card` rules.

### 4b. Hero section — particle refinement
- Ensure `.particle` animations use `var(--accent)` / `var(--rose)` rather than inline hex.

### 4c. Day-header weather tile — severity glow with tokens
- `.is-weather-warn` and `.is-weather-alert` glows should use `color-mix(in srgb, var(--warning) N%, transparent)` not hardcoded orange/red rgba.

### 4d. Budget panel — token audit
- `.budget-stat`, `.budget-category`, `.budget-txn-row` — check for hardcoded text colors.

---

## Token rules for chapter-reader.css

`chapter-reader.css` is an **enforced component file** — it is scanned by the validator for hex leaks and palette rgba leaks.

Exempt sections:
- `[data-reading-theme="sepia"]` and `[data-reading-theme="light"]` selector blocks — hardcoded per-reading-theme colors are intentional and exempt.
- `.dark-dot`, `.sepia-dot`, `.light-dot` swatch classes — literal brand color swatches, intentional.
- `rgba(0,0,0,N)` and `rgba(255,255,255,N)` in box-shadow and background-gradient endpoints — universal, exempt.

All other rgba/hex in chapter-reader.css must use tokens:
- White-alpha borders/backgrounds → `var(--white-N)` (see theme.css for available tokens: `--white-04` through `--white-90`)
- Error-color derivatives → `color-mix(in srgb, var(--error) N%, transparent)`
- Dark background gradients for floating pills → `color-mix(in srgb, var(--bg-secondary) N%, transparent)`

---

## Spacing & Breathing Room Rules (mandatory for all views)

All components MUST maintain minimum spacing thresholds to ensure visual breathing room. These are non-negotiable minimums — never go below these values.

### Spacing Scale

| Context | Minimum | Preferred | Notes |
|---|---|---|---|
| **Section-to-section gap** (`.itn-container`, `.grid-cards`) | 2rem | 2.5rem | Gap between sibling sections |
| **Section internal padding** (`.itn-section`) | 2rem | 2.25rem | Internal content padding |
| **Card internal padding** (`.event-card`, `.stat-card`, `.card`) | .85rem | 1rem+ | Cards never cramped |
| **Card gap in grid** (`.timeline`, `.day-body-inner`) | 1.25rem | 1.5rem | Between cards in a list |
| **Section header bottom margin** (`.section-header`) | 1.5rem | 1.75rem | Space below "The Itinerary" etc. |
| **Hero bottom margin** (`.hero`) | 2rem | 2.5rem | Between hero and next section |
| **Widget containers** (`.ft-root`, `.budget-panel`) | 1.25rem padding | 1.5rem | Self-contained widgets |
| **Day card open body** (`.day-body-inner`) | 1rem top, 1.25rem bottom | 1.25rem top, 1.75rem bottom | First/last event breathing room |
| **Dashboard grid gap** (`.grid-cards`) | 1.5rem | 1.75rem | Between dashboard cards |
| **Log module top padding** | 24px | 28px | Clears nav comfortably |

### Responsive Scaling

At mobile breakpoints (≤680px, ≤420px), spacing reduces proportionally but never drops below 60% of the desktop minimum. For example:
- Section padding: 2.25rem → 1.5rem (680px) → 1.15rem (420px)
- Card padding: 1rem → .85rem (680px) → .65rem (420px)
- Grid gap: 1.5rem → 1.25rem (680px) → 1rem (420px)

### Zero-Margin Anti-Patterns (NEVER do these)

- `margin: 0` on a section boundary — always provide at least 1rem separation
- `padding: 0` on a card-level container — cards always need internal padding
- `margin-top: -Nrem` that collapses the gap between two sections below 1rem
- `gap: 0` on any grid that contains user-visible content items

### New Component Checklist

When creating a new component or widget:
1. Define `padding` on the component root (minimum 1rem)
2. Define `margin` for spacing from siblings (minimum 1rem)
3. If it's a grid/list container, set `gap` (minimum 1rem)
4. Test at 1440px, 860px, 680px, and 420px breakpoints
5. Verify no content hugs the edges of its parent container

---

## Validation gate

After all phases, run:
```
cd /Users/asifhussain/PROJECTS/journal/server && npm run validate-themes
```
All 9 checks must pass before invoking `ui-reviewer`.

## Post-phase protocol

After each phase commit:
1. Run `npm run validate-themes` — must be clean.
2. Invoke `ui-reviewer` agent — address all **P0** and **P1** items before next phase.
3. Commit with message format: `style(ui): Phase N — <one-line description>`.

## Determinism Contract

Per the shared bootstrap (`reference/skill-bootstrap.md` §4):

- **Findings sort order:** severity (P0 first) → phase number → file path (lexicographic POSIX) → line number → check ID.
- **Tiebreakers for anchored extraction:** when multiple candidate boundaries are detected, the disambiguator is, in order: (1) banner-comment match (`/* === ... === */` strongest), (2) h2-style block comment (`/* ====... */`), (3) blank-line-separated rule grouping with section name in adjacent comment. The first deterministic match wins. If none decisive, downgrade to a Challenge Gate (alternatives surfaced to operator).
- **Run identifiers:** `run_id` = SHA-256(skill_name + phase_number + ISO-8601 UTC timestamp + input_hash), truncated to 16 hex chars. `input_hash` = SHA-256 of newline-normalized concatenation of all in-scope files sorted by lexicographic POSIX path.
- **Locale / clock:** dates ISO-8601 UTC in report.
- **No line-number-based edits** (deterministic enough is not enough — they drift on hand-edits). Use anchors or AST-style boundaries.

## DoR & Convergence

- **DoR:** 100% required before `--apply` per `cortex-compliance.md`. On failure: `_workspace/ui-modernizer-dor-incomplete-<run_id>.md` + halt.
- **Convergence:** max 3 cycles per phase. On exceed: halt + `_workspace/ui-modernizer-convergence-failed-<phase>-<run_id>.md`.
- **Sweep:** all 9 themes in scope or none; all enforced-scope CSS in scope or none; phase rollback applies atomically on failure.

## Run report

After every phase, write `_workspace/challenger-reports/ui-modernizer-phase<N>-<run_id>.yml` per framework §3 schema.
