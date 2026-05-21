---
schema_version: 2
last_updated: 2026-05-21
editor: operator (Asif) for queue order; either machine for In-flight/Completed transitions via claim/completion protocol
---

# Book → machine assignments (v2 — superseded by book-queue.md)

> **As of 2026-05-21, this file is INFORMATIONAL ONLY.** The authoritative
> single source of truth for cross-machine work assignment has moved to
> [`_workspace/plan/book-queue.md`](../book-queue.md), which uses a
> **pull-on-demand claim protocol** rather than the v1 static assignment
> model. Machines claim books from the Queue section by editing the queue
> file on develop and pushing immediately (push-rejection is the mutex).
>
> Read `book-queue.md` from `origin/develop` at the start of every session
> to know what's in-flight, what's queued, and what claim protocol to use.

## Why the change

The static-assignment model in v1 bakes in failure modes — if one machine
is asleep or unavailable, the books assigned to it idle until that machine
returns. The pull-on-demand model lets either machine claim the next book
when free, giving:

- **Resilience**: Air can sleep without blocking Studio
- **Natural load balancing**: faster-finishing machine grabs next slot
- **No author bias**: queue order is Asif's call, not "Studio always does X"
- **Race-safety**: git push-rejection serializes claims deterministically

The two operator files (`macbook-air-secondary.md`, `mac-studio-primary.md`)
are unchanged — they still describe each machine's CURRENT state. The book
queue describes the WORK pipeline. Different concepts.

---

## Current state (as of 2026-05-21, mirrors book-queue.md)

| Book | Machine | Branch | Status | Phase |
|---|---|---|---|---|
| `asaas-al-taveel` | `mac-studio-primary` | `book/asaas-al-taveel` | IN-FLIGHT | 0c |
| `kitab-al-riyad` | `macbook-air-secondary` | `book/kitab-al-riyad` | IN-FLIGHT | 0f-halt (awaiting 0g go-ahead) |
| 8 books queued | — | — | QUEUED | pending claim |

For the full queue and per-book notes, see [book-queue.md](../book-queue.md).

---

## Claim and completion protocols

See [book-queue.md](../book-queue.md) — both protocols (claim a book,
ship a book) are defined there with copy-pasteable bash recipes.

---

## Reclamation log (v1 holdover — still relevant)

(none yet)

When a machine reclaims a peer's book per
[coordination-protocol.md §11](coordination-protocol.md), record here:

```
- 2026-MM-DD <book> reclaimed from <dead-machine> by <surviving-machine>
  reason: <e.g., 26h heartbeat staleness + offline confirmation>
```
