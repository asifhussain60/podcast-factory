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

## Iteration 2 — 2026-05-28 (full site audit)

| iter | page | score | status | delta | notes |
|---|---|---|---|---|---|
| 1 | /quality | ERROR | refactor | `loadBaseline` parsed flat dict JSON as `BookBaseline` → `chapters` undefined → TypeError on `c.total` | Baseline JSON is `{chSlug: {scores}}` not `{chapters:[]}` |
| 2 | /quality | 17/24 | ✅ CONVERGED | Fixed `loadBaseline` to detect and convert dict format; added defensive `filter` on `allChapters` | Fleet avg 73.0, 21 chapters, 0 PASS / 17 WARN / 4 FAIL rendered correctly |
| 1 | /security | blank | investigate | Playwright screenshot taken before web fonts loaded — false negative | No code defect; 3s wait confirms full render at 20/24 |
| 1 | / (home) | blank | investigate | Same font-load timing issue | NarrativeScroll + GSAP renders correctly at 18/24 with wait |

**Summary:** One real defect fixed (quality page TypeError). Two false negatives resolved (font load timing). All 12 pages confirmed ≥ 16/24. No duplicate-diagram penalty anywhere. Playwright screenshots must use `--wait-for-timeout=3000` for this site.

---
