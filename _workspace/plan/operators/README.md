# `_workspace/plan/operators/` — cross-machine coordination zone

The state, protocol, and per-machine resume files that let multiple Claude
sessions on multiple physical machines work the podcast pipeline
autonomously without stepping on each other.

## How to start a session (run this first, every time)

**Auto-orientation files at repo root mean new chat sessions in either
Claude Code or VSCode Copilot are oriented to this folder automatically:**

- `CLAUDE.md` (repo root) — auto-loaded by Claude Code on every session
- `.github/copilot-instructions.md` — auto-loaded by VSCode Copilot Chat

Both files instruct the session to:

```bash
bash _workspace/plan/operators/start-session.sh
```

That script reads your `~/.machine-id`, pulls develop, switches to your
assigned book branch, prints orchestrator state + next_action, exits 0
if ready / 2 if you're IDLE (in which case it points you at the claim
protocol in `book-queue.md`).

If `start-session.sh` is missing or you need the manual equivalent, see
[coordination-protocol.md §3](coordination-protocol.md#3-session-start-protocol-run-before-any-other-work).

## Files in this folder

| File                            | Writer                | Readers     | Purpose                                                                  |
|---------------------------------|-----------------------|-------------|--------------------------------------------------------------------------|
| [start-session.sh](start-session.sh) | operator (Asif) — rarely edited | all machines run it | Per-machine session bootstrap. Executable from any branch. |
| [index.md](index.md)            | machines (each writes its own row) + operator (queue ordering) | all machines | Cross-machine dashboard: Mac Air ↔ Mac Studio side-by-side current state + cost/time estimates per queued book. |
| [coordination-protocol.md](coordination-protocol.md) | operator (Asif) | all machines | The discipline — write rules, push rules, branch policy, quota, sole-write zones, known bugs, conventions. **Wins over per-machine files when in conflict.** |
| [mac-studio-primary.md](mac-studio-primary.md) | Mac Studio only | all machines | Studio's identity, current book, resume action, peer pointer. |
| [macbook-air-secondary.md](macbook-air-secondary.md) | MacBook Air only | all machines | Air's identity, current book, resume action, peer pointer. |
| [assignments.md](assignments.md) | (vestigial — see file) | (read for history only) | Pre-v3 static assignment model. Marked informational-only; superseded by `../book-queue.md`. |
| [setup/](setup/) folder | either machine | all machines | **Setup + recreate-from-scratch reference**: per-machine config ([setup/machines.md](setup/machines.md)), Azure stack ([setup/azure-stack.md](setup/azure-stack.md)), new-Mac bootstrap ([setup/recreate-from-scratch.md](setup/recreate-from-scratch.md)), runtime compatibility / Cowork verdict / second-Claude-session pattern ([setup/runtime-compatibility.md](setup/runtime-compatibility.md)). Index at [setup/README.md](setup/README.md). |

## Related files in `../` (one directory up)

| File                            | Writer                | Purpose                                                                  |
|---------------------------------|-----------------------|--------------------------------------------------------------------------|
| `../book-queue.md`              | machines (claim-protocol) + operator (queue ordering) | Pull-on-demand work queue. The single source of truth for "what is being worked on and what's next." |
| `../response-conventions.md`    | operator (Asif)       | The BLUF response format both Air and Studio sessions follow. Read once per session. |

## Reading order on session start (post-script)

1. `start-session.sh` output (it reads files 2-4 for you)
2. `index.md` — quick scan of both machines' current state
3. `../book-queue.md` — only if you need to know what's queued or claim something
4. `coordination-protocol.md` — only on first session per machine, or when you change conventions
5. `<your-machine-id>.md` — your own operator file (frontmatter `next_action` is what to do)
6. `content/drafts/<your-book>/_system/orchestrator-state.json` — authoritative phase/status (script already shows this)

If files 2-5 disagree with file 6, **trust file 6** (the state file is truth; operator files are snapshots). Update operator file to match, commit.

## Adding a new machine

1. Pick a slug (`<role>-<location>`, e.g. `macbook-pro-asif-home`).
2. On the new physical machine: `echo <slug> > ~/.machine-id`.
3. Create `<slug>.md` here from one of the existing operator files as template (copy `macbook-air-secondary.md` and edit frontmatter).
4. Commit on develop; merge to every active book branch via the standard merge pattern.
5. On the new machine, run `start-session.sh`. Expected exit code: 2 (IDLE — claim a book from `../book-queue.md`).

## Why this lives at `_workspace/plan/operators/` and not `_workspace/operators/`

Historical: the coordination protocol was authored when operator files sat
alongside the plan. Many cross-references already hardcode this path. The
*content* is cross-machine coordination, not plan content, but the *path* is
stable. Future move (to `_workspace/operators/`) would touch every reference
and is not worth the churn unless we promote `_workspace/plan/` itself.
