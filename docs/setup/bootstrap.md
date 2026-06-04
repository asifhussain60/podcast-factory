# From-scratch operator setup — blank Mac → working session

Use this procedure when:
- Setting up a new Mac (or a fresh user account) to run `podcast-factory`
- Rebuilding after a wipe / reinstall

Walks from blank macOS to a Claude Code session that runs `scripts/start-session.sh` cleanly. The repo is single-machine (machine-agnostic since 2026-05-23); there is no operator file to author, no `~/.machine-id` to set, no `book-queue.md` to claim from. Just clone, install dependencies, wire Azure, and start work.

## Prerequisites

- macOS (any recent version; tested on Darwin 24+)
- A GitHub account with read/push access to [asifhussain60/podcast-factory](https://github.com/asifhussain60/podcast-factory)
- (If this Mac will drive Azure pipeline phases) An Azure account with read access to the `Journal AI — primary` subscription

## Step 1 — Install command-line tools

```bash
xcode-select --install
git --version    # Confirm git is available
```

## Step 2 — Install Homebrew + project dependencies

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required:
brew install python@3.11 jq azure-cli gh
# Recommended:
brew install ripgrep fd

# Verify:
python3 --version    # Must be ≥ 3.11 (cost-ledger silently fails on <3.11)
jq --version
az --version
gh --version
```

## Step 3 — Install Claude Code

```bash
# Either Homebrew:
brew install --cask claude-code
# Or Anthropic's official installer per https://claude.com/claude-code

# Authenticate:
claude login
# Follow the OAuth flow in browser. Auth is local to this Mac.
```

## Step 4 — Clone the repo

```bash
mkdir -p ~/PROJECTS && cd ~/PROJECTS
gh repo clone asifhussain60/podcast-factory
cd podcast-factory
git status              # Should be clean, on `develop`
git log --oneline -5    # Sanity-check recent history
```

The repo is flat (no worktrees container). Books in flight live under [`content/drafts/<slug>/`](../../content/drafts/); shipped books live under [`content/published/books/<slug>/`](../../content/published/books/).

## Step 4.5 — Install git hooks and Claude skills

```bash
cd ~/PROJECTS/podcast-factory

# Enforce DR-009 (no version markers) + HTML-view quality gate on every commit:
bash scripts/install-git-hooks.sh

# Install Claude agent specs into .claude/agents/ (required for orchestrator, challenger, etc.):
bash scripts/install-claude-skills.sh
```

Both scripts are idempotent — safe to re-run after pulling new hook or skill versions.

## Step 5 — Wire Azure credentials (ONLY if this Mac drives pipeline phases)

All credentials are stored in Azure Key Vault (`podcast-factory-vault`). A single command pulls everything into the local Keychain.

```bash
cd ~/PROJECTS/podcast-factory/infra/azure
az login
az account set --subscription "Journal AI — primary"
bash pull-secrets.sh
```

`pull-secrets.sh` pulls all 14+ secrets (Translator, Document Intelligence, Speech, Storage, Gemini, Anthropic keys) from Key Vault into the local Keychain, then runs the connectivity test automatically.

Expect the script to end with `pass 5  fail 0  ✓ Azure connectivity OK`.

**First-time Azure provisioning only** (blank Azure subscription — not a new Mac):
```bash
bash provision-azure.sh          # Creates all Azure resources
bash store-keychain-keys.sh      # Local Keychain ← Azure
bash migrate-to-keyvault.sh      # Key Vault ← local Keychain
```

Full reference: [docs/setup/azure-stack.md](azure-stack.md).

## Step 5.5 — Wire LLM APIs (Claude + Gemini)

Anthropic Claude runs off the Max subscription (no API key needed on operator Macs — `claude login` in Step 3 covers it). Google Gemini and the Anthropic API key are already included in the Key Vault pull from Step 5.

Verify both providers:

```bash
cd ~/PROJECTS/podcast-factory
bash infra/llm-apis/verify-llm-apis.sh
```

Full reference: [infra/llm-apis/README.md](../../infra/llm-apis/README.md).

## Step 5.7 — Set up the source library database (local knowledge corpus)

The source library server needs a local SQL Server container with three databases (Quran, topics, sessions). Run once per machine:

```bash
# Prerequisite: Docker runtime running (OrbStack recommended)
brew install orbstack   # if not already installed
open -a OrbStack        # complete setup, pick Docker

# SQL dump files must be present (they are gitignored — copy from another machine
# or re-export from the home server at 192.168.1.158 if needed):
#   CONTENT/_shared/source-library/KQur.sql       (~15 MB)
#   CONTENT/_shared/source-library/KSessions.sql  (~29 MB)
#   CONTENT/_shared/source-library/Kashkole.sql   (~724 MB)

cd ~/PROJECTS/podcast-factory
bash infra/setup-wisdom-db.sh   # ~3-5 min on first run; idempotent on re-runs
```

After the script completes, register the MCP server so Claude Code can call it:

```bash
python3 scripts/podcast/source_library_server.py --register
```

## Step 6 — Run the session-starter

```bash
cd ~/PROJECTS/podcast-factory
bash scripts/start-session.sh
```

Exit codes:
- `0` — ready (on `develop`, fetched, fast-forwarded, no dirty tree)
- `1` — pre-flight failed (dirty tree, or not in a git repo)

Output lists current books in flight and the most common next-action commands. You're now set up.

## What this Mac does NOT need anymore

The pre-2026-05-23 setup required all of the following — none of which apply now:

- ❌ `~/.machine-id` (single-machine; no machine identity needed)
- ❌ `_workspace/plan/operators/<slug>.md` (operator files retired)
- ❌ `.git/hooks/post-commit` for operator-file auto-push (no operator files)
- ❌ `book-queue.md` mutex (single-machine; no queue contention)
- ❌ A `coordination-protocol.md` file (retired with the multi-machine model)

If you see references to any of these in older docs, treat them as historical and follow [CLAUDE.md](../../CLAUDE.md) instead.

## Where to look next

- [CLAUDE.md](../../CLAUDE.md) — the project's standing brief; auto-loaded into every Claude Code session in this repo
- [framework.md](../../framework.md) — the pipeline framework spec
- [_workspace/setup/azure-stack.md](azure-stack.md) — full Azure resource reference + recreate-from-scratch
- [infra/llm-apis/README.md](../../infra/llm-apis/README.md) — Anthropic + Google API accounts, keys, budgets
- [scripts/start-session.sh](../../scripts/start-session.sh) — what runs every session start
