# infra/ — everything the pipeline needs that is not the pipeline

Provisioning scripts, credential wiring, git hooks, deployment records, and the
canonical agent specifications. **Last reconciled against the live systems and the
running code: 2026-08-10.**

## Start here

**[pipeline-runtime.md](pipeline-runtime.md) is the migration document.** It maps all
29 orchestrator phases to the external services they reach, states where every secret
actually lives (and which four are not recoverable from anything in this repo), lists
the software a machine must have, and names the three steps only a human can do. If
you are standing up a new machine or answering "what would we have to reproduce",
read that first and treat this file as its index.

## Directory map

| Path | What it is | When you need it |
|---|---|---|
| [`pipeline-runtime.md`](pipeline-runtime.md) | The end-to-end runtime + credential map | Migration; "what does phase X touch" |
| [`azure/`](azure/) | Azure resource provisioning, Key Vault sync, the transcription runbook | New subscription, key rotation, Speech transcription |
| [`llm-apis/`](llm-apis/) | Anthropic, Google and ElevenLabs accounts, keys, budgets | New Mac, key rotation, spend questions |
| [`cloudflare/`](cloudflare/) | The Cloudflare account, what is deployed, and how to deploy | Anything touching the Podcast Factory Library or a Pages site |
| [`git-hooks/`](git-hooks/) | Five tracked hooks — the commit gate, and the develop↔localhost sync | Post-clone; a blocked commit you do not understand |
| [`claude-agents/`](claude-agents/) | Canonical specs for all 22 agents | Agent authoring |
| [`wisdom-db/`](wisdom-db/) | Local SQL Server container for the three source-library dumps | Optional, once per machine |

Two things that are **not** here, so you do not go looking: the Astro Site's own
build tooling lives in `plan-dashboard/`, and the Podcast Factory Library's Worker
config lives in `listener/wrangler.jsonc`. `infra/cloudflare/` documents where those
deploy to; it does not hold their configuration.

## New machine, in the order that actually matters

The full walkthrough with the reasoning is
[pipeline-runtime.md §5](pipeline-runtime.md); this is the shape of it.

```bash
brew install python@3.11 jq azure-cli gh node ffmpeg poppler
brew install --cask claude-code
gh repo clone asifhussain60/podcast-factory && cd podcast-factory
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/install-git-hooks.sh
bash scripts/install-claude-skills.sh
claude login                 # asifhussain60@gmail.com — Max subscription
az login                     # asifhussain60@msn.com   — a DIFFERENT account
python3 scripts/podcast/preflight_doctor.py
```

> **`az login` is what makes credentials work — not `pull-secrets.sh`.** The pipeline
> resolves every secret as environment variable → Azure Key Vault. The macOS-keychain
> tier was removed on 2026-06-04. Any document that tells you the pipeline reads the
> keychain for Azure or Gemini credentials is describing the system as it was before
> that date.

The keychain is still the *only* home of four values — the ElevenLabs key, the
Cloudflare token, and the two Podcast Factory Library development secrets. Those must
be stored by hand and are listed with their recovery paths in
[pipeline-runtime.md §1](pipeline-runtime.md).

## azure/ — resources and secret lifecycle

| Script | Role | Who runs it |
|---|---|---|
| `provision-azure.sh` | Create the Azure resources | Once, on a blank subscription |
| `store-keychain-keys.sh` | Azure → local keychain | After a rotation, on the primary Mac |
| `migrate-to-keyvault.sh` | Local keychain → Key Vault | After a rotation, on the primary Mac |
| `pull-secrets.sh` | Key Vault → local keychain | Legacy — see the caveat below |
| `verify-azure.sh` | Read-only health check | Troubleshooting — see the caveat below |
| `azure-config.env` | Live non-secret config, tracked | Read by every script above |
| `azure-config.template.env` | Template for a different app | Standing up a parallel stack |
| `transcription-runbook.md` | Azure Speech transcription, and its failure log | `audio-ingest`, lecture transcription |

