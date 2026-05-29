# Continuation prompt — podcast-factory Astro site overhaul

**How to use:** paste this as your first message in a new Claude Code session in the `podcast-factory` repo. It is self-contained — a fresh session with no memory of the prior chat can pick up from here.

---

## My ask (Asif)

Begin the discussion on the **complete podcast-factory Astro site overhaul**. We have already converged the *content* of what the site must show (see Context below) and a per-view diagram spec. I want to converge the *overhaul itself* — visual language, structure, and build approach — and then build it. Work with me the same way as before: restate intent in one line, challenge weak assumptions, recommend the strongest option, ask **one question at a time** with a clearly marked **(Recommended)** default and a short plain-English why, max ~3 questions before proceeding on best assumption. Plain-English responses (H2/H3 headings, blockquote callouts, alphabetized Next, no jargon in chat). Plan-first gate applies: design → plan entry → `cd plan-dashboard && npm run snapshot` → my approval → build. Never open a PR for this repo (commit + push to `develop` directly).

## HARD CONSTRAINTS — do not violate (Definition of Done)

1. **Do NOT modify the existing CSS or the existing colour theme.** The current palette/theme stays exactly as-is. New work composes within it.
2. **Zero inline styling across any view.** No `style="..."` attributes, no inline `<style>` blocks in components/pages. DoD fails if any inline styling exists.
3. **All styling and scripts referenced through external file links.** CSS via external stylesheet links/imports; JS via external script files. No embedded style/script bodies.
4. Diagrams: **vertical flow only** (top-to-bottom, never left-right); **no max-height cap** on SVG/diagram containers (the page scrolls, the diagram grows); **variety** (rotate diagram types so no two adjacent views look alike).
5. No new colour theme, no theme swap, no "while I was in there" restyling.

## What I want the overhaul to achieve

Turn the dense written architecture into something I can **understand visually**. A guided Overview front door that explains the whole system top-to-bottom in one scroll (for me), plus the existing detailed views enriched with varied vertical diagrams and labelled by audience ("For you" conceptual vs "For technical teams" infrastructure). The infrastructure-architecture views must carry the depth technical teams need.

---

## Context — what was decided in the prior session (read these first)

**Read in this order:**
1. `_workspace/prompts/improvements/_tasklist.md` — the cross-session ledger (decisions D1–D21, standing prefs, gap-fill, T4 site-redesign requirements). **Read first.**
2. `_workspace/prompts/improvements/07-site-redesign-spec.md` — the full design-on-paper spec: every view, every diagram (type/audience/content), global styling standard, build methodology, the styling DoD above.
3. `_workspace/plan/refactor/plan.yaml` → section `wisdom_corpus_program` (18 decisions, waves WC1–WC6) and `_workspace/plan/refactor/plan.md` (human-readable, plan blocks 1–6).
4. `_workspace/prompts/improvements/00-audit-findings.md` — the repo audit (incl. the preserved prior Plan Audit punchlist).

### The three design topics converged (T1–T3)
- **T1 Wisdom corpus** — consolidate KQUR + KASHKOLE (frozen) + KSESSIONS (live, dump-sync) into the EXISTING `CONTENT/knowledge-base/knowledge.db` (it already has the corpus + annotation + tradition schema, empty). Tiered dedup; tradition auto-stamp; KASHKOLE never re-translated; KQUR canonical Quran; SQLite, no Docker. (D1–D9, D16, D17)
- **T2 Annotation engine** — the MCP blackbox drives corpus-verified markers (Quran/hadith/term/topic) rendered IN the existing `ChapterEditor`; interpretive tags (esoteric/reality/sharia) suggest-only; sidecar storage; corpus is the sole authority (no quran.com/Gemini fallback). (D10–D13)
- **T3 Intelligence ↔ podcast** — ONE lean knowledge phase after enrich (0e), before the existing review gate (06a): reads each chapter once → feeds both podcast framing and reader markers; tradition-filtered; pilot on `ayyuhal-walad`. (D14, D15)
- **Absorbed:** the prior audio-intake/translation/review-gate/Gemini "Wave I" work is now wave WC5. (D18)

### Plan updates made
- Added `wisdom_corpus_program` to `plan.yaml` (waves WC1 corpus, WC2 blackbox+annotation, WC3 knowledge phase, WC4 Wisdom Corpus UI, WC5 audio-intake, **WC6 site redesign**) + matching plan.md blocks 1–6. Status: AWAITING_APPROVAL.
- Dashboard snapshots regenerated. Committed + pushed to `develop` (no PR).
- Cleanup: removed YNAB MCP (both configs); deleted three absorbed prompt files; flushed sprawl.

### Site facts (verified, do not re-trust docs)
- 12 top-level views: `index, overview, dashboard, architecture, system-map, infrastructure, db-schema, intelligence, quality, security, plan, annotation-ops` + `library/` (reader+`ChapterEditor`) + `wisdom/` (corpus area, already routed).
- Existing bespoke diagram components: C4ContextDiagram, PhaseSwimlaneDiagram, DbArchitecture, TrustBoundaryDFD, CredentialMap, LayerStack, StackFlow, StepDiagram, NarrativeScroll, PipelineSpine/Rail, SpendChart, InfraColumns.
- `d3` is a dependency; **Mermaid is NOT** (D19 adds it for flow/UML/sequence/state/ER → inline SVG, vertical, uncapped).

### Redesign decisions already locked (D19–D21)
- **D19** — hybrid: Mermaid for flowcharts/UML/sequence/state/ER; keep bespoke React/SVG for system/swimlane/trust-boundary/credential.
- **D20** — guided "Overview" front door (reuse `NarrativeScroll`) + audience-labeled drill-down views.
- **D21** — design ALL views on paper first (spec doc 07), then build everything (no incremental pilot).

---

## My recommendations to open the discussion (Claude: propose, don't just execute)

1. **Reconcile the styling DoD against the current code FIRST.** Before any design talk, audit the existing views for (a) inline `style=` usage, (b) inline `<style>`/`<script>` blocks, (c) whether current components rely on Tailwind utility classes — because "zero inline styling + external file links only" may conflict with a utility-class approach. Tell me the gap and recommend how new diagrams/components meet the DoD without touching the existing CSS/theme. **This is the highest-leverage first question.**
2. **Confirm the per-view diagram set in spec 07** — add/drop/relabel any view; lock audience labels.
3. **Lock the shared diagram infrastructure** — how Mermaid renders to inline SVG at build, where the vertical/no-height-cap rules live (external stylesheet, not inline), and the audience-badge component — all DoD-compliant.
4. **Then** write WC6 build steps into the plan at finer grain, snapshot, get my approval, and build per the spec's build sequence (shared infra → Overview front door → technical cluster → conceptual cluster → Wisdom view + Plan roadmap → reader/editor markers).

## Definition of Done (site overhaul)
- Every view in spec 07 has its specified diagrams; all vertical; no height caps; variety preserved.
- Guided Overview explains the whole system top-to-bottom; every view audience-labeled.
- **Zero inline styling anywhere; all styling + scripts via external file links; existing CSS + colour theme unchanged.**
- Builds clean; WCAG AA contrast floor; no duplicate diagrams.
