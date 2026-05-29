# Continuation prompt — per-view Cortex redesign of the Podcast Factory Astro Site

**How to use:** paste this as your first message in a new Claude Code session in the
`podcast-factory` repo. It is self-contained — a fresh session can pick up from here.

---

## My ask (Asif)

The Cortex substrate is built (skill + challenger agent + enforcement hook). Now I want
to **redesign the Podcast Factory Astro Site (`plan-dashboard/`) one view at a time**,
discussing the design of each page WITH ME before you change anything. Work the way we
have been: restate intent in one line, challenge weak assumptions, recommend the
strongest option, ask **one question at a time** with a clearly marked **(Recommended)**
default and a short plain-English why (max ~3 questions, then proceed on best
assumption). Plain-English responses (H2/H3, blockquote callouts, alphabetized Next, no
jargon). Plan-first gate applies: design-on-paper → plan entry → `cd plan-dashboard &&
npm run snapshot` → my approval → build. Never open a PR (commit + push to `develop`).

## Non-negotiables (already locked — do not re-litigate)

- **Follow the Cortex HTML View Quality Standard implicitly.** Load and apply
  `skills-staging/html-view-quality/SKILL.md`; gate every built view through the
  `html-view-challenger` agent before it's "done". The `UserPromptSubmit` hook will
  remind you automatically — never bypass, never drift.
- **Styling DoD:** external CSS/JS only; ZERO inline styling; theme-adapter onto the
  existing `--c-*` tokens with the **colour theme unchanged**; diagrams vertical +
  uncapped + varied; Mermaid rendered at build → inline SVG.
- **Conflict rule:** blend both standards; content + SVG lean Cortex; delivery
  mechanics follow the DoD.
- **One view at a time.** We agree the design of each page (what it shows, which
  diagrams, audience labels) BEFORE any code changes. No bulk rewrite.

## Read first (context)

1. `skills-staging/html-view-quality/SKILL.md` — the craft contract + theme-adapter
   token map + conformance workflow.
2. `docs/standards/html-view-quality.md` — the full 74
   `REQ-NNN` Cortex rules (cite by ID).
3. `_workspace/prompts/improvements/07-site-redesign-spec.md` — the per-view diagram
   spec already drafted (every view, every diagram: type/audience/content).
4. `_workspace/plan/refactor/plan.yaml` → `wisdom_corpus_program` → WC6 (and its
   `cortex_substrate`) for status + decisions D19–D25.
5. `infra/claude-agents/html-view-challenger.md` — the output gate's checklist.

## The views to redesign (in `plan-dashboard/src/pages/`)

`index` (NarrativeBase hero), `overview`, `dashboard`, `architecture`, `system-map`,
`infrastructure`, `db-schema`, `intelligence`, `quality`, `security`, `plan`,
`annotation-ops`, plus the `library/` and `wisdom/` sections. Existing bespoke diagram
components live in `plan-dashboard/src/components/` (C4ContextDiagram,
PhaseSwimlaneDiagram, DbArchitecture, TrustBoundaryDFD, CredentialMap, LayerStack,
StackFlow, NarrativeScroll, PipelineSpine, PipelineOverviewRail, SpendChart,
InfraColumns; StepDiagram is a stub). `d3` is a dep; Mermaid is to be added (D19).

## Known prerequisite (surface it, don't silently fix)

WC6c remediation is still pending: ~90 inline `style=` instances + 6 inline `<style>`
+ 2 inline `<script>` blocks across the current views/components violate the
zero-inline-styling DoD (audit 2026-05-29). The `html-view-challenger` will flag these.
Decide with me per-view whether to remediate as part of that view's redesign or as a
separate pass.

## How to open the discussion (Claude: propose, don't execute)

1. Recommend the **build sequence** across the views (the spec suggests: shared infra →
   Overview front door → technical cluster → conceptual cluster → Wisdom + Plan →
   reader/editor markers). Confirm or adjust with me.
2. Pick the **first view** and bring me its design-on-paper: purpose, audience label
   ("For you" / "For technical teams"), the coffee-test opening, the diagram set
   (archetype + which Cortex/bespoke/Mermaid form, vertical viewBox), and how it meets
   the styling DoD — all before any code.
3. On my approval of that view's design: add the WC6 build entry, snapshot, then build
   it and converge it through the challenger to a declared conformance level.
