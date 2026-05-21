---
schema_version: 2
applies_to: all machines
edited_by: operator (Asif) only
last_updated: 2026-05-21
---

# Cross-machine coordination protocol (v2 — 2026-05-21)

The discipline every machine MUST follow when it picks up work. If a rule
here conflicts with anything in a per-machine operator file, **this file
wins**. If a rule here conflicts with `response-conventions.md`, that file
wins for response format only; this file wins on everything else.

This file is **shared reference material**. It is the same on every branch.
Asif edits it; machines read it. Never write to this file from a Claude
session unless explicitly asked.

### v2 changes (2026-05-21)
- §3 session-start: prefer `start-session.sh` over manual bash recipe
- §7 sole-write zones: queue-driven instead of hardcoded book→machine
- §10 pause-and-handoff: end-of-response format references `response-conventions.md`
- §13 conventions: full spec moved to `response-conventions.md`; this file links
- §14 (NEW) — concurrency models for sole-write vs shared-write files
- §15 (NEW) — write-exception protocol (one machine writes peer's operator file)

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

**Preferred — run the script:**

```bash
bash _workspace/plan/operators/start-session.sh
```

The script: identifies your machine via `~/.machine-id`, syncs develop,
reads your operator file from develop (the freshest copy), switches to
your assigned book branch, prints orchestrator state + next_action.

Exit codes:
- `0` — ready (sitting on the right branch with a known next step)
- `1` — pre-flight failed (dirty tree / missing machine-id) — fix and re-run
- `2` — IDLE (no assigned book — claim one per `book-queue.md`)

**Manual fallback** (if the script is broken or missing):

```bash
# 3.1  Update remote-tracking refs (does not affect working tree)
git fetch --all --prune

# 3.2  Fast-forward current branch to remote
git pull --ff-only

# 3.3  Read the dashboard (cross-machine state)
git show origin/develop:_workspace/plan/operators/index.md

# 3.4  Read your own operator file
cat _workspace/plan/operators/$(cat ~/.machine-id).md

# 3.5  Read the queue (only if you're IDLE)
git show origin/develop:_workspace/plan/book-queue.md

# 3.6  Get authoritative phase + status from orchestrator state
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

**The book-to-machine mapping is dynamic — it lives in `../book-queue.md`'s
"In-flight" section, not hardcoded here.** A machine writes only to
`content/podcast/library/books/<book>/**` for the book(s) listed as
in-flight against its own machine_id. Symmetric rule applies to book
branches (`book/<slug>`).

The claim protocol in `book-queue.md` ensures only one machine claims a
book at a time (git push-rejection mutex). Once claimed, the sole-write
discipline kicks in.

**Current snapshot (mirror of `book-queue.md` In-flight section as of
2026-05-21):**
- `mac-studio-primary` → `book/asaas-al-taveel`
- `macbook-air-secondary` → `book/kitab-al-riyad`

This snapshot is illustrative; `book-queue.md` is canonical.

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

## 9. Branch policy + worktree guidance

### Branches

| Branch                       | Purpose                                  | Direct commits? |
|------------------------------|------------------------------------------|-----------------|
| `main`                       | shipped to GitHub Pages                  | No — protected  |
| `develop`                    | integration; accumulates every shipped book + framework upgrades | Yes (any machine, via book→develop merges) |
| `feat/podcast-w1-foundation` | canonical `_workspace/plan/**`; orchestrator features | Yes (rarely active; merges to develop when meaningful work lands) |
| `book/<slug>`                | per-book working branch (one machine)    | Yes (assigned machine only) |

Merge direction:
```
feat/podcast-w1-foundation ──┐
                              ├──► develop ──► main
book/<slug> ──────────────────┘   (book → develop after book ships)
```

Always pull `develop` into a book branch before merging book → develop, to
keep the merge fast-forwardable. The standard pattern is:

```bash
git checkout book/<slug>
git pull --ff-only origin book/<slug>
git merge --no-ff origin/develop          # bring develop's framework upgrades onto your book branch
# ... do your work ...
git push origin book/<slug>
git checkout develop
git pull --ff-only origin develop
git merge --no-ff book/<slug>             # ship the book's work to develop
git push origin develop
git checkout book/<slug>                  # back to your lane
```

### Worktrees — single-worktree-per-machine recommended

One git repo, one working directory per physical machine. Each machine's
single worktree switches between branches as needed (the `book/<slug>` your
machine owns most of the time; `develop` only during the periodic merge
dance above).

`git worktree` lets you have a second working directory on a different
branch, but for this project's branch-per-book model that adds visual
sprawl without benefit (you'll see two `journal` folders on the machine
and wonder which is real — they share the same `.git/`). If you find a
dormant worktree (its branch is 0 commits ahead of develop), prune it:

```bash
cd <primary worktree>
git worktree remove <dormant worktree path>
```

The branch survives; you can check it out in the primary worktree if needed.

---

## 10. Pause-and-handoff protocol

When you finish a phase or hit a natural pause, every machine MUST:

1. Re-read state file (`jq '...' state.json`) for the truth.
2. Update **your own** operator file's frontmatter:
   - `last_verified_at` → now (ISO 8601 UTC)
   - `current_phase` → from state file
   - `current_phase_status_summary` → one-line human summary
   - `next_action` → what the next session should do first
   - `status_tag` → one of `ACTIVE`, `HOLDING-AT-<gate>`, `IDLE`, `BLOCKED`
3. If you transitioned a book (started, paused, finished): also update
   `_workspace/plan/book-queue.md` per the claim/completion protocol there.
4. If you finished work that should be shared across both machines: update
   `_workspace/plan/operators/index.md` (your own row in the Machine Status
   table).
5. Commit with message: `coord(<machine-id>): update operator state @ phase <X>`
6. Push immediately to origin. If a `post-commit` hook is installed, it
   auto-pushes; otherwise push manually.
7. Write a response to Asif following `_workspace/plan/response-conventions.md`
   (BLUF format: TL;DR, Status emoji, Body, Your next step). No custom
   section labels.

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

## 13. Response conventions (in every response Asif sees)

Full spec: [`../response-conventions.md`](../response-conventions.md).

Highlights both machines follow without exception:

1. **BLUF format** — every substantive response uses this **5-part shape, in order**:
   1. `**TL;DR:**` (one sentence, plain English)
   2. `**Status:**` 🟢 / 🟡 / 🔴
   3. **Body** — `### N. <name> <emoji>` numbered blocks (*Plain English*/*Impact*/*Fix*/*Where* bullets) OR tables. **No custom section labels** ("Deviation from plan", "Verification", "Coord doc", "What changed", etc.).
   4. `**Your next step:**` (one explicit sentence)
   5. `---` + `## Summary (scan-and-skip)` ordered list — one line per body section, final item `**Next step:**`-prefixed; clickable links preserved so Asif can act from the Summary without scrolling
