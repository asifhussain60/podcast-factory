<!--
  Parked backlog (2026-05-29): structural audit of the 13 Astro-site views against the
  redesign spec (docs ref: _workspace/prompts/improvements/07-site-redesign-spec.md).
  Captured at Asif's request to defer the per-view redesign while the intelligence +
  podcast-pipeline work takes priority. Resume from here; discuss each view one page at
  a time before changing it. Method: structural sweep (audience badge / Mermaid usage /
  bespoke diagram components / inline SVG) — NOT a full visual review.
-->
# Site-view redesign — parked audit (2026-05-29)

**Status:** Per-view redesign DEFERRED. Priority shifted to the intelligence + podcast
pipeline. This is the resume point.

## Per-view state vs spec (07-site-redesign-spec.md)

| View | Spec diagrams (§) | Built? | Gap to close when resumed |
|---|---|---|---|
| Overview | §0 system map + book journey + sequence + index rail | ✅ done | Mermaid×3 + OverviewSystemMap + OverviewIndexRail present; verify 0.1–0.4 all covered |
| Infrastructure | §5 deployment + transport + ingest + credentials | ✅ done | Mermaid×3 + InfraDeployment/InfraColumns; rebuilt in WC6f |
| Security | §6 trust boundaries + tradition firewall + secrets | ✅ done | Mermaid×3; vertical diagrams + credentials table (recent) |
| Architecture | §2 consolidation + dedup + DFD + layers | 🟡 partial | Has bespoke components (LayerStack/Swimlane/Spine/Rail); spec wants Mermaid dedup-flow (2.1/2.2) — confirm coverage |
| DB-Schema | §3 ER model + atom lifecycle + tradition stamping | 🟡 partial | Has DbArchitecture; spec wants Mermaid ER (3.1) + state machine (3.2) — likely missing |
| System-Map | §1 C4 context + component diagram | 🔴 pending | No Mermaid, no bespoke comp; 1 inline SVG only — diagrams not built |
| Intelligence | §4 swimlane + extract→librarian→augmenter + sequence | 🔴 pending | No diagrams at all — text-only |
| Quality | §7 two-gates state + PEQ flow + dedup tiers | 🔴 pending | No diagrams at all — text-only |
| Plan | §8 roadmap rail + wave-dependency flow | 🔴 pending | No diagrams; roadmap rail not wired into the page |
| Annotation-Ops | §9 (annotation engine ops) | 🔴 pending | No diagrams at all — text-only |
| Dashboard | §11 | n/a | Live-metrics surface; 1 badge; not a diagram view |
| Wisdom (index) | §10 (rename from Kashkole) + review-queue state | 🔴 pending | No badge, no diagrams; lowest priority (audience surface) |
| Library (index) | §12 reader/editor markers | n/a | Reader surface, not a diagram view |

## Resume order (when picked back up)
1. **System-Map, Intelligence, Quality, Plan, Annotation-Ops** — the five text-only views
   missing all spec'd diagrams (highest gap).
2. **Architecture, DB-Schema** — confirm/complete the Mermaid pieces the spec calls for.
3. **Wisdom** — rename + review-queue state diagram.
4. Cross-cutting: the 51 lint warnings (`npm run lint:views`) — extract oversized `<style>`
   blocks, author SVG a11y triples, remove `<svg>` w/h attrs, NarrativeBase skip-link.

## Build discipline (unchanged)
- One page at a time; discuss before changing (locked 2026-05-29).
- Build → full-page screenshot → score → converge (≤5 iterations), per spec build methodology.
- DoD: zero inline styling, external CSS/JS, colour theme unchanged; gate via
  `html-view-challenger` + `npm run lint:views`.
