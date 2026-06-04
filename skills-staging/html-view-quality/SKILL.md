---
name: html-view-quality
description: >
  The Cortex HTML View Quality Standard, adapted for the Podcast Factory Astro Site
  (directory plan-dashboard/). MUST be applied to ANY work that builds or edits an
  HTML view, Astro page, component, or diagram on this site — never bypass, never
  drift. Encodes the 74 REQ-NNN craft + governance rules with Astro delivery deltas,
  the theme-adapter bridge onto the existing --c-* tokens (colour theme never
  changes), and the conformance workflow gated by the html-view-challenger agent.
  TRIGGER: "build a view", "build/edit a page", "add/edit a diagram", "html", or
  anything touching plan-dashboard/. Canonical source of the full rule text:
  docs/standards/html-view-quality.md.
---

# HTML View Quality — Podcast Factory Astro Site

This skill is the operational contract for building and editing views on the
**Podcast Factory Astro Site** (directory `plan-dashboard/`). It adapts the **Cortex
HTML View Quality Standard v2.0.0** (the full 74 `REQ-NNN` rules live in
`docs/standards/html-view-quality.md` — read it for any
rule's exact text; cite findings by `REQ-NNN`, never by section).

> **Hard precedence.** This skill is mandatory and implicit. If you are building or
> editing any HTML view, page, component, or diagram on this site, these rules apply
> whether or not anyone restated them. Do not bypass and do not drift. The
> `html-view-challenger` agent is the output gate — a view is not "done" until it
> passes at its declared conformance level.

## 0. Conflict-resolution rule (locked 2026-05-29)

When the Cortex standard and this repo's styling DoD collide, **blend both; content
and SVG lean Cortex; delivery mechanics follow the repo DoD.** Concretely:

- **Delivery mechanics → repo DoD wins.** External CSS + external JS only. ZERO
  inline styling: no `style="..."` attributes, no inline `<style>` blocks, no inline
  `<script>` bodies in `.astro`/`.tsx`. (This OVERRIDES Cortex REQ-007's "inline JS"
  and the "re-assert the floor in an inline `<style>`" guidance — those assume a
  standalone `file://` document; we ship an Astro site.)
- **Content + SVG + typography intent → Cortex wins.** Diagram craft/selection
  (REQ-021–034, 056–062), the audience gradient + density caps (REQ-029, 035, 040),
  the reading floor + font roles (REQ-010–016), and the content-integrity rules
  (REQ-063–070) are followed as written.
- **Theme → never change it.** Map Cortex token names onto the EXISTING theme via the
  adapter in §2; never alter an existing colour value.

## 1. Astro delivery deltas (how Cortex maps onto this site)

| Cortex assumes | On this site, do instead |
|---|---|
| Standalone `file://` HTML, inline `<script>` | External JS modules referenced via Astro; client logic in external `.ts`/`.js`, never inline bodies |
| Inline `<style>` / re-asserted floor inline | All CSS in external stylesheets under `plan-dashboard/src/styles/`; never inline |
| Per-page document shell (skip-link→header→sticky nav→main→footer→back-to-top) | A shared Astro **layout** owns the shell (today: `Base.astro`); views fill `<main>` with numbered `<section>`s |
| Fresh `:root` token block per view | One shared `theme.css`; Cortex names mapped to existing `--c-*` via the adapter (§2) |
| Hand-authored bespoke SVG only | Bespoke React/SVG components (system/swimlane/trust-boundary/credential) PLUS Mermaid for flow/UML/sequence/state/ER, rendered **at build time → inline SVG** (vertical TB, uncapped). Never client-rendered Mermaid (breaks REQ-021/062). |
| One HTML file = one purpose | One Astro page = one purpose; the 12 views are separate pages |

Everything else in Cortex (§1 architecture, §2 typography, §4 SVG, §5 tone, §6
integrity, §7 chrome, §8 a11y) applies unchanged in intent.

## 2. Theme-Adapter Contract (Pattern B) — never change the colour theme

The existing theme lives in `plan-dashboard/src/styles/theme.css` as `--c-*` tokens.
Cortex rules reference tokens by Cortex names. Bridge them with a thin adapter that
maps Cortex names → existing values, and ADD the four missing aliases. Never replace
an existing value; the editorial-modern palette and reader aesthetic stay intact.

| Cortex token | Existing equivalent | Action |
|---|---|---|
| `--bg-primary` | `--c-bg` | alias |
| `--bg-secondary` | `--c-bg-card` | alias |
| `--bg-tertiary` | `--c-bg-elev` | alias |
| `--bg-card` | `--c-bg-card` | alias |
| `--text-primary` | `--c-ink` | alias |
| `--text-secondary` | `--c-ink-dim` | alias |
| `--text-tertiary` | `--c-ink-muted` | alias |
| `--text-muted` | `--c-ink-muted` | alias |
| `--accent-primary` | `--c-accent` | alias |
| `--accent-secondary` | `--c-accent-soft` | alias |
| `--accent-primary-dim` | derive from `--c-accent` at ~0.12 alpha | alias |
| `--accent-secondary-dim` | derive from `--c-accent-soft` at ~0.12 alpha | alias |
| `--color-success` | `--c-green` | alias |
| `--color-warning` | `--c-amber` | alias |
| `--color-error` | `--c-red` | alias |
| `--radius-sm/md/lg` | `--r-sm/md/lg` | alias |
| `--font-sans` | `--font-body` | alias |
| `--font-display` | **MISSING** | ADD (new alias; pick from existing display/serif intent — do not introduce a new brand font without Asif) |
| `--font-mono` | **MISSING** | ADD (new alias) |
| `--glass-bg` | **MISSING** | ADD as a near-opaque card surface mapped to `--c-bg-card` (light theme → drop `backdrop-filter`, per Cortex Appendix D) |
| `--glass-border` | **MISSING** | ADD mapped to existing border/`--c-ink` at low alpha |

Single-accent fallback for the gradient title (REQ-013): if only one accent reads
well, gradient from `--text-primary`→`--accent-primary`; never invent a second accent
(REQ-018).

## 3. The non-negotiables

The MUST-tier rules are NOT restated here — they live in exactly one short card,
[docs/standards/html-view-quality-digest.md](../../docs/standards/html-view-quality-digest.md)
(one line per rule, cited by `REQ-NNN`). Keep the digest in context while authoring;
open the full [standard](../../docs/standards/html-view-quality.md) only for a rule's
exact wording, examples, or its SHOULD/MAY siblings. This single-source rule is
deliberate (WC7b) — duplicating rule text across the skill, the agent, and the standard
is how the three drift apart.

Three repo-specific deltas the digest flags but that bear repeating here because they
are the ones most often broken on THIS site:

- **D-DoD beats Cortex's inline guidance.** Where the standard says "inline JS" /
  "re-assert the floor in an inline `<style>`", the repo DoD wins: external CSS/JS only,
  ZERO inline styling. (Those Cortex lines assume a standalone `file://` doc; we ship Astro.)
- **D-DIAGRAM.** Diagrams vertical (top→bottom), uncapped (no height clamp on SVG
  containers), varied (no two adjacent views lead with the same archetype); Mermaid →
  build-time inline SVG, never client-rendered (would break REQ-021/062).
- **D-THEME.** Never change a `theme.css` colour value; add Cortex-token aliases only (§2).

## 4. Conformance workflow

1. **Author** the view/component per §1–§3, consuming the shared layout + `theme.css`.
2. **Self-check** against Cortex §10 (the per-tier checklist) and §11 (the automated
   greps — adapt the `DIR` to the built output / the relevant `plan-dashboard/src`
   files).
3. **Gate** with the `html-view-challenger` agent: it emits `REQ-NNN`-cited
   MUST/SHOULD findings, converges fix→re-audit, and stamps **Level 1 Conformant**
   (all MUSTs) / **Level 2 Recommended** (all SHOULDs too) / **Level 3 Exemplary**.
4. **MUST findings block.** SHOULD findings warn (skip only with a stated reason in a
   code comment near the deviation).
5. **Footer** records the conformance level + provenance (REQ-047, §13).

## 5. Process guardrails

- **Discuss per-view redesigns one page at a time** before changing anything (Asif,
  2026-05-29). This skill governs HOW a view is built; WHAT each view shows is agreed
  page by page first.
- **Plan-first gate** still applies: plan entry + snapshot + approval before executing
  a build.
- **Never change `theme.css` colour values.** Add aliases only (§2).
- **Keep the directory `plan-dashboard/`** in all paths/commands; name the app "the
  Podcast Factory Astro Site" in prose.
