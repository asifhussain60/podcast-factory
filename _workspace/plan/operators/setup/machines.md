# Per-machine configuration

Both operator machines run the same project but with **different macOS users, different paths, and different worktree counts**. This doc is the source of truth for "what's installed and where" on each.

## Cross-cutting facts (same on every operator Mac)

- macOS Big Sur or later (verified on Darwin 24+ on Studio)
- ONE git repo: `git@github.com:asifhussain60/Journal.git`
- ONE primary working directory per machine; optional additional worktrees for parallel branch work (see [../coordination-protocol.md §9](../coordination-protocol.md))
- `~/.machine-id` file holds the identity slug (`mac-studio-primary`, `macbook-air-secondary`, or future `<role>-<location>`)
- `claude` CLI authenticated per-machine via `claude login` (auth is local, not shared across machines)
- macOS Keychain holds all secrets (Azure keys, etc.); naming convention `azure-<app>-<resource>-<field>` per [azure-stack.md](azure-stack.md)
- [../start-session.sh](../start-session.sh) is the per-session bootstrap — reads `~/.machine-id`, syncs `develop`, switches to assigned branch, prints next action
- Post-commit hook at `.git/hooks/post-commit` auto-pushes commits that touch `_workspace/plan/operators/*` — see [../coordination-protocol.md §2](../coordination-protocol.md)

## Mac Studio — `mac-studio-primary`

| Attribute | Value |
|---|---|
| Identity file | `~/.machine-id` → `mac-studio-primary` |
| Hostname hint | `Asifs-Mac-Studio.local` |
| macOS user | `ahmac` |
| Home directory | `/Users/ahmac` |
| Primary worktree | `/Users/ahmac/Code/podcast-factory/worktrees/book-asaas` — branch `book/asaas-al-taveel` (Option 2 layout 2026-05-22; container-parent at `podcast-factory/`, repo + worktrees grouped under `worktrees/`) |
| Additional worktrees | `worktrees/main` (`develop`, integration target), `worktrees/book-islr` (`book/islr-mas-i`), `worktrees/book-kar` (`book/kitab-al-riyad` — checked out after the 2026-05-22 KaR ownership transfer, then transferred back to Air same day), `worktrees/feat-w1` (`feat/operator-review-studio` — RETIRED 2026-05-22 when the branch was merged + deleted; remove from disk if still present) |
| Role | Primary — designated for autonomous Azure-backed podcast-pipeline runs (per memory `project_primary_mac.md`, 2026-05-18) |
| Anthropic quota share | 0.5 |
| Currently in-flight | `book/asaas-al-taveel` (Phase 0b halted, awaiting operator gate (b)) |
| Operator file | [../mac-studio-primary.md](../mac-studio-primary.md) |

**Note on Studio's three worktrees:** [../coordination-protocol.md §9](../coordination-protocol.md) recommends single-worktree-per-machine for branch-per-book workflows. Studio currently runs three because [feat/operator-review-studio](/Users/ahmac/Code/podcast-factory/feat-w1) is actively being developed in parallel with the asaas pipeline work. The `dump` worktree is essentially a local stash and could be pruned if not needed. Consolidation is at the operator's discretion — see [runtime-compatibility.md](runtime-compatibility.md) for the "two Claude Code sessions on one Mac" pattern which actually benefits from this layout.

## MacBook Air — `macbook-air-secondary`

| Attribute | Value |
|---|---|
| Identity file | `~/.machine-id` → `macbook-air-secondary` |
| Hostname hint | `Asifs-MacBook-Air.local` |
| macOS user | `asifhussain` |
| Home directory | `/Users/asifhussain` |
| Primary worktree | `/Users/asifhussain/PROJECTS/podcast-factory/worktrees/book-kar` — branch `book/kitab-al-riyad` (Option 2 layout 2026-05-22) |
| Additional worktrees | `worktrees/main` (`develop`), `worktrees/book-asaas` (`book/asaas-al-taveel`), `worktrees/book-islr` (`book/islr-mas-i`) — all under `/Users/asifhussain/PROJECTS/podcast-factory/` |
| Role | Secondary — currently driving `book/kitab-al-riyad`; flexes to other books per claim protocol in [../book-queue.md](../book-queue.md) |
| Anthropic quota share | 0.5 |
| Currently in-flight | `book/kitab-al-riyad` (Phase 0g per-chapter — EP10 shipped SHIP-WITH-CAUTION, EP14 in flight after X3/X4 fixes) |
| Operator file | [../macbook-air-secondary.md](../macbook-air-secondary.md) |

## What is THE SAME across machines

- Repo URL and all branches
- [../coordination-protocol.md](../coordination-protocol.md) (read-only for both)
- [../../../../infra/azure/azure-config.env](../../../../infra/azure/azure-config.env) — subscription, region, resource names, feature flags
- Keychain naming convention (per [azure-stack.md](azure-stack.md))
- Skill specs in [.github/agents/](../../../../.github/agents/) and [skills-staging/](../../../../skills-staging/)
- Memory directory naming pattern (each Mac has its own `~/.claude/projects/<slug>/memory/`)

## What is DIFFERENT across machines

| Dimension | Studio | Air |
|---|---|---|
| macOS user | `ahmac` | `asifhussain` |
| Home path | `/Users/ahmac` | `/Users/asifhussain` |
| Primary worktree path | `/Users/ahmac/Code/podcast-factory/worktrees/book-asaas` | `/Users/asifhussain/PROJECTS/podcast-factory/worktrees/book-kar` |
| Worktree count | 4 (main + book-asaas + book-islr + book-kar; feat-w1 retired 2026-05-22) | 4 (main + book-asaas + book-islr + book-kar) |
| Currently assigned book branch | `book/asaas-al-taveel` | `book/kitab-al-riyad` |
| `claude` auth | separate session (logged in as `ahmac`) | separate session (logged in as `asifhussain`) |
| Memory directory | `~/.claude/projects/-Users-ahmac-Code-Journal/memory/` | `~/.claude/projects/-Users-asifhussain-PROJECTS-journal/memory/` |

## Why these specific paths and not one convention?

The two machines were set up independently at different times, with different macOS users (a personal account on Air, a dedicated `ahmac` account on Studio for the AI work). Standardizing the paths would require re-cloning + re-creating worktrees + updating absolute paths in operator files. The cost is real (commits in each operator file reference absolute paths; renaming touches everything). For now: tolerated divergence, documented here.

If a future Mac is added: pick whatever path makes sense for that Mac's user; just record it in this doc + the new machine's operator file frontmatter `worktree_layout` field. The pipeline code uses repo-relative paths internally.

## Where to update this doc

When physical setup changes (new worktree added, machine wiped, user account changed, new Mac onboarded), update this doc + the relevant operator file's `worktree_layout` frontmatter + commit to `develop` (don't wait for a book ship). The other machine will see the change on its next `start-session.sh` sync.
