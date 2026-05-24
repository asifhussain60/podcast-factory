# Operator Index — Cross-Machine Work Dashboard

**Source of truth for "what is each machine doing right now" + "what's queued + at what cost."**
Both machines read this on session start. Updated 2026-05-21 by the Air session.

For the underlying claim/completion protocol see [book-queue.md](../book-queue.md).
For response-format conventions both sessions follow, see [response-conventions.md](../response-conventions.md).

## One repo, one worktree per machine (architecture clarification)

There is **ONE git repo** shared across all machines: `https://github.com/asifhussain60/podcast-factory`.
Each physical machine clones it ONCE into a single working directory (e.g.,
`~/PROJECTS/journal/` on the Air, `~/Code/podcast-factory/book-asaas/` on the Studio).
That single working directory switches between branches as needed —
`develop`, `book/<slug>` per active book, occasionally `feat/*` for framework work.

**Books are processed on branches, not in separate folders.** Each book lives
on its own `book/<slug>` branch. The integration target is `develop`, which
accumulates every shipped book. Production-ready releases promote from
`develop` → `main`.

**Git worktrees are a power feature you generally don't need here.** A worktree
gives you a second working directory on a different branch in parallel.
Useful if you're actively rebasing one branch while another is mid-build —
but for this project's branch-per-book model, single-worktree-per-machine is
cleaner. If you see a second journal folder on a machine and it's on a dormant
branch (0 commits ahead of develop), prune it:

  ```bash
  cd ~/PROJECTS/journal   # the primary worktree
  git worktree remove ~/PROJECTS/journal-feat
  ```

The branch itself survives the worktree removal; you can always check it out
in the primary worktree if you need it.

---

## Machine Status (current snapshot)

