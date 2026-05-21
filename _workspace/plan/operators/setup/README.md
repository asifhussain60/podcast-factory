# Operator setup — index

Canonical reference for **how each operator machine is configured** and **how to rebuild from scratch**. Both [mac-studio-primary.md](../mac-studio-primary.md) and [macbook-air-secondary.md](../macbook-air-secondary.md) reference this folder.

## When to read what

| Situation | Read this |
|---|---|
| "What's installed on each machine? Where are the worktrees? Which macOS user?" | [machines.md](machines.md) |
| "Azure resources, keychain entries, recreate Azure from blank account" | [azure-stack.md](azure-stack.md) |
| "Setting up a brand-new Mac (blank macOS → working operator)" | [recreate-from-scratch.md](recreate-from-scratch.md) |
| "Which UIs can drive the pipeline? Why doesn't Cowork work? Second-Claude-session pattern?" | [runtime-compatibility.md](runtime-compatibility.md) |
| "Cross-machine coordination rules (sole-write, push, branch policy, quota)" | [../coordination-protocol.md](../coordination-protocol.md) |
| "Pull-on-demand work queue and claim mutex" | [../book-queue.md](../book-queue.md) |
| "Live machine-status dashboard" | [../index.md](../index.md) |

## Source-of-truth split

| Concern | Where |
|---|---|
| Recreation + machine config | This folder (`setup/`) |
| Cross-machine discipline | [../coordination-protocol.md](../coordination-protocol.md) |
| Work assignment | [../book-queue.md](../book-queue.md) |
| Live dashboard | [../index.md](../index.md) |
| Per-machine resume state | [../mac-studio-primary.md](../mac-studio-primary.md), [../macbook-air-secondary.md](../macbook-air-secondary.md) |
| Response format | [../../response-conventions.md](../../response-conventions.md) |

The operator files keep ephemeral "what's happening right now" state; the `setup/` docs keep stable "how the machine is wired" knowledge.

## Update discipline

These docs change when reality changes — new Azure resource, new worktree, new physical machine, new runtime UI proven/disproven.

- Either machine may update them (multi-writer with claim-mutex pattern per [../coordination-protocol.md §14](../coordination-protocol.md)).
- Commit message convention: `coord(setup): <file> updated for <change>`.
- Merge to `develop` reasonably aggressively (don't wait for a full book ship) so the peer machine sees the update on its next session-start sync.

## Where the executable scripts live

This folder is documentation only. The actual bootstrap automation lives at:

- [../../../../infra/azure/](../../../../infra/azure/) — Azure provisioning, key extraction, verification, Key Vault migration
- [../../../../infra/claude-agents/](../../../../infra/claude-agents/) — Claude Code agent specs
- [../../../../infra/launchd/](../../../../infra/launchd/) — macOS launchd jobs for scheduled work
- [../start-session.sh](../start-session.sh) — per-session bootstrap (reads `~/.machine-id`, syncs branch, prints next action)

When in doubt about "what command actually runs", check those folders first. The docs here describe what the scripts DO and when to invoke them.
