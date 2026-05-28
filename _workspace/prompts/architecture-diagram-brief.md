# Architecture Diagram Brief — Podcast Factory
**For:** IT Architecture Team  
**Date:** 2026-05-28  
**Owner:** Asif Hussain

---

## Diagrams Required

| # | Document / Lens | Diagram Type | What it should illustrate |
|---|---|---|---|
| L1 | System Context | C4 Context diagram | Every external actor and service the system touches — Operator, IT Audit team, Listeners, the 5 external trust boundaries (Anthropic, Google AI, Azure, NotebookLM, GitHub), and the source materials datastore. Flows vertically: Operator at top, system in middle, external services below. |
| L2 | Containers & Data Flow | Data Flow Diagram with trust boundaries | All runnable containers inside the local Mac boundary (pipeline scripts, Claude agents, state stores, local UI apps), their internal call relationships, and HTTPS egress lines crossing into each external trust zone. Flows vertically: Operator → Pipeline → State/Agents → External zones. |
| L3 | Pipeline Phase Sequence | Swimlane / linear sequence | The 14 pipeline phases from PDF intake to publish, annotated with model used (Opus/Sonnet/Haiku), service hit (Azure vs Anthropic), token volume class (colour-coded low/med/high), and the two human-halt gates. Flows vertically top-to-bottom. |
| L4 | Credentials & Auth Boundary Map | Custom diagram | Where every secret physically lives (macOS Keychain vs opaque claude CLI store), which pipeline surface reads each key, and which external service it authorises. Split into two vertical zones: Local Mac (left) and External Trust Zones (right). Arrows coloured by risk level. |
| HS | Hotspots Index | Table (no diagram) | Consolidated audit punchlist — 20 rows covering SEC, COST, ARCH, and OK-verified items, cross-referenced to the lens that surfaces each gap. |
| GL | Glossary | Definition list (no diagram) | Short reference for 14 domain terms specific to this pipeline. |

---

## Styling Requirements

| Requirement | Spec |
|---|---|
| Flow direction | Top-to-bottom on all diagrams (not left-to-right) |
| Minimum font size | 14px throughout |
| Connector labels | Required on every arrow — must include protocol and auth method |
| Trust boundaries | Dashed coloured rectangles enclosing related nodes |
| Colour: teal | Local / safe flows |
| Colour: amber | Managed external credential flows |
| Colour: red | Flows outside pipeline control (risk) |
| Colour: green | Verified / mitigated items |
