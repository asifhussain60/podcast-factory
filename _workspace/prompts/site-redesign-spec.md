# 07 — podcast-factory Astro site redesign spec (DESIGN ON PAPER — review before build)

> **STATUS 2026-05-29: design-on-paper per Asif (D21). Discuss/approve this whole spec BEFORE any implementation.** Decisions D19 (hybrid diagram tech), D20 (guided Overview front door + audience-labeled drill-downs), D21 (design-all-first) govern. Plan-first gate: this spec → plan entry → snapshot → Asif approval → build.

## Global principles (apply to EVERY diagram, baked into shared styling)
- **Vertical flow only.** Mermaid `flowchart TB`, sequence/class diagrams top-down. Bespoke components stack vertically. NO left-right layouts.
- **No height cap.** Diagram containers grow to full content height; no `max-height`, no inner scroll. Page scrolls, diagram doesn't.
- **Variety by rotation.** No two adjacent views lead with the same diagram type. Palette below is rotated deliberately.
- **Audience label on every view:** badge `For you` (conceptual) / `For technical teams` (infra/engineering) / `For both`.
- **Hybrid tech (D19):** Mermaid (build-time → inline SVG) for flowcharts/UML/sequence/state/ER; existing bespoke React/SVG components for high-level system, swimlane, trust-boundary, credential map.
- **Aesthetic:** editorial-modern (Stripe/MIT Press) per locked reader aesthetic — restrained palette, strong serif headings, minimal ornament.

## Diagram-type palette (the variety set)
| Type | Tool | Best for |
|---|---|---|
| System / context map | bespoke (C4ContextDiagram) | "how it all fits" big picture |
| Flowchart (TB) | Mermaid | processes, decisions, pipelines |
| Swimlane | bespoke (PhaseSwimlaneDiagram) | phases × responsibilities |
| UML class / ER | Mermaid | schema, data model |
| Sequence | Mermaid | lifecycles, request/response over time |
| State diagram | Mermaid | status machines (review gates, ingestion) |
| Data-flow (DFD) | bespoke (TrustBoundaryDFD) | data crossing trust boundaries |
| Layer stack | bespoke (LayerStack/StackFlow) | dependency layers |
| Deployment / component | Mermaid + bespoke (InfraColumns) | infra topology |
| Roadmap rail | bespoke (PipelineSpine/Rail) | waves, sequence |

---

## Per-view spec

### 0. Overview (NEW front door — `overview.astro`)  ·  For both
The guided top-to-bottom narrative (reuse `NarrativeScroll`). Read once, understand everything; links into every drill-down.
| # | Diagram | Type | Shows |
|---|---|---|---|
| 0.1 | The whole system, one picture | System map (bespoke) | Sources → Wisdom Corpus (knowledge.db) → Blackbox → Pipeline (knowledge phase) → Reader + Podcast |
| 0.2 | Where a book travels | Flowchart TB (Mermaid) | PDF/audio intake → phases → gates → episodes + annotated chapters |
| 0.3 | One read, two outputs | Sequence (Mermaid) | Knowledge phase reads chapter once → framing + reader markers |
| 0.4 | Where to go next | Index rail (bespoke) | Audience-labeled links to all drill-down views |

### 1. System Map (`system-map.astro`)  ·  For both
| 1.1 | Three-angles view | System/context (bespoke C4) | Corpus = source, blackbox = access, intelligence = writer, reader = consumer |
| 1.2 | Component responsibilities | Component diagram (Mermaid) | Each subsystem + what it owns |

### 2. Architecture (`architecture.astro`)  ·  For both
| 2.1 | Corpus consolidation | Flowchart TB (Mermaid) | 3 sources → extract → dedup (tiered) → knowledge.db; KQUR/KASHKOLE retired, KSESSIONS synced |
| 2.2 | Dedup decision | Flowchart TB w/ branches (Mermaid) | exact/near → auto-merge; borderline → review queue; ambiguous → never merge |
| 2.3 | Annotation engine data-flow | DFD (bespoke) | chapter → classify via blackbox → sidecar markers → editor render |
| 2.4 | Module layers | Layer stack (bespoke) | Core → Domain → Intelligence+Authoring → Phases → Driver (DR-005) |

### 3. DB Schema (`db-schema.astro`)  ·  For technical teams
| 3.1 | knowledge.db entity model | ER / UML class (Mermaid) | external_corpora, corpus_chapters, atoms(+tradition), atoms_sources/variants, annotations, manual_review_queue |
| 3.2 | Atom lifecycle | State diagram (Mermaid) | new → known/variant/conflict → review/merged |
| 3.3 | Tradition stamping | Flowchart TB (Mermaid) | source/content-type → fatimid-ismaili / universal |

### 4. Intelligence (`intelligence.astro`)  ·  For both
| 4.1 | Knowledge phase placement | Swimlane (bespoke) | CANONICAL_PHASES with the new phase after 0e, before 06a |
| 4.2 | Extract → librarian → augmenter | Flowchart TB (Mermaid) | one read → atoms → two renderers; conflicts to 06a |
| 4.3 | Tradition-filtered injection | Sequence (Mermaid) | augmenter checks tradition before injecting |

### 5. Infrastructure (`infrastructure.astro`)  ·  For technical teams  (ADD missing content)
| 5.1 | Deployment topology | Deployment (Mermaid + InfraColumns) | Mac-local, SQLite corpus (no Docker), Astro site, Azure/Anthropic/Gemini externals |
| 5.2 | Blackbox dual transport | Component (Mermaid) | MCP stdio (agents) + HTTP :4390 (browser) → same query layer |
| 5.3 | KSESSIONS dump-ingest path | Flowchart TB (Mermaid) | drop dump → ingest → dedup → corpus (idempotent) |
| 5.4 | External services + credentials | Credential map (bespoke) | which key reaches which service; YNAB removed |

