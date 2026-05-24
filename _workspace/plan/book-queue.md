# Book queue — single source of truth for cross-machine work assignment

**Source of truth for what each machine is working on and what's next.**
Both `mac-studio-primary` and `macbook-air-secondary` read this file on session
start and on every book transition. When a machine starts a new book, it
updates this file BEFORE doing any other work.

The queue is **pull-on-demand**, not pre-assigned. Whichever machine becomes
free first claims the top of the Queue section via the claim protocol below.
This trades a tiny amount of coord overhead for: resilience (one machine
sleeping doesn't block the other), natural load balancing, and freedom from
"which machine owns which author" bias.

## Related authority

This file is **multi-writer with claim-mutex** semantics (see
[coordination-protocol.md §14](operators/coordination-protocol.md#14-concurrency-models-for-shared-files)).
For the full discipline both machines follow (write rules, push rules,
branch policy, quota, known bugs, response conventions), read
[`operators/coordination-protocol.md`](operators/coordination-protocol.md)
once per machine on first session, then defer to that file's rules.

For the cross-machine dashboard (Air ↔ Studio current state side-by-side
+ cost/time estimates per book), see [`operators/index.md`](operators/index.md).

---

## In-flight

| Book | Slug | Machine | Branch | Phase | Started | Notes |
|---|---|---|---|---|---|---|
| Intro to Statistical Learning (ISL2) | `islr-mas-i` | `mac-studio-primary` | `book/islr-mas-i` | 0d | 2026-05-23 | Secular MAS-I textbook, non-orchestrated Mode-2 per [integration-analysis.md](../../content/drafts/islr-mas-i/_system/integration-analysis.md). EP01 shipped; ch2-7 contract authoring in progress under positive-framed math-intuition rule. |

## Paused (held by a machine but not actively driven)

| Book | Slug | Machine | Branch | Phase | Paused | Reason |
|---|---|---|---|---|---|---|
| Asaas Al-Taveel | `asaas-al-taveel` | `mac-studio-primary` | `book/asaas-al-taveel` | 0b | 2026-05-23 | HOLDING-FOR-OPERATOR-GATES — operator-review.md §§1-8 (gate b) still pending Asif. Studio pivots to ISLR ch2-7 while asaas waits on operator. Resumes when ISLR ships + gate-b cleared. 416 pages; recursive scaffold (7 nāṭiqs). |

## Queue (priority order — top = next claimed)

| # | PDF | Slug (proposed) | Pages | Size | Mode | Notes |
|---|---|---|---|---|---|---|
| 1 | `Raahat al-Aqal.pdf` | `rahat-al-aql` | 591 | 13M | scholarly_treatise | al-Kirmani's magnum opus. Pairs thematically with KaR (same author corpus, the "Repose of the Intellect" referenced 60+ times in KaR's enrichment whitelist). HIGH content value, LONG runtime. |
| 2 | `Kitab Isbath Al-Imamah.txt` | `kitab-ithbat-al-imamah` | (text) | — | pre_refined_source | Already plain text. Pre-refined source mode (SKILL.md §198): skip Phase 0a-0e, build `_notebooklm/` scaffolding only. Fast turnaround (~hours, not days). |
| 3 | `Ahed Namah for Men & Women.pdf` | `ahed-namah` | 20 | 4.0M | scholarly_treatise | Small (20 pages); quick win. Likely 1-2 episodes. |
| 4 | `MM - Anjum apa.pdf` | `mm-anjum-apa` | 17 | 13M | scholarly_treatise | Small but image-heavy (13MB / 17 pages). May need extra OCR care. |
| 5 | `Masaail - Searchable.pdf` | `masaail` | 81 | 3.2M | scholarly_treatise | Use the Searchable version (not the other Masaail.pdf which is likely a scan-only duplicate). Medium-size. |
| 6 | `Majalis Moyyada.pdf` | `majalis-moyyada` | 139 | 11M | scholarly_treatise | "Majalis" = sittings/sessions; sermon-collection register. Medium runtime. |
| 7 | `Kitab Maqbas al Akhbar al Jariyah fi Akhyar wa Ashrar - Sayedna Ali bin Sayedna Sulaiman PDF (2).pdf` | `kitab-maqbas-al-akhbar` | 392 | 236M | scholarly_treatise | Very large file (236MB / 392 pages = image-only scanned PDF). Needs extra Azure OCR time. Mid-priority on size grounds. |
| 8 | `Rasail Ikhwan AsSafa.pdf` | `rasail-ikhwan-as-safa` | 865 | 5.6M | scholarly_treatise | LONGEST in queue. The Brethren of Purity's philosophical encyclopedia. Save for when the pipeline is mature; potentially split into multiple series. |

## Completed / out-of-queue

| Book | Slug | How shipped | Notes |
|---|---|---|---|
| Ayyuhal Walad | `ayyuhal-walad` | manually (pre-pipeline) | 5 chapters + 5 episodes + transcripts already exist in library. Not re-running. |
| Kitab al-Riyad | `kitab-al-riyad` | archetype-driven manual finish + overlay-merged into develop (4e26c46) + published 2026-05-23 via `publish_to_library.py` | 15 EPs sequential EP01..EP15 (incl. EP04 chapter-group summary + EP15 book-end). SHIP-WITH-CAUTION. Distilled islamic-scholastic-text archetype v1.1 as the pivot deliverable. Library at `content/published/books/kitab-al-riyad/` (filesystem-only). |
| The Master and the Disciple | `the-master-and-the-disciple` | pre-refined source mode (in progress on coworker session) | Chapters frozen (hand-refined by Asif); `_notebooklm/` scaffolding being authored by parallel coworker session. Not in main pipeline queue. |

---

## Claim protocol

When a machine finishes a book OR starts a session with no in-flight work assigned to it:

```bash
# 1. Sync develop to see the latest queue
git fetch origin develop
git show origin/develop:_workspace/plan/book-queue.md | less

# 2. Identify the top of the Queue section. To claim it:
git checkout develop
git pull --ff-only origin develop

# 3. Edit _workspace/plan/book-queue.md:
#    - REMOVE the claimed row from "Queue"
#    - ADD a row to "In-flight" with: machine_id, branch=book/<slug>, phase=pending,
#      started=<today UTC>, your notes
# Then commit on develop directly:
git add _workspace/plan/book-queue.md
git commit -m "book-queue: claim <slug> for <machine_id>"

# 4. Push IMMEDIATELY — before doing any other work
git push origin develop

# 5. If push is rejected (non-fast-forward), the OTHER machine claimed in parallel:
git pull --rebase origin develop
# Re-read book-queue.md, the top of Queue is now different. Pick the new top and retry.
# Repeat until your claim push succeeds.

# 6. Once your claim is published, branch and start:
git checkout -b book/<slug>
# (scaffold the book per the orchestrator's --initial path or pre-refined mode per genre)
# Update your operator file's next_action.
```

The git push-rejection is the mutex. Whoever pushes the claim first wins. No locks, no servers.

## Completion protocol

When a book ships (per-chapter SHIP-READY + trainer pass + merge complete):

```bash
# 1. On develop, edit book-queue.md:
#    - REMOVE the book from "In-flight"
#    - ADD a row to "Completed" with: slug, "how shipped", brief note
git add _workspace/plan/book-queue.md
git commit -m "book-queue: ship <slug> from <machine_id>"
git push origin develop

# 2. Then call the claim protocol above to grab the next book.
```

## Priority adjustment

Asif owns queue ordering. To re-prioritize: edit the Queue section directly (move rows up/down), commit, push to develop. Machines on their next claim see the new order.

If a machine has already claimed a book that you want to deprioritize: it can pause and release the claim by moving the book back to the top of Queue with a "paused at phase X" note in its row. The next claimer can resume from that phase (`--resume <slug>`).

## Quota awareness

Anthropic API quota is shared 50/50 by `_system/cost-ledger.jsonl` accounting (when the P6.5 cost-ledger bug is fixed; until then, treat as soft 50/50).

- Two LLM-heavy phases on both machines simultaneously will throttle both. Prefer to stagger heavy phases (one machine in Phase 0g, the other in Phase 0d) when possible.
- Azure OCR + Translator (Phase 0a) has separate quotas per resource group; both machines can run 0a simultaneously without contention.
- If you observe rate-limit errors: one machine should pause its current heavy phase until the other finishes its heavy phase, then resume.

Operators (you, the human) authorize the spend per book before claiming. Per-book budget envelope is recorded in the In-flight row's notes.
