# Multi-Mac Runbook — Run the Journal & Podcast Skills from Any Mac

This runbook is the executable plan for running the **/journal** and **/podcast**
Cowork skills, plus the Azure-backed OCR + translation pipeline, from any Mac
you sit down at — primary workstation, laptop, future replacement machine.

Estimated time per new Mac: **~30 minutes**, most of it waiting for installs.

---

## What's already cloud-ready (no work needed)

Some pieces are already cross-machine because they live in the cloud:

| Component | Where it lives | Implication |
|-----------|---------------|-------------|
| Azure resources | `rg-journal-ai` in East US | Any Mac with `az login` can use them |
| GitHub journal repo | (presumed; not yet wired) | Clone on each Mac |
| Cowork app | App download per Mac (sign in once) | Skills install via `scripts/install-claude-skills.sh` from the cloned repo |
| DayOne entries | iCloud sync | Already automatic |
| NotebookLM bundles | Google account | Already automatic |
| Memoir source material | `content/babu-memoir/` in repo | Git is the sync layer |

## What's per-Mac (needs bootstrap)

The bootstrap fills these gaps on each Mac:

| Component | Why per-Mac | Bootstrap step |
|-----------|------------|----------------|
| Azure API keys | Keychain is local-only | Run `store-keychain-keys.sh` |
| Anthropic API key (if running the web app) | Same | Manual `security add-generic-password` |
| Anthropic proxy launchd job | macOS-local | Install plist (if running web app) |
| cloudflared tunnel | macOS-local | Install only on the Mac that hosts the web app |
| Repo working copy | Git clones are local | `git clone` |
| Cowork app | App installs are local | Download + sign in |

---

## The three-phase plan

**Phase 1 — Per-Mac bootstrap** *(works today with existing scripts).* Get a
fresh Mac running the skills + Azure stack in ~30 minutes. All the tooling
already exists; this phase is just running it.

**Phase 2 — Migrate Azure secrets to Key Vault** *(one-time, on your primary
Mac).* Cleaner secrets posture: one rotation point in Azure, Keychain becomes
a local cache. Optional but recommended once you have 2+ Macs.

**Phase 3 — One-command bootstrap script** *(also works today).* Wrap the
Phase-1 dance in a single script (`bootstrap-new-mac.sh`) so a new Mac is
~5 commands total instead of 15.

Do them in order. Phase 1 alone is enough to use the skills on a new Mac
today. Phase 2 and 3 reduce ongoing friction.

---

## Phase 1 — Per-Mac bootstrap

Run these steps once on each new Mac. The order matters.

### Step 1 — Install prerequisites

```sh
# Homebrew (if not already)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Tools the bootstrap script needs
brew install azure-cli git
```

### Step 2 — Install the Cowork desktop app

Download from claude.ai/downloads (or your usual source) and sign in with the
same Anthropic account you use on your primary Mac. Your installed skills and
plugins will sync automatically.

### Step 3 — Clone the journal repo

```sh
mkdir -p ~/PROJECTS
cd ~/PROJECTS
git clone <your-github-repo-url> journal
cd journal
```

(If the journal repo isn't on GitHub yet, push it from your primary Mac
first: `cd ~/PROJECTS/journal && git remote add origin <url> && git push -u origin main`.)

### Step 4 — Log into Azure

```sh
az login
```

Opens a browser. Pick `asifhussain60@msn.com` (the account that owns
`rg-journal-ai`). Verify with:

```sh
az account show --query name -o tsv
# Expected output: Azure subscription 1
```

### Step 5 — Pull Azure secrets into local Keychain

```sh
cd ~/PROJECTS/journal/infra/azure
./store-keychain-keys.sh
```

This is the linchpin step. It reads `azure-config.env` (committed in the
repo, matches the live deployment), then calls `az` to fetch the current
Key 1 + endpoint for each Azure resource and stores them in this Mac's
login keychain under the `azure-journal-*` prefix.

No secrets ever cross through the chat or get pasted — they're fetched
directly from Azure to the local keychain.

### Step 6 — Verify

```sh
./verify-azure.sh
```

Expected: all checks PASS. If any FAIL, see `docs/azure/troubleshooting.md`.

### Step 7 — Install Claude Code skills + agent wrappers

