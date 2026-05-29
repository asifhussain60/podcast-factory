# Continuation prompt — open topics after the Cortex substrate (podcast-factory)

**How to use:** paste this as your first message in a new Claude Code session in the
`podcast-factory` repo. Self-contained — a fresh session can pick up from here.

---

## My ask (Asif)

The Cortex substrate is built and committed (`develop` @ commit `2832236`): the
`html-view-quality` skill, the `html-view-challenger` agent, the implicit-enforcement
hook, and the canonical "Podcast Factory Astro Site" naming. Now I want to **work
through the remaining open topics with you, discussing each before you change anything.**
Work the way we have been: restate intent in one line, challenge weak assumptions,
recommend the strongest option, ask **one question at a time** with a clearly marked
**(Recommended)** default and a short plain-English why (hard cap ~3 questions, then
proceed on best assumption). Plain-English responses (H2/H3 headings, blockquote
callouts, alphabetized Next, no jargon). Plan-first gate applies: design → plan entry →
`cd plan-dashboard && npm run snapshot` → my approval → build. Never open a PR (commit +
push to `develop` directly).

## Non-negotiables already locked (do not re-litigate)

- **Follow the Cortex HTML View Quality Standard implicitly.** Load + apply
  `skills-staging/html-view-quality/SKILL.md`; gate every built view through the
  `html-view-challenger` agent before it's "done". The `UserPromptSubmit` hook reminds
  you automatically — never bypass, never drift.
- **Styling DoD:** external CSS/JS only; ZERO inline styling; theme-adapter onto the
  existing `--c-*` tokens with the **colour theme unchanged**; diagrams vertical +
  uncapped + varied; Mermaid build-time → inline SVG. Conflict rule: blend both; content
  + SVG lean Cortex; mechanics follow the DoD.
- **App naming:** the Astro app is the **Podcast Factory Astro Site**; directory stays
  `plan-dashboard/`. There is no separate `podcast-reader` app.
- **One view at a time.** Agree each page's design (what it shows, diagrams, audience
  labels) BEFORE any code. No bulk rewrite.

## Read first

1. `skills-staging/html-view-quality/SKILL.md` — craft contract + theme-adapter token
   map + conformance workflow.
2. `_workspace/prompts/improvements/html-view-quality.instructions.md` — full 74
   `REQ-NNN` Cortex rules (cite by ID).
3. `_workspace/prompts/improvements/07-site-redesign-spec.md` — the per-view diagram
   spec (every view, every diagram: type/audience/content).
4. `_workspace/plan/refactor/plan.yaml` → `wisdom_corpus_program` → WC6 +
   `cortex_substrate` (decisions D19–D25, what shipped, what's deferred).
5. `infra/claude-agents/html-view-challenger.md` — the output gate's checklist.

## The open topics (triage these with me; recommend an order)

### Topic 1 — Per-view Cortex redesign (the main thread)

Redesign the Podcast Factory Astro Site one view at a time. Views in
`plan-dashboard/src/pages/`: `index` (NarrativeBase hero), `overview`, `dashboard`,
`architecture`, `system-map`, `infrastructure`, `db-schema`, `intelligence`, `quality`,
`security`, `plan`, `annotation-ops`, plus the `library/` and `wisdom/` sections.
Existing bespoke diagram components in `plan-dashboard/src/components/`: C4ContextDiagram,
PhaseSwimlaneDiagram, DbArchitecture, TrustBoundaryDFD, CredentialMap, LayerStack,
StackFlow, NarrativeScroll, PipelineSpine, PipelineOverviewRail, SpendChart,
InfraColumns; StepDiagram is a stub. `d3` is a dep; Mermaid to be added (D19).

For the FIRST view, bring me design-on-paper before any code: purpose, audience label
("For you" conceptual / "For technical teams" infra), the coffee-test opening, the
diagram set (archetype + Cortex/bespoke/Mermaid form, vertical viewBox), and how it
meets the styling DoD. The spec suggests build order: shared infra → Overview front door
→ technical cluster → conceptual cluster → Wisdom + Plan → reader/editor markers —
confirm or adjust with me.

### Topic 2 — WC6c inline-styling remediation (DoD compliance)

Audit 2026-05-29 found ~90 inline `style=` instances + 6 inline `<style>` blocks + 2
inline `<script>` blocks across current views/components — these violate the
zero-inline-styling DoD and the `html-view-challenger` will flag them. Decide with me:
remediate per-view as each view is redesigned, OR run one dedicated remediation pass
first. Note the NarrativeScroll GSAP `@keyframes` need special handling (move to external
stylesheet, verify animation parity).

### Topic 3 — Two pre-existing config drifts (flagged 2026-05-29; not yet fixed)

- **Snapshot-regen hook not wired.** CLAUDE.md claims a `PostToolUse` hook regenerates
  plan snapshots on edits to architecture.md / plan.md / plan.yaml / pipeline-debt.md.
  The script `.claude/hooks/plan-snapshot-regen.sh` exists but is NOT registered in
  `.claude/settings.json` (or settings.local.json). Today the regen is manual. Decide:
  wire it as the documented safety net, or update the docs to match reality.
- **YNAB MCP still enabled.** `.claude/settings.local.json` still lists `ynab` under
  `enabledMcpjsonServers` despite the recent "remove YNAB MCP" commit. Decide: remove
  it, or confirm it should stay.

## How to open

Restate my intent in one line, then recommend the order to tackle Topics 1–3 (my
instinct: clear the small Topic 3 drifts first so the workspace is clean, then start
Topic 1 view-by-view with Topic 2 folded into each view's redesign — but challenge that
if a better sequence exists). Ask me one question only if it materially changes the
outcome. Then bring me the first concrete step for approval.