### 6. Security (`security.astro`)  ·  For technical teams
| 6.1 | Trust boundaries | DFD (bespoke TrustBoundaryDFD) | corpus-only authority; no public-web fallback |
| 6.2 | Tradition firewall | Flowchart TB (Mermaid) | universal vs tradition-scoped injection rules (P7) |
| 6.3 | Secret handling | Flowchart TB (Mermaid) | gitignored configs, no plaintext in git, rotation |

### 7. Quality (`quality.astro`)  ·  For both
| 7.1 | Two review gates | State diagram (Mermaid) | Source Review (06a) + Publish Review |
| 7.2 | PEQ scoring | Flowchart TB (Mermaid) | Fidelity/Voice/Structure/Enrichment → PASS/WARN/FAIL |
| 7.3 | Dedup tiers | Flowchart TB (Mermaid) | auto-merge / review / never |

### 8. Plan (`plan.astro`)  ·  For you
| 8.1 | Wisdom Corpus Program roadmap | Roadmap rail (bespoke) | WC1→WC5 + build order, vertical |
| 8.2 | Wave dependencies | Flowchart TB (Mermaid) | depends_on graph, top-down |

### 9. Annotation Ops (`annotation-ops.astro`)  ·  For both
| 9.1 | Marker lifecycle | Sequence (Mermaid) | generate (phase) → render in editor → suggest tags → human comment/accept |
| 9.2 | Reference vs interpretive | Flowchart TB (Mermaid) | auto reference markers vs suggest-only esoteric/reality/sharia |

### 10. Wisdom Corpus view (`wisdom/`)  ·  For you  (rename from "Kashkole")
| 10.1 | Curation flow | UI flow (Mermaid) | browse → keep/delete → confirm dedup candidates |
| 10.2 | Review queue | State diagram (Mermaid) | pending → confirmed/merged/rejected |

### 11. Dashboard (`dashboard.astro`)  ·  For both
Keep operational tiles; add one small vertical sparkline cluster. No heavy diagrams (it's a status surface).

### 12. Reader + Editor (`library/.../chapter`)  ·  For you
Not a diagram view — but the marker-render target. Spec: reference markers visible inline in `ChapterEditor`, per-type color/icon, comment integration. (Covered functionally in docs 04/06.)

---

## Build sequence (after approval)
1. Shared diagram infra: Mermaid build integration (→ inline SVG), vertical + no-cap styling tokens, audience-badge component.
2. Overview front door (0.1–0.4) + navigation wiring.
3. Technical cluster: Infrastructure, DB-Schema, Security (for teams).
4. Conceptual cluster: Architecture, System-Map, Intelligence, Quality, Annotation-Ops.
5. Wisdom Corpus view + Plan roadmap refresh.
6. Reader/editor marker rendering (joins with WC2).

## Diagram styling standard (absorbed from architecture-diagram-brief.md, 2026-05-29)
Applies to the technical-team diagrams (Architecture, Infrastructure, Security, DB-Schema, Intelligence phase swimlane):
- **Flow:** top-to-bottom on every diagram (already global).
- **Min font:** 14px throughout.
- **Connector labels required** on every arrow — include protocol + auth method (e.g. `HTTPS / API key`, `stdio / none`).
- **Trust boundaries:** dashed coloured rectangles enclosing related nodes.
- **Colour semantics (consistent across all diagrams):** teal = local/safe flows; amber = managed external credential flows; red = flows outside pipeline control (risk); green = verified/mitigated.
- **Technical lenses to cover** (map onto views above): L1 System Context (→ System-Map 1.1), L2 Containers & Data Flow w/ trust boundaries (→ Infrastructure 5.1/5.2 + Security 6.1), L3 Pipeline Phase Sequence w/ model+service+token-class+halt-gates (→ Intelligence 4.1), L4 Credentials & Auth Boundary Map (→ Infrastructure 5.4).
- **Two non-diagram artifacts to include:** a Hotspots Index table (SEC/COST/ARCH/OK-verified audit punchlist, cross-referenced to the lens that surfaces each) on the Security or Infrastructure view; a Glossary (domain terms) linked from the Overview.

## Build methodology (absorbed from podcast-factory-visual-build.md, 2026-05-29)
For the build phase (after approval), each view is built with a self-scoring convergence loop:
- **Two-audience linear flow per page:** conceptual (For you) content resolves COMPLETELY before technical (For teams) content begins; a reader who stops at the boundary is satisfied; a reader who continues sees nothing repeated.
- **Build → screenshot → score → converge:** implement, capture a full-page screenshot (Playwright), inspect the IMAGE (not just source), score against a rubric (visual hierarchy, self-contained conceptual layer, non-redundant technical layer, consistent typography, uniform spacing, purposeful diagrams, felt progressive disclosure), refactor highest-penalty item first; max 5 iterations/section then flag for human review.
- **Hard floors:** never ship a duplicate diagram; WCAG AA contrast is the floor; never declare done without a screenshot.
- **STYLING DoD (Asif, 2026-05-29 — overrides the old 'Tailwind utilities' note):** ZERO inline styling on any view; ALL styling and scripts referenced via external file links; DO NOT modify the existing CSS or colour theme.

## Open items for Asif (this spec)
- Confirm the per-view diagram set above (add/remove any).
- Confirm audience labels per view.
- Any view to drop or merge?