The repo carries the canonical skill content (`skills-staging/{journal,podcast}/SKILL.md`)
and tracked agent wrappers (`infra/claude-agents/*.md`). One command materializes both
into Claude Code's per-machine runtime locations:

```sh
cd ~/PROJECTS/journal
./scripts/install-claude-skills.sh
```

The script copies:
- `skills-staging/journal/SKILL.md` → `~/Library/Application Support/Claude/skills/journal/SKILL.md`
- `skills-staging/podcast/SKILL.md` → `~/Library/Application Support/Claude/skills/podcast/SKILL.md`
- `infra/claude-agents/*.md` → `.claude/agents/*.md` (5 wrappers: journal-challenger, podcast-challenger, podcast-extract, refine-prompt, ui-reviewer)

After running it, restart Cowork. Confirm `/journal` and `/podcast` appear
in the slash-command menu.

Phase 3 (the one-command bootstrap) calls this script automatically — Step 7
is the manual fallback when running Phase 1 standalone.

### Step 8 — Test end-to-end

In Cowork, try a small action that uses Azure:

> @podcast — translate page 1 of the file `source-arabic/test.pdf` and save the result.

If it works, you're done. The skills can now read Azure keys from Keychain
and call OCR + translation from this Mac.

---

## Phase 1 — Optional: also run the journal web app on this Mac

The web app at `journal.kashkole.com` is normally hosted on your primary
Mac. If you want a *second* Mac to host it too (for testing, or as a
backup), you need three more pieces:

### Step 9 — Anthropic API key in Keychain

The Express proxy at `server/` reads the Anthropic key from Keychain at
startup. Store it once:

```sh
security add-generic-password -U -a "$USER" -s anthropic-api-key -w '<your-sk-ant-...-key>'
```

Verify with `security find-generic-password -s anthropic-api-key` (it'll
return metadata only, not the value).

### Step 10 — Install + run the proxy under launchd

```sh
cd ~/PROJECTS/journal/server
npm install
# Install + load the launchd plist (script lives in server/scripts/, see server/README.md)
```

Confirm the proxy is up:

```sh
curl -s http://127.0.0.1:3001/health | python3 -m json.tool
# Expect: {"status":"ok","keySource":"keychain", ...}
```

### Step 11 — Set up the cloudflared tunnel (only if this Mac becomes the primary)

The tunnel only runs on one Mac at a time. If you want this Mac to be the
host, follow `docs/cloudflare/setup.md` from the top. If this Mac is a
secondary, **skip this step** — the tunnel on your primary Mac is still
serving `journal-api.kashkole.com`.

---

## Phase 2 — Migrate Azure secrets to Key Vault *(one-time, primary Mac)*

Run this once you have 2+ Macs and want a single rotation point. Without
this phase, rotating an Azure key means running the store script on every
Mac. With this phase, rotation happens in Azure once and every Mac picks
up the new value on its next fetch.

### Step P2.1 — Enable Key Vault in the config

```sh
cd ~/PROJECTS/journal/infra/azure
sed -i '' 's/ENABLE_KEYVAULT="false"/ENABLE_KEYVAULT="true"/' azure-config.env
```

### Step P2.2 — Provision the Key Vault

```sh
./provision-azure.sh
```

The script is idempotent. This run only adds the Key Vault and grants
your user the `Key Vault Secrets Officer` role.

### Step P2.3 — Push existing Keychain entries to Key Vault

```sh
./migrate-to-keyvault.sh
```

Reads each `azure-journal-*` entry from this Mac's Keychain and uploads it
as a secret in `kv-journal-ai` with the same name. Run only once, only on
your primary Mac.

### Step P2.4 — Update other Macs to read from Key Vault

On each non-primary Mac (and the primary Mac too, to refresh from Key Vault), run:

```sh
cd ~/PROJECTS/journal/infra/azure
./store-keychain-keys.sh   # When ENABLE_KEYVAULT=true and the vault is
                           # reachable, reads from Key Vault FIRST. Falls back
                           # to direct Azure fetch on a per-secret KV miss
                           # (you'll see a NOTE line for any missing secret,
                           # which means migrate-to-keyvault.sh needs a re-run).
```

After this, Keychain on each Mac is a local cache; Key Vault is the source of truth.

### Rotating a key after Phase 2

