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

## Step 5 — Wire Azure (ONLY if this Mac drives Azure pipeline phases)

The pipeline uses three Azure services: Document Intelligence (OCR), Translator (ar→en + others), and Speech (audio transcription). Credentials live in the macOS Keychain so the scripts can find them without env vars or dotfiles.

```bash
cd ~/PROJECTS/podcast-factory/infra/azure
az login
az account set --subscription "Journal AI — primary"

# One-time provisioning if the Azure resources don't exist yet:
bash provision-azure.sh         # Idempotent; safe to re-run
# Always:
bash store-keychain-keys.sh     # Pulls keys/endpoints/regions into Keychain
```

Verify with the connectivity probe:

```bash
cd ~/PROJECTS/podcast-factory
python3 scripts/podcast/test_azure_connectivity.py
```

Expect 5 PASS lines (Translator creds + Doc Intel creds + Translator live + Doc Intel reachable + Speech creds). Speech is optional and prints `PASS (skipped)` if the credentials aren't yet provisioned — that's fine if you don't plan to transcribe audio yet.

## Step 5.5 — Wire LLM APIs (Claude + Gemini)

Anthropic Claude runs off the Max subscription (no API key on this Mac). Google Gemini needs an API key stored in keychain. Full reference: [infra/llm-apis/README.md](../../infra/llm-apis/README.md).

```bash
cd ~/PROJECTS/podcast-factory
bash infra/llm-apis/bootstrap-llm-apis.sh   # Prompts you to paste the Gemini key (silent)
bash infra/llm-apis/verify-llm-apis.sh      # Confirms both providers reachable
```

To get the Gemini key value: open [aistudio.google.com/apikey](https://aistudio.google.com/apikey), find the `podcast-factory` row, click the copy icon.

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
