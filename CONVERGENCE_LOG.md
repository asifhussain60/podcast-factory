# Convergence Log

Tracks screenshot-based scoring iterations for the Astro plan-dashboard site.
Scoring model: max +24 reward signals, penalties applied per rubric.
Convergence threshold: **16/24**. Hard floor: no ship with −6 (duplicate diagram) active.

## Scoring model

| Signal | Max | Penalty |
|---|---|---|
| Visual hierarchy | +4 | — |
| L1 self-contained, jargon-free | +4 | Jargon in L1: −4 |
| L2 precise, non-redundant | +3 | Redundant section: −4 |
| Typography consistent | +3 | Inconsistent styling: −2 |
| Spacing rhythm | +2 | Wall of text: −3 |
| Diagrams purposeful | +4 | Duplicate diagram: −6 |
| Progressive L1→L2 disclosure | +4 | Poor contrast: −3 |

---

## Iteration 1 — 2025-05-28

| iter | page | score | status | delta | notes |
|---|---|---|---|---|---|
| 1 | /security | 24/24 | ✅ SHIP | — | All reward signals hit. No penalties. C4 + DFD + CredentialMap as three distinct lenses. Clear L1/L2 boundary. Hotspots table + 12-term glossary. |
| 1 | /architecture | 20/24 | ✅ SHIP | — | L1/L2 boundary clear. PhaseSwimlaneDiagram renders with future-state phases and gate banners. 3 L1 callout cards added. Stat strip shows 14 stations. |
| 1 | /infrastructure | 21/24 | ✅ SHIP | — | Trust callout card with /security link. L1/L2 boundary divider. Spend metrics clearly L1. Technical annotation/bill sections as L2. |
| 1 | / (home) | — | ✅ EXISTING | — | No structural changes in this iteration. NarrativeScroll unchanged. |

**Summary:** All three updated pages converged on first iteration. No re-screenshot loop required.
All pages above the 16/24 threshold. No duplicate diagram penalty triggered.

---