| | **Mac Air (secondary)** | **Mac Studio (primary)** |
|---|---|---|
| **In-flight book** | `kitab-al-riyad` | `asaas-al-taveel` |
| **Branch** | `book/kitab-al-riyad` | `book/asaas-al-taveel` |
| **Current phase** | per-chapter / 0g (running — EP10 shipped SHIP-WITH-CAUTION, EP14 in flight after X4 fix) | 0b complete (HOLDING-FOR-OPERATOR-GATES — §§1-8 review) |
| **Pages** | 260 | 416 |
| **Episodes (est)** | 14 (Ep 2 removed; 1 shipped, 1 in-flight, 12 remaining) | 15-20 (pending 0d) |
| **Anthropic spent so far** | ~$13 + EP10/EP14 burn (cost-ledger broken — P6.5 + datetime.UTC AttributeError) | ~$8 estimated (Phase 0a+0b; cost-ledger broken — P6.5) |
| **ETA to ship** | ~12 episodes × 30–90 min wall + reviews; X-bug cycles add overhead | 6-10 days (once operator gates clear) |
| **Last verified** | 2026-05-21T13:30Z | 2026-05-21T11:30Z (Studio session, Azure gate cleared) |
| **Next gate** | Resolve R-PHONETICS-OUT (Asif chose author-side patching in [d2246b3](https://github.com/asifhussain60/podcast-factory/commit/d2246b3)); resume orchestrator on EP14; then EP11→EP13, EP15, ch01a–ch09 | Operator gate: §§1-8 of [operator-review.md](../../../content/drafts/asaas-al-taveel/operator-review.md). (Azure F0 cleared 2026-05-21 — see [mac-studio-primary.md §13](mac-studio-primary.md).) Then framework lane (P22.impl, P4.10, P6.5, P23) on `feat/podcast-w1-foundation` → merge → Phase 0c. |

---

## Queue (priority order — top = next claimed)

Cost and time estimates derived from observed KaR + asaas runs (see "Methodology" at end). Ranges reflect uncertainty; actual will land within the range for typical scholarly Arabic source material.

| # | Book | Pages | Series (est) | Episodes (total est) | Est cost | Wall time | Notes |
|---|---|---|---|---|---|---|---|
| 1 | **Raahat al-Aqal** | 591 | 7 series (one per "sea") | ~25-35 | **$80-120** | **7-10 days** (parallel across 2 machines: ~4-5 days) | al-Kirmani's magnum opus. Natural 7-sea split into 7 book entries (one series each); each "sea" = ~85 pages = 3-5 episodes. Pairs thematically with KaR (same author corpus). |
| 2 | **Kitab Maqbas** | 392 | 1 (evaluate at 0d) | ~12-18 | **$30-50** + extra Azure | **3-5 days** | 236MB scanned PDF → heavy Azure OCR cost (image-only). Structure unknown until 0a lands; may split at 0d if it has named sections. |
| 3 | **Majalis Moyyada** | 139 | 1 | ~5-8 | **$10-20** | **1-2 days** | "Majalis" = sittings/sermon-collection register. Single-series candidate. |
| 4 | **Masaail** | 81 | 1 | ~3-5 | **$8-15** | **~1 day** | Smallest active book. Quick ship. |
| 5 | **Rasail Ikhwan AsSafa** | 865 | 4 thematic clusters → 4 book entries | ~60-80 total | **$200-300** | **14-21 days total** (parallel: 7-11 days) | The Brethren of Purity encyclopedia. 57 epistles in 4 sections: Mathematics (14 epistles), Natural Sciences (17), Soul/Intellect (10), Theology+Comprehensive (16). Each cluster = own book + own series. Save for when pipeline is mature. |

**Queue subtotal**: ~$330-505 across all 5 active queue items, 25-39 days wall clock running both machines in parallel.

## Out of queue

| Book | Slug | Reason | Status |
|---|---|---|---|
| Ayyuhal Walad | `ayyuhal-walad` | Already shipped manually (pre-pipeline) | 5 chapters + 5 episodes + transcript in library. Not re-running. |
| The Master and the Disciple | `the-master-and-the-disciple` | Pre-refined source mode, in progress on coworker session | Chapters frozen (hand-refined by Asif); `_notebooklm/` scaffolding being authored separately. Not in main pipeline queue. |

---

## Cost/time methodology (so you can sanity-check the numbers)

**Per-page Anthropic-API costs observed on KaR + asaas runs (2026-05-19 to 2026-05-21):**

| Phase | Cost rule of thumb | KaR datapoint (260pp, 14ep) |
|---|---|---|
| 0a (Azure ingest) | $0.005-0.010 per page (OCR + Translate, image-density dependent) | $1-3 |
| 0b (Claude refine, chunked) | ~$0.12 per 3000-word window | $3-5 (32 windows) |
| 0c (Claude phonetic) | ~$0.02 per page | $5-6 |
| 0d (Claude chapter design) | ~$3-5 per book (deterministic-ish; per-source-chunk) | $4-6 |
| 0e (Claude enrichment) | ~$0.50 per episode | $5-8 (13 chapters) |
| 0g (Claude per-episode + challenger) | $1-3 per episode (3 outer × 5 inner iterations max) | $14-42 (14 episodes) |
| Trainer | ~$1-2 per book | $1-2 |
| **Total per book** | **~$30-70** for a 200-400 page scholarly book | **~$33-72** observed/projected |

**Per-page wall time:**

| Phase | Wall time | KaR datapoint |
|---|---|---|
| 0a | 5-15 min | done in ~10 min |
| 0b | ~3 min per window | ~95 min (32 windows) |
| 0c | 30-60 min | ~3 hours observed |
| 0d | 1-3 hours (timeout-prone on large chunks) | ~3 hours observed |
| 0e | 1-2 hours | ~2 hours 20 min observed (1 timeout recovery) |
| 0g | 30-60 min per episode | 14 × ~45min = ~10 hours (queued) |
| Trainer | 30-60 min | (pending) |
| **Total per book** | **~12-24 hours wall time per single-book series** | KaR projected ~20 hours total |

**Multi-series books (Raahat, Rasail) scale roughly linearly with series count. Parallelizing across both machines roughly halves total wall time (modulo Anthropic quota throttling when both are LLM-heavy).**

**Caveats:**
- Cost-ledger (P6.5) is currently silent-failing — actual costs are estimates from window/episode counts, not measured. Studio is queued to fix.
- Wall times are "active LLM time"; human-review gates add unbounded clock time (depends on operator availability).
- Quota throttling: heavy LLM phases on both machines simultaneously can throttle both. Stagger when possible.
- First-of-genre books may run 1.5-2x estimate while the pipeline learns the source's quirks (e.g., KaR's Phase 0b re-run after P22.markers fix added 1 day).

---

## Aggregate budget projection (5 queue items + 2 in-flight)

| | Low | High |
|---|---|---|
| Anthropic-API spend | $360 | $550 |
| Wall time (1 machine, sequential) | ~50 days | ~80 days |
| Wall time (2 machines, parallel-safe) | ~25 days | ~40 days |
| Operator-review time (gates) | several hours per book | several days per book |

**To check before scaling further:** the cost-ledger fix (P6.5) is queued to Studio's framework lane. Until it lands, all spend numbers are estimates. Once it lands, both machines can publish per-book actuals and we can refine these projections.

---

## Update protocol

- This file's **Machine Status** rows are updated by each machine's session when it claims/transitions a book (per claim/completion protocol in [book-queue.md](../book-queue.md)). Each machine writes its own row.
- The **Queue** section is owned by Asif — re-order by editing directly on develop, commit, push. Machines pick up new order on next claim.
- Cost/time estimates may drift as we learn — update the Methodology section when datapoints from new books contradict the rules of thumb.