**Caveat on the last two.** `pull-secrets.sh` writes a keychain cache the pipeline no
longer reads, and `verify-azure.sh` checks that same cache — so on a correct,
vault-only machine it reports missing keys for a stack that works. Neither is wrong
about what it claims to do; they are simply no longer how a machine is made to work.
Use `preflight_doctor.py` or `test_azure_connectivity.py`, which resolve credentials
the way the pipeline does.

Key Vault `podcast-factory-vault` holds **22** secrets and has been the source of
truth since 2026-06-02. Full resource inventory and the recreate-from-scratch
procedure: [docs/setup/azure-stack.md](../docs/setup/azure-stack.md).

## git-hooks/ — the commit gate and the develop sync

Five hooks, installed with `bash scripts/install-git-hooks.sh`, doing two unrelated
jobs: `pre-commit` blocks a commit that breaks a documented contract (DR-009, DR-005,
ruff, agent-mirror parity, dead links, the repo-surgeon probe, eslint, prettier, the
Astro Site tests), and `post-commit` / `post-merge` / `post-checkout` regenerate the
Astro Site snapshots and apply the local D1 migrations whenever `develop` moves.

Per-hook detail, what each check means, and the bypass rule:
[git-hooks/README.md](git-hooks/README.md).

## llm-apis/ — the model providers

- **Claude** — Max subscription, `claude login` OAuth, no API key. `claude -p` is the
  pipeline's main reasoning path and is flat-rate.
- **Anthropic API** — a *separate* org with its own $25 cap, used only by the SDK
  refinement path. The key is the vault's `llm-anthropic-api-key` and is deliberately
  never loaded into the environment, so it cannot divert `claude -p` onto metered
  billing.
- **Gemini** — paid tier, key `llm-gemini-api-key` in the vault. Second-opinion
  auditor, literary pass, image generation, and the Composer's Explain button.
- **ElevenLabs** — keychain-only, used by the `audio-script` and `audio-render`
  phases on API-voiced books.

Accounts, billing IDs, budgets and rotation: [llm-apis/README.md](llm-apis/README.md).

## cloudflare/ — what is live

The gmail account (`19cb05067ea7e704f94481df1685ec51`), the `safinaverse.com` zone,
the `podcast-listener` Worker at `podcast-factory.safinaverse.com` with its D1
database and R2 bucket, the exact permissions the API token has and the two it does
not, and the standing hazard that `wrangler` on this machine is logged into a
different account. [cloudflare/README.md](cloudflare/README.md).

Going live is one command, and it is gated on Asif's own local test, never on green
checks: `scripts/podcast/deploy_listener.sh <slug>`.

## claude-agents/ — the agent specifications

22 canonical specs. This directory is the single source of truth; the copies under
`.github/agents/` and `.codex/agents/` are **generated** by
`scripts/podcast/sync-agent-wrappers.sh` and must never be hand-edited — the
pre-commit hook fails on drift. Registry and the generation contract:
[claude-agents/_README.md](claude-agents/_README.md).

## wisdom-db/ — the local source-library corpus

Optional. One-time Docker SQL Server bootstrap for the Quran / sessions / topics
databases, needed only by the source-library MCP server.

```bash
bash infra/wisdom-db/setup-wisdom-db.sh    # ~3-5 min first run; idempotent
python3 scripts/podcast/source_library_server.py --register
```

Requires a Docker runtime (OrbStack) and the three gitignored dumps under
`content/_shared/source-library/` — `KQur.sql` (~15 MB), `KSessions.sql` (~29 MB),
`Kashkole.sql` (~724 MB). They are not in git and not in any cloud store the repo
knows about: restore them from an external backup or another Mac. What travels in git
and what does not is tabulated in [pipeline-runtime.md §4](pipeline-runtime.md).
