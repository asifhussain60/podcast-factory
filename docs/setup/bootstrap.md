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

The repo is flat (no worktrees container). Books live under `content/<Bucket>/<slug>/` (bucket-grouped layout since 2026-06-07); `published` is a status field in `_system/orchestrator-state.json`, not a folder.

## Step 4.5 — Install git hooks and Claude skills

```bash
cd ~/PROJECTS/podcast-factory

# Enforce DR-009 (no version markers) + HTML-view quality gate on every commit:
bash scripts/install-git-hooks.sh

# Install Claude agent specs into .claude/agents/ (required for orchestrator, challenger, etc.):
bash scripts/install-claude-skills.sh
```

Both scripts are idempotent — safe to re-run after pulling new hook or skill versions.

## Step 4.7 — Set up the Python virtual environment

The pipeline runs under a venv so all sub-scripts inherit the right packages via `sys.executable`.

```bash
cd ~/PROJECTS/podcast-factory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After this, **always activate the venv before running pipeline commands**:

```bash
source .venv/bin/activate   # once per terminal session
python3 scripts/podcast/orchestrate_book.py <pdf>
```

## Step 5 — Wire Azure credentials (ONLY if this Mac drives pipeline phases)

All credentials are stored in Azure Key Vault (`podcast-factory-vault`), and the
pipeline reads them **from the vault directly**. `az login` is the whole step.

```bash
cd ~/PROJECTS/podcast-factory
az login                 # sign in as asifhussain60@msn.com — NOT the gmail account
az account set --subscription "Journal AI — primary"
python3 scripts/podcast/test_azure_connectivity.py
```

Expect `pass 9  fail 0  ✓ Azure connectivity OK`.

> **The Azure identity is a different account from everything else.** Claude,
> Google and Cloudflare are `asifhussain60@gmail.com`; Azure is
> `asifhussain60@msn.com`. Confirm with `az account show --query user.name -o tsv`.

`infra/azure/pull-secrets.sh` also exists and copies the vault into the local
keychain. It is **not** required: the keychain tier was removed from credential
resolution on 2026-06-04, so nothing in the pipeline reads what it writes. The
credentials that genuinely live only in the keychain — the Cloudflare token and the
two Podcast Factory Library dev secrets, all three for the audience site rather than
the book pipeline — are listed with their recovery paths in
[infra/pipeline-runtime.md](../../infra/pipeline-runtime.md).

**First-time Azure provisioning only** (blank Azure subscription — not a new Mac):
```bash
bash provision-azure.sh          # Creates all Azure resources
bash store-keychain-keys.sh      # Local Keychain ← Azure
bash migrate-to-keyvault.sh      # Key Vault ← local Keychain
```

Full reference: [docs/setup/azure-stack.md](azure-stack.md).

## Step 5.5 — Wire LLM APIs (Claude + Gemini)

Anthropic Claude runs off the Max subscription (`claude login` in Step 3 covers it). The Gemini key and the separate Anthropic API key both come from the Key Vault reached in Step 5 — nothing extra to install.

There is no third provider to wire. Audio is produced by hand in NotebookLM and needs no key.

Verify both:

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
bash infra/wisdom-db/setup-wisdom-db.sh   # ~3-5 min on first run; idempotent on re-runs
```

After the script completes, register the MCP server so Claude Code can call it:

```bash
python3 scripts/podcast/source_library_server.py --register
```

### Database inventory (what travels with the repo, what is local-only)

| File | Tracked? | Size | Source of truth / how to restore |
|---|---|---|---|
| `content/knowledge-base/mirror.db` | ✅ committed | ~29 MB | Travels in git. The reference "wisdom-corpus mirror" some scripts/tests guard on. |
| `content/knowledge-base/knowledge.db` | gitignored | ~0.5 MB | **Rebuilt from JSONL** — `python3 scripts/podcast/intelligence/corpus_sync.py rebuild`. The durable corpus is the committed `content/knowledge-base/*.jsonl` atoms (union-merged across machines via `.gitattributes`). |
| `content/_shared/source-library/{KQur,KSessions,Kashkole}.sql` | gitignored | ~768 MB | Large dumps — **restore from your external backup** (Google Drive or another Mac); not in git. Feed `infra/wisdom-db/setup-wisdom-db.sh` to populate the SQL Server container. |
| `content/_shared/source-library/wisdom-corpus.db` | gitignored | ~11 MB | Local-only SQLite extract of the KSessions session/transcript data (the paused Wave-M import). Holds source transcripts (sessions/transcripts/groups), **not corpus atoms** — it is intentionally **kept, not deleted**: it is non-redundant local source data re-buildable only from `KSessions.sql`. |

> Only `mirror.db` and the JSONL atoms travel in git. Everything else is rebuildable on a fresh machine from the SQL dumps (restored from external backup) or from the committed JSONL.

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
