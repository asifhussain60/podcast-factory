# infra/ — infrastructure components

This directory contains all provisioning scripts, credential management tooling, git hooks, background task scheduling, and agent specifications for the podcast-factory pipeline.

## Directory map

| Directory / File | Purpose | When to use |
|---|---|---|
| [`azure/`](azure/) | Azure Cognitive Services provisioning + Key Vault secret sync | New Mac setup, key rotation, recreate-from-scratch |
| [`git-hooks/`](git-hooks/) | Pre-commit quality gates (DR-009 + HTML-view Cortex checks) | Post-clone (`bash scripts/install-git-hooks.sh`) |
| [`launchd/`](launchd/) | macOS background task (Wave 1 hourly pipeline runner) | Optional: autonomous background processing |
| [`llm-apis/`](llm-apis/) | Claude + Gemini API account docs, keys, bootstrap | New Mac setup, key verification |
| [`claude-agents/`](claude-agents/) | Canonical agent spec files (18 agents) | Agent authoring; `.github/agents/` stubs point here |
| [`setup-wisdom-db.sh`](supabase/setup-wisdom-db.sh) | Local SQL Server (Docker) for Quran/sessions/topics corpus | Post-clone, once per Mac |
| [`cloudflare/`](cloudflare/) | Cloudflare account, secrets, and how to deploy to it | Canonical |
| [`supabase/`](supabase/) | Salty Lamps notes database record (not podcast-factory pipeline) | Reference only |

## Quick-reference: new Mac setup order

Full guide at [docs/setup/bootstrap.md](../docs/setup/bootstrap.md). The infra steps in order:

```
1. brew install python@3.11 jq azure-cli gh
2. claude login
3. gh repo clone asifhussain60/podcast-factory
4. bash scripts/install-git-hooks.sh          # infra/git-hooks/
5. bash scripts/install-claude-skills.sh       # infra/claude-agents/
6. cd infra/azure && az login && bash pull-secrets.sh   # all credentials from Key Vault
7. bash infra/llm-apis/verify-llm-apis.sh      # confirm Claude + Gemini
8. bash infra/supabase/setup-wisdom-db.sh               # SQL Server (optional; needs Docker + dump files)
9. bash scripts/start-session.sh               # confirm ready
```

## azure/ — credential management

The `azure/` subdirectory owns all secret lifecycle operations:

| Script | Role | Who runs it |
|---|---|---|
| `provision-azure.sh` | Create Azure resources (one-time per subscription) | Primary Mac, blank-slate only |
| `store-keychain-keys.sh` | Azure → local Keychain (direct fetch, no KV) | Primary Mac after rotation |
| `migrate-to-keyvault.sh` | Local Keychain → Key Vault (source of truth) | Primary Mac after rotation |
| `pull-secrets.sh` | Key Vault → local Keychain (all secrets, one command) | Every new Mac; after rotation |
| `verify-azure.sh` | Read-only health check (credentials + endpoints) | Troubleshooting |
| `azure-config.env` | Live non-secret config (resource names, flags, subscription) | Tracked; read by all scripts |
| `azure-config.template.env` | Template for new projects | Copying to a new project |

**Key Vault is active** (`ENABLE_KEYVAULT=true`, vault `podcast-factory-vault`, enabled 2026-06-02). All 14 secrets are stored there. New Macs only need `pull-secrets.sh`.

See [docs/setup/azure-stack.md](../docs/setup/azure-stack.md) for the full resource inventory and recreate-from-scratch procedure.

## git-hooks/ — commit quality gates

`infra/git-hooks/pre-commit` runs on every commit and blocks:
- Version stamps in files (`Version: <digit>`) — DR-009
- Versioned filenames (`*v[0-9]*.md`, `*v[0-9]*.yaml`, excluding `_archive/`)
- HTML-view Cortex violations in `plan-dashboard/src/` (via `lint-html-views.mjs`)

Install with:
```bash
bash scripts/install-git-hooks.sh
```

The install script symlinks the hook into `.git/hooks/` — it is per-machine (not tracked by git). Re-run after pulling hook updates.

## llm-apis/ — Claude + Gemini accounts

Full documentation at [infra/llm-apis/README.md](llm-apis/README.md). Key facts:

- **Claude**: Max subscription via `claude login` OAuth. Pipeline uses `claude -p` headless mode. No API key stored on operator Macs.
- **Gemini**: Paid-tier API key stored under keychain service `gemini_api_key`. Included in Key Vault — pulled automatically by `pull-secrets.sh`.
- **Anthropic API** (separate from Max subscription): key stored under `anthropic_api_key` in Key Vault. Used for direct API calls outside the pipeline.

## setup-wisdom-db.sh — local knowledge corpus

One-time Docker SQL Server bootstrap for the source library (Quran lookup, session topics, Kashkole). Prerequisites:

- Docker runtime running (OrbStack recommended: `brew install orbstack`)
- Three dump files present (gitignored — copy from another machine or export from home server at `192.168.1.158`):
  - `CONTENT/_shared/source-library/KQur.sql` (~15 MB)
  - `CONTENT/_shared/source-library/KSessions.sql` (~29 MB)
  - `CONTENT/_shared/source-library/Kashkole.sql` (~724 MB)

```bash
bash infra/supabase/setup-wisdom-db.sh   # ~3-5 min first run; idempotent

# After script completes, register the MCP server:
python3 scripts/podcast/source_library_server.py --register
```

Troubleshooting:
- `docker: command not found` → start OrbStack and retry
- `container already exists` → idempotent; script skips creation
- Dump files missing → copy from `CONTENT/_shared/source-library/` on another Mac or re-export from home server

## claude-agents/ — canonical agent specifications

18 agent spec files live here. This is the **single source of truth** for agent behavior. `.github/agents/` contains thin discovery stubs (≤15 lines) pointing into this directory. Agents are installed into `.claude/agents/` by `scripts/install-claude-skills.sh`.

See `infra/claude-agents/_README.md` for the full manifest and DR-014 stub-pattern decision.
