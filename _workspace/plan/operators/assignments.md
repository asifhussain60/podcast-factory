---
schema_version: 1
last_updated: 2026-05-20
editor: operator (Asif) — single-writer per reassignment event
---

# Book → machine assignments

The single source of truth for "who owns what book." Read this **from
`origin/develop`** at the start of every session (per
[coordination-protocol.md](coordination-protocol.md) §3.3) — the copy on
your current branch may be stale.

---

## Active assignments

| Book                  | Machine                  | Branch                  | Status   | Phase | last_verified_at         |
|-----------------------|--------------------------|-------------------------|----------|-------|--------------------------|
| `asaas-al-taveel`     | `mac-studio-primary`     | `book/asaas-al-taveel`  | ACTIVE   | 0b (stale running-lock from SIGKILL) | 2026-05-20T10:00:00Z |
| `kitab-al-riyad`      | `macbook-air-secondary`  | `book/kitab-al-riyad`   | HOLDING  | 0e (pending; 0a–0d complete; operator-held for quota) | 2026-05-20T10:30:00Z |

**Status values**:
- `ACTIVE` — machine is actively running the pipeline on this book
- `HOLDING` — machine is paused at a human gate (e.g., P22 transcript review)
- `IDLE` — machine is between books, awaiting reassignment
- `BLOCKED` — machine cannot proceed; needs operator intervention

---

## Idle machines

(none — both machines are assigned)

---

## Reassignment protocol

1. Asif (or, in his explicit absence, the surviving machine under [§11](coordination-protocol.md))
   updates this file.
2. Commit on any branch where it lives; the post-commit hook auto-pushes.
3. Merge into `develop` so it propagates to every book branch on next
   `develop → book/<slug>` sync.
4. Other machines pick up the new mapping at next session-start.

---

## Reclamation log

(none yet)

When a machine reclaims a peer's book per
[coordination-protocol.md §11](coordination-protocol.md), record here:

```
- 2026-MM-DD <book> reclaimed from <dead-machine> by <surviving-machine>
  reason: <e.g., 26h heartbeat staleness + offline confirmation>
```
