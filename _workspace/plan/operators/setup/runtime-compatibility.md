# Runtime compatibility — which UIs can drive the pipeline

The podcast pipeline has specific runtime requirements. Not every Anthropic product, not every IDE, not every AI assistant can satisfy them. This doc is the authoritative compatibility matrix and the rationale.

## TL;DR matrix

| UI | Status | Use for pipeline? | Verdict date |
|---|---|---|---|
| **Claude Code in VS Code extension** | ✅ Canonical | Yes — primary mode | (always) |
| **Claude Code desktop app** (the "Code" tab of Anthropic's unified Mac app) | ✅ Expected compatible | Yes — same harness, same tool surface | not directly probed; high confidence |
| **Claude Code CLI** (bare terminal `claude` command) | ✅ Expected compatible | Yes — same harness | not directly probed; high confidence |
| **Cowork** (the "Cowork" tab of Anthropic's unified Mac app — async project workspace) | 🔴 INCOMPATIBLE | No | verified 2026-05-21 |
| **GitHub Copilot Chat in VS Code** | ❓ Untested | Unknown — see below | n/a |
| **Claude.ai web** | 🔴 No host file access | No | (architectural) |

## Why Claude Code is canonical

The pipeline needs **ALL** of these capabilities, available together, in one persistent session on the Mac host:

1. **Live Mac shell** with access to host environment, processes, filesystem
2. **macOS Keychain access** via `security find-generic-password` (Azure credentials)
3. **Authenticated `claude -p` subprocess execution** — the orchestrator's chunked LLM calls in Phases 0b/0c/0d/0e/0g shell out from Python to the local `claude` CLI
4. **Multi-hour wall-time supervision** — Phase 0b ~1.5h, Phase 0g ~10h across 14 chapters; the assistant supervises the orchestrator process and re-resumes on `claude -p` timeout
5. **File read/edit/write** on tracked files
6. **Git operations** with push to origin (no sandbox auth boundary)
7. **Python ≥3.11** for cost-ledger + orchestrator
8. **Skill system** (`/podcast`, `/podcast-challenger`, `/extract-chapter`, etc.)
9. **Persistent memory** across sessions ([~/.claude/projects/-Users-ahmac-Code-Journal/memory/](/Users/ahmac/.claude/projects/-Users-ahmac-Code-Journal/memory/))

Claude Code on macOS — in any form factor (VS Code extension, desktop app, bare CLI) — satisfies all 9 natively. No other tested UI does.

## Cowork — verified INCOMPATIBLE (do not re-test)

Capability probe ran **2026-05-21** via a 13-step diagnostic inside a Cowork task in the "Journal" project. Cowork's bash runs in an **isolated Linux aarch64 sandbox VM**, NOT the Mac host. Hard blockers, in severity order:

1. `pwd` returns `/sessions/<random-slug>` — sandbox VM, not the Mac
2. `USER` is sandbox-named (not `ahmac`), `TERM_PROGRAM` + `CLAUDECODE` both empty
3. **No `security` binary** → no Keychain → no Azure credential resolution
4. `/usr/local/bin/claude` v2.1.142 exists in the sandbox but returns **"Not logged in"** — cannot inherit the Mac's Claude Code authentication
5. Each `mcp__workspace__bash` call is independent (~45s cap, no env carryover between calls); no mechanism to supervise a 1.5–10h orchestrator across turns. `nohup` works within one call but the process dies at VM teardown
6. Only the `dump` worktree (`/Users/ahmac/Code/Journal`) is mounted by default; live `book/<slug>` branches are invisible to Cowork even read-only
7. Sandbox Python is 3.10, below the 3.11 floor flagged in [../coordination-protocol.md §12](../coordination-protocol.md) (cost-ledger silently fails)
8. Cowork memory store lives at `…/spaces/<id>/memory/`, separate from Claude Code's `~/.claude/projects/...`; no continuity

**Architectural, not configurable.** Do not propose Cowork as a pipeline operator. The desktop-app UI being on the Mac is a UI illusion — the runtime is in a cloud sandbox.

### What Cowork CAN do here (off-pipeline)

- Adjacent content work against whatever branch is mounted (currently `dump`) — drafting prompt revisions, reviewing shipped transcripts, formatting deliverables
- One-off snapshot analyses after a phase ships and merges to `dump` or `develop`
- **NOT** live coordination, **NOT** orchestrator driving, **NOT** keychain-dependent tasks

If you want Cowork active for adjacent work, point its "On your computer" folder at a worktree where shipped output exists (or at `develop` once a book ships) — never at the live `book/<slug>` working branches.

## GitHub Copilot Chat — untested

Architectural prediction: similar issues to Cowork (no `claude -p` auth, different LLM model, VS Code-extension sandbox with limited shell semantics). But "probably" isn't "verified". To test:

Run the same 13-step diagnostic that Cowork ran, with two changes:
1. Drop the `$CLAUDECODE` check (replace with `$GITHUB_TOKEN` for Copilot scope)
2. Drop the memory-store path check (Copilot doesn't have one; verify there's no equivalent)

The full Cowork probe prompt is preserved in conversation history (2026-05-21) and can be re-issued in Copilot Chat. Update this doc with the verdict when probed.

## Second-Claude-Code-session pattern (recommended for parallel work on one Mac)

If you want **two operators on the same physical Mac**, the right pattern is to launch a second Claude Code session — not Cowork, not Copilot. Both sessions can:
- Read the same macOS Keychain
- Shell out to `claude -p` using the Mac's shared auth
- Supervise long-running processes
- Share the local memory store at `~/.claude/projects/<repo-slug>/memory/`

### Setup variant A — shared machine-id (recommended for start)

Both sessions identify as the same machine (e.g., `mac-studio-primary`). They coordinate via working-directory/branch separation:

| Session | Worktree | Branch | Role |
|---|---|---|---|
| Session A (primary) | [/Users/ahmac/Code/Journal-book-asaas](/Users/ahmac/Code/Journal-book-asaas) | `book/asaas-al-taveel` | Pipeline driver — autonomous orchestrator runs here; owns operator-file updates |
| Session B (auxiliary) | [/Users/ahmac/Code/Journal-feat-w1](/Users/ahmac/Code/Journal-feat-w1) | `feat/operator-review-studio` | Framework / UI work, read-only audits, parallel feat-branch development; does NOT touch coord docs |

Pros: minimal setup, both share `claude` auth + Keychain. Cons: only one session can update the operator file (collisions otherwise).

### Setup variant B — separate machine-ids

Each session has its own `~/.machine-id` (`mac-studio-primary` for A, `mac-studio-review` for B in a separate shell with `MACHINE_ID_OVERRIDE` env var if supported, or via separate user account). Each writes its own operator file.

Pros: full isolation, both visible in [../index.md](../index.md) dashboard. Cons: more setup, two operator files to maintain.

### Recommendation

Start with variant A. Promote to variant B if session B becomes long-lived and starts driving its own pipeline work that needs separate status reporting.

## How to add a new UI to this matrix

Run the 13-step Cowork diagnostic (preserved in conversation history 2026-05-21, or re-derive from the 9 capability requirements listed at the top of this doc) inside the candidate UI. Verdict criteria:

| All 9 capabilities pass | ✅ Compatible |
| Steps 1-3 (shell + Keychain + `claude -p`) all pass; some others fail | 🟡 Partial (probably hybrid usable for off-pipeline work) |
| Any of steps 1-3 fail | 🔴 INCOMPATIBLE for pipeline work |

Update this matrix + commit to `develop` so both machines see the change.

## Quick re-runnable probe (5 commands)

For a fast "is this UI viable?" check, run these 5 inside the candidate UI on a Mac and verify they all succeed against the Mac host (not a sandbox):

```bash
pwd                                                                              # Should be a Mac path, not /sessions/...
echo "$TERM_PROGRAM | $CLAUDECODE | $USER"                                      # Reveals UI identity + Mac user
claude -p "Reply PONG."                                                          # Anthropic auth working
security find-generic-password -s azure-journal-language-endpoint -w            # macOS Keychain reachable
python3 --version                                                                # ≥ 3.11
```

If any of those 5 fail, the UI is unsuitable for pipeline work. Run the full 13-step diagnostic for the formal verdict.
