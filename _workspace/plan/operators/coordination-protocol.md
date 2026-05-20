---
schema_version: 1
applies_to: all machines
edited_by: operator (Asif) only
last_updated: 2026-05-20
---

# Cross-machine coordination protocol

The discipline every machine MUST follow when it picks up work. If a rule
here conflicts with anything in a per-machine operator file, **this file
wins**.

This file is **shared reference material**. It is the same on every branch.
Asif edits it; machines read it. Never write to this file from a Claude
session unless explicitly asked.

---

## 1. Write discipline (the no-conflict rule)

The single most important invariant — break this and you will create merge
hell across branches.

- A machine writes **only** to its own `<machine-id>.md` operator file.
  Studio writes `mac-studio-primary.md`. Air writes `macbook-air-secondary.md`.
  Neither writes the other's file. Ever.
- `assignments.md` is writable by both, but only on **reassignment events**
  (a machine finishes its book, a machine crashes and gets reclaimed, a new
  book is added). Reassignments are operator-driven, so concurrent writes
  are effectively zero.
- `coordination-protocol.md` (this file) is **read-only for all machines**.

When this discipline holds, the operator files exist redundantly on every
branch but never conflict, because no two machines ever write the same file.

---

## 2. Push discipline (no orphan commits)

- Every commit that touches `_workspace/plan/operators/*` is pushed
  immediately to `origin`.
- A `post-commit` git hook is installed in the shared `.git/hooks/`
  directory of the main repo. It auto-pushes whenever those files are
  touched. The hook is installed once per physical machine.
- If the hook is missing (fresh checkout, hook disabled), the machine MUST
  run `git push` manually after every operator-file commit.

---

## 3. Session-start protocol (run before any other work)

```bash
# 3.1  Update all remote-tracking refs (does not affect working tree)
git fetch --all --prune

# 3.2  Fast-forward current branch to remote
git pull --ff-only

# 3.3  Read assignments from canonical source (always fresh from remote)
git show origin/develop:_workspace/plan/operators/assignments.md

# 3.4  Read my own operator file on current branch
cat _workspace/plan/operators/$(cat ~/.machine-id).md

# 3.5  Get authoritative phase + status from orchestrator state
jq '{phase, phase_status, last_completed_phase, last_error}' \
    content/podcast/library/books/<my-book>/_system/orchestrator-state.json
```

The session-start protocol is the only correct way to enter a session. Skip
it and you risk acting on stale state.

---

## 4. Identity detection

Each physical machine has `~/.machine-id` containing its slug (`mac-studio-primary`
or `macbook-air-secondary`). Created once per machine.

If `~/.machine-id` is missing, the Claude session MUST ask Asif before
assuming an identity. Never guess.

---

## 5. Phase / status authority

`content/podcast/library/books/<book>/_system/orchestrator-state.json` is the
**only** authoritative source for phase + status.

Operator files MUST NOT duplicate this. They may quote a `last_verified_at`
timestamp and a one-line summary, but on session start you ALWAYS re-read
the state file. The operator file's view is a snapshot for human eyes; the
state file is the truth for any decision.

---

## 6. Shared-infra zones (require operator approval before commit)

Changes to these paths can collide with the other machine's work. Coordinate
with Asif before committing here.

- `scripts/podcast/**`
- `content/podcast/.skill/handbook/**`
- `.github/agents/podcast-*.agent.md`
- `skills-staging/podcast/**`
- `_workspace/plan/podcast-plan.yaml` — canonical only on `feat/podcast-w1-foundation`

If you need to fix a bug in a shared script during a book run, prefer
`git cherry-pick` from another branch over an inline fix, so the change can
be merged consistently.

---

## 7. Sole-write zones (one machine, never the other)

- **Studio** writes `content/podcast/library/books/asaas-al-taveel/**`
- **Air** writes `content/podcast/library/books/kitab-al-riyad/**`
- Neither writes into the other's book directory or onto the other's
  book branch (`book/<slug>`).
- See `assignments.md` for the current book → machine mapping.

---

## 8. Quota policy

| Resource             | Phase that uses it | Sharing                                                             |
|----------------------|--------------------|---------------------------------------------------------------------|
| Azure OCR            | 0a only            | Stagger 0a starts if both books need ingest in same 24h window      |
| Azure Translator     | 0a only            | Same caveat. Transient `ConnectionRefused` — retry once             |
| Anthropic via claude -p | 0b/0c/0d/0e + per-chapter | Shared monthly quota. Each machine caps at `anthropic_share` from its operator file. Default 0.5 each |
| Anthropic SDK        | cost-ledger token counting | Minimal — not user-facing                                    |