```sh
# On primary Mac
az cognitiveservices account keys regenerate \
  --name journal-translator \
  --resource-group rg-journal-ai \
  --key-name Key1

# Push new value into Key Vault
./migrate-to-keyvault.sh   # picks up the new value and updates the secret

# On every Mac (including primary)
./store-keychain-keys.sh   # re-fetches from Key Vault
```

Zero secrets pasted, zero per-Mac edits, single rotation point.

---

## Phase 3 — One-command bootstrap

After Phase 1 the per-Mac setup works but it's eight steps. Phase 3 wraps
those into one script.

### On a new Mac (after Cowork + repo clone)

```sh
cd ~/PROJECTS/journal/infra/azure
./bootstrap-new-mac.sh
```

This script:

1. Checks `brew`, `az`, `git` are installed
2. Runs `az login` if not logged in
3. Verifies the subscription matches the config
4. Runs `store-keychain-keys.sh` (Key Vault → Keychain when SoT is KV; direct Azure fetch otherwise)
5. Runs `verify-azure.sh`
6. Runs `scripts/install-claude-skills.sh` (skill files + agent wrappers)
7. Reports next manual steps (restart Cowork, Anthropic key if web app, etc.)

If everything passes, the Mac is ready. If anything fails, the script
prints the exact command to fix it.

---

## Keeping multiple Macs in sync over time

After both Macs are bootstrapped, sync is mostly automatic:

| Change happens | Sync mechanism | Manual step? |
|----------------|----------------|--------------|
| Memoir chapter edited | git push / git pull | git pull on the other Mac |
| Cowork skill updated | Cowork plugin sync | None |
| Azure key rotated | Phase 2 Key Vault → fetch script | One command per Mac |
| New container added to Azure | Edit config + re-run `provision-azure.sh` | None on other Macs (Azure is cloud) |
| Anthropic key rotated | Manual `security add-generic-password` per Mac | One command per Mac |
| Memoir source PDF added | git push / git pull | git pull on the other Mac |
| Web app code change | git push / restart proxy | git pull + restart launchd job |
| Tunnel UUID regenerated | Manual reinstall (rare) | Phase 1 step 11 redo |

---

## What this plan does NOT solve

- **Concurrent web app on multiple Macs.** Only one Mac at a time should
  serve `journal.kashkole.com`. The cloudflared tunnel routes to whichever
  Mac is currently running it. If both run it, last-writer-wins on connection
  multiplexing — not a hard failure, but unpredictable. Pick one host.
- **Sharing the Anthropic key cleanly.** Today the key sits in each Mac's
  Keychain separately. A future Phase 4 could push it into Key Vault too
  (Anthropic doesn't care which Mac the call comes from). Punt unless you
  have a 3rd Mac.
- **Coexisting active editing of the same memoir chapter on two Macs.** Git
  handles this fine for sequential edits but you'll hit merge conflicts on
  concurrent edits. Stick to one Mac at a time per chapter.

---

## Checklist — what to do right now to start

If you're at your primary Mac with everything working:

- [ ] Push the journal repo to a private GitHub repo (one-time)
- [ ] On your second Mac, run Phase 1 Steps 1–8 (~30 min)
- [ ] (Optional) Run Phase 2 to migrate Azure secrets to Key Vault
- [ ] (Optional) Run Phase 3 by replacing Phase 1 Steps 4–6 with one command

Each phase is independent. Doing only Phase 1 already gets you running the
skills on the second Mac.

---

## Quick-reference paths

| What | Where |
|------|-------|
| This runbook | `docs/multi-mac-runbook.md` |
| Azure provisioning script | `infra/azure/provision-azure.sh` |
| Azure key-fetch script | `infra/azure/store-keychain-keys.sh` |
| Azure health check | `infra/azure/verify-azure.sh` |
| Phase 2 migration script | `infra/azure/migrate-to-keyvault.sh` |
| Phase 3 bootstrap script | `infra/azure/bootstrap-new-mac.sh` |
| Azure config (live) | `infra/azure/azure-config.env` |
| Claude Code skill install | `scripts/install-claude-skills.sh` |
| Tracked agent wrappers | `infra/claude-agents/*.md` |
| Top-level Makefile | `Makefile` (targets: `bootstrap`, `verify`, `install-skills`, …) |
| Cloudflare runbook | `docs/cloudflare/setup.md` |
| Azure architecture | `docs/architecture/azure.html` |
| Cloudflare architecture | `docs/architecture/cloudflare.html` |