2. **AskUserQuestion ordering**: recommended option first, labeled
   "(Recommended)"; remaining options ordered priority highest→lowest.
3. **Asif IS Babu** (the memoir's protagonist). Relevant only if memoir
   context comes up; not relevant to podcast work.
4. Terse responses; clickable markdown links for files/commits (`[name](path)`,
   `[short-sha](github-url)`); harness-side confirmation for risky actions
   (force pushes, branch deletions, `rm -rf`).

---

## 14. Concurrency models for shared files

Two distinct patterns are in play; do not confuse them.

| Pattern | Files | How writes are serialized |
|---|---|---|
| **Sole-write** | `mac-studio-primary.md`, `macbook-air-secondary.md` (each owned by the named machine) | Convention. Only the named machine writes. Coupled with the WRITE EXCEPTION protocol in §15 for one-time cross-writes. |
| **Multi-writer with claim-mutex** | `../book-queue.md`, `index.md` (machine-status rows) | Each machine edits → commits → pushes immediately. Git push-rejection serializes claims: whoever pushes first wins. Loser pulls/rebases and retries. |
| **Read-only for machines** | `coordination-protocol.md`, `README.md`, `start-session.sh`, `assignments.md` | Only Asif edits (typically on develop). Machines read. |

When a multi-writer file conflicts on merge, the conflict is resolved by
re-reading the latest state from origin/develop and re-applying your change
on top — never overwrite the other machine's claim.

---

## 15. WRITE EXCEPTION protocol (one machine writes peer's operator file)

By default, machines NEVER write the other machine's operator file. The
exception: Asif may explicitly authorize a one-time cross-write (e.g.,
to seed a new machine's operator file, or to record cross-machine sync
state when the peer machine is unavailable).

When this happens:

1. The writing machine adds a `written_by:` field to the frontmatter,
   naming itself and citing "one-time exception per Asif's explicit
   instruction" with the date.
2. The writing machine adds an inline `> ⚠️ **WRITE EXCEPTION — <date>**`
   blockquote at the top of the body explaining what was written and why.
3. The blockquote MUST instruct the file's owning machine to re-assert
   ownership on its next session (drop the WRITE EXCEPTION block, refresh
   frontmatter from its own observed state).
4. On the owning machine's next session: it reads the WRITE EXCEPTION,
   reconciles the contents (typically: keeps cross-machine sync notes,
   refreshes its own state-fields), removes the block, commits as
   `coord(<machine-id>): re-assert ownership after <date> write exception`.

Cycle: ownership returns to the named owner; cross-machine sync is preserved.