The cost ledger (`_system/cost-ledger.jsonl`) may silently fail on Python
< 3.11 (P6.5 datetime.UTC bug). Phases run anyway; ignore for now.

---

## 9. Branch policy

| Branch                       | Purpose                                  | Direct commits? |
|------------------------------|------------------------------------------|-----------------|
| `main`                       | shipped to GitHub Pages                  | No — protected  |
| `develop`                    | integration; canonical operator files    | Yes (operator)  |
| `feat/podcast-w1-foundation` | canonical `_workspace/plan/**`; orchestrator features | Yes |
| `book/<slug>`                | per-book working branch (one machine)    | Yes (assigned machine only) |

Merge direction:
```
feat/podcast-w1-foundation ──┐
                              ├──► develop ──► main
book/<slug> ──────────────────┘   (book → develop after book ships)
```

Always pull `develop` into a book branch before merging book → develop, to
keep the merge fast-forwardable.

---

## 10. Pause-and-handoff protocol

When you finish a phase or hit a natural pause, every machine MUST:

1. Run session-start protocol step 5 (read fresh state from state file).
2. Update **your own** operator file's frontmatter:
   - `last_verified_at` → now (ISO 8601 UTC)
   - `current_phase` → from state file
   - `current_phase_status_summary` → one-line human summary
   - `next_action` → what the next session should do first
   - `status_tag` → one of `ACTIVE`, `HOLDING`, `IDLE`, `BLOCKED`
3. Commit with message: `coord(<machine-id>): update operator state @ phase <X>`
4. The post-commit hook auto-pushes. If it doesn't, push manually.
5. Write a `## Project Status` block back to Asif (his convention — see
   per-machine operator file).

---

## 11. Reclamation (machine crash)

If a machine dies mid-phase, its operator file's `last_verified_at` will go
stale and its assigned book's `orchestrator-state.json` will show
`phase_status=running` indefinitely.

The surviving machine MAY reclaim the dead machine's book ONLY when:

1. The dead machine's `last_verified_at` is > 24h stale, **AND**
2. The dead machine is confirmed unreachable (Asif confirms, or repeated
   network checks fail), **AND**
3. Asif approves the reclamation.

To reclaim:
1. Edit `assignments.md`: move the book to the surviving machine; add a
   `reclaimed_from: <dead-machine>` note and `reclaimed_at: <ISO>`.
2. Reset the stale running-lock on the book's `orchestrator-state.json`
   (`phase_status: running` → `failed`) and commit on the book branch.
3. Resume.

---

## 12. Known orchestrator bugs (apply on any machine)

1. **1200s `claude -p` LLM timeout** (phases 0b/0c/0d). Shell-out dies after
   ~4–5 work units; just `--resume` and it advances another 4–5.
2. **Cost-ledger `datetime.UTC` AttributeError** on Python < 3.11. Every
   `claude -p` invocation silently fails the ledger append. Tracked as P6.5.
   Phases run regardless — ignore.
3. **Stale `phase_status=running` after unclean shutdown**. Flip to `failed`
   manually before `--resume`. Real fix needs heartbeat-age check (P5.x).
4. **Phase 0d source-toc fasl counts may be off-by-one** (e.g., KaR Bāb 10
   declared 16 fusūl, actual 15). Small discrepancies are fine.
5. **Azure Translator transient `ConnectionRefused`** in phase 0a. Retry once
   via `--retry-phase 0a` (wired by commit `9f0f277`). Persistent failure →
   check Azure quota in the portal.

---

## 13. Asif's collaboration conventions (apply in every response)

1. **`## Project Status` block at end of every response** — mandatory
   **Work Completed** + **Work Pending** sub-sections; optional Blockers /
   Next Action / Decisions Needed / Risks / Verdict.
2. **AskUserQuestion ordering**: recommended option first, labeled
   "(Recommended)"; remaining options ordered priority highest→lowest.
3. **Asif IS Babu** (the memoir's protagonist). Relevant only if memoir
   context comes up; not relevant to podcast work.
4. Terse responses; file:line refs; harness-side confirmation for risky
   actions (force pushes, branch deletions, `rm -rf`).
