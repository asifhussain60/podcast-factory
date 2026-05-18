# Primary-Mac Activation Runbook

**Purpose.** Bring the primary Mac (the one with `az` CLI installed and your Azure subscription already provisioned for Translator + Doc Intelligence + Storage) to **100% activation** of the work shipped in commit `c85e87d` (`origin/test/api-connectivity`):

- Azure Speech-to-Text resource live + creds in Keychain
- Loop M post-publication path fully automated (transcribe → audit → challenger next-step)
- Claude Code skills + agent wrappers installed from the tracked source-of-truth
- One-command `make bootstrap` available for future Macs

This is a **one-time** runbook. Once done, the activation steps don't need to repeat unless you rotate keys or onboard a new Mac.

---

## Section 0 — Preconditions

Run these checks first. **Stop and fix anything that fails before continuing.**

```sh
# A. az CLI installed (the bootstrap script's prereq)
command -v az  # expect: /opt/homebrew/bin/az  (or wherever brew put it)

# B. Logged into the right Azure account
az account show --query "{name:name, id:id}" -o tsv
# expect: the subscription that owns rg-journal-ai (3440564d-c056-4173-bec6-7af92dbece77)

# C. Resource group reachable
az group show --name rg-journal-ai --query name -o tsv
# expect: rg-journal-ai

# D. Existing Keychain entries (proof you've bootstrapped at least once)
security find-generic-password -s azure-journal-translator-key1 >/dev/null && echo "OK translator" || echo "MISSING translator — run: make store-keys"
security find-generic-password -s azure-journal-docintel-key1   >/dev/null && echo "OK docintel"   || echo "MISSING docintel — run: make store-keys"
```

If A/B/C pass and D shows OK for translator+docintel, you're ready. If D is missing entries, run `cd ~/PROJECTS/journal && make store-keys` first.

If you are setting up a **fresh Mac**, skip this runbook and run `cd ~/PROJECTS/journal && make bootstrap` instead — it covers everything end-to-end (including Speech activation if `ENABLE_SPEECH=true` is already in the tracked config).

---

## Section 1 — Sync the branch

```sh
cd ~/PROJECTS/journal
git fetch origin
git status                                # confirm working tree is clean (no uncommitted local changes)
git checkout test/api-connectivity
git pull --ff-only origin test/api-connectivity
git log --oneline -3                      # confirm HEAD is c85e87d (or descendant)
```

Expected HEAD line:
```
c85e87d infra(podcast,multi-mac): Azure STT, Loop M SLA, one-command bootstrap
```

If `git pull` errors with a merge conflict on `infra/azure/azure-config.env`, your primary Mac had a local edit. Resolve manually — the tracked version on `origin` is the canonical source of truth now.

---

## Section 2 — Activate Azure Speech (the 4-liner)

The work this runbook exists for. Each command is idempotent — safe to re-run after partial failure.

```sh
# 1. Flip the flag in the tracked config
sed -i '' 's/ENABLE_SPEECH="false"/ENABLE_SPEECH="true"/' infra/azure/azure-config.env
grep ENABLE_SPEECH infra/azure/azure-config.env
# expect: ENABLE_SPEECH="true"     # Flip to "true" + re-run provision-azure.sh ...

# 2. Provision the Azure Speech resource (~30 sec; SKU S0 = $1/audio-hour pay-as-you-go)
make provision
# expect: [4/6] Speech: journal-speech (SKU S0)  /  OK
# (If you see [4/6] Speech: SKIPPED, the sed in step 1 didn't take — check the file.)

# 3. Fetch keys to Keychain
make store-keys
# expect: ==> Speech keys → keychain  /  OK azure-journal-speech-key1
#                                         OK azure-journal-speech-endpoint
#                                         OK azure-journal-speech-region

# 4. Health check
make verify
# expect: All checks passed (N / N).  Speech section now shows 4 PASS lines.
```

---

## Section 3 — Verify post-activation

```sh
# 5. Connectivity probe — Speech credentials check now PASSes (was SKIP before)
make azure-probe
# expect: PASS  5. Speech credentials (optional)  region=eastus

# 6. Python smoke test
python3 -c "
import sys; sys.path.insert(0, 'scripts/podcast')
import _azure
creds = _azure.load_speech_creds()
print(f'Speech endpoint: {creds.endpoint}')
print(f'Speech region:   {creds.region}')
"
# expect: Speech endpoint: https://eastus.api.cognitive.microsoft.com
#         Speech region:   eastus
```

---

## Section 4 — End-to-end smoke test (optional but recommended)

Once you have a NotebookLM Audio Overview MP3 to test against:

```sh
# 7. Full post-publication pipeline: transcribe → audit → challenger next-step
make podcast-post-publish \
  BOOK_DIR=content/podcast/library/books/ayyuhal-walad \
  EP=EP02-hatim-eight-benefits \
  AUDIO=path/to/EP02-hatim-eight-benefits.mp3

# expect output ends with:
#   [3/3] Next — invoke podcast-challenger to fold Loop M into convergence:
#         Use the Agent tool with subagent_type=podcast-challenger,
#         prompt: `ayyuhal-walad --chapter hatim-eight-benefits`
```

Parity check: the resulting `turboscribe/EP02-hatim-eight-benefits.transcript.txt` should be similar (not byte-identical, but functionally equivalent) to the existing TurboScribe transcript at the same path. The audit report at `_system/audit-EP02-hatim-eight-benefits.md` should produce comparable P0/P1 counts to the manual-transcript audit.

If parity diverges materially, surface the diff — that's empirical signal worth adding to `ROADMAP.md` Section B.

---

## Section 5 — Commit & push the activation

After Sections 2–3 pass, commit the flag flip so future Macs (and a re-clone here) inherit the active state:

```sh
git add infra/azure/azure-config.env
git diff --cached infra/azure/azure-config.env   # one-line change: ENABLE_SPEECH="false" → "true"
git commit -m "infra(azure): activate Azure Speech (ENABLE_SPEECH=true)"
git push origin test/api-connectivity
```

If you have a merge to `main` planned, this is the moment to do it (or open a PR — your call on the branching model).

---

## Section 6 — Rollback (if needed)

If anything misbehaves and you want to back out:

```sh
# Delete the Azure resource (stops billing)
az cognitiveservices account delete --name journal-speech --resource-group rg-journal-ai --yes

# Flip the flag back
sed -i '' 's/ENABLE_SPEECH="true"/ENABLE_SPEECH="false"/' infra/azure/azure-config.env

# Clean Keychain
for s in speech-key1 speech-endpoint speech-region; do
  security delete-generic-password -s "azure-journal-$s" 2>/dev/null
done

# Verify (Speech section should now SKIP)
make verify
```

The manual TurboScribe drop path remains unchanged at all times — `transcribe_episode.py` is the *added* path, not a replacement.

---

## Section 7 — What this runbook does NOT cover

| Item | Why excluded | Where to find it |
|---|---|---|
| Installing `az` CLI on a fresh Mac | This runbook assumes the primary Mac is already set up | `docs/multi-mac-runbook.md` Phase 1 Step 1 |
| Cloudflare tunnel for the web app | Separate concern from the podcast pipeline | `docs/cloudflare/setup.md` |
| Anthropic API key in Keychain | Runbook classifies as "punt unless 3rd Mac" | `docs/multi-mac-runbook.md` Step 9 |
| NotebookLM audio auto-download | No public API exists | Manual download remains |
| B1–B8 (Arabic TTS protocol) | Pre-empirical rule rewrites; awaiting Loop M data | `content/podcast/.skill/ROADMAP.md` §B |
| E1 (`skills-staging/` → `skills/` rename) | High-blast-radius refactor; deserves its own session | `content/podcast/.skill/ROADMAP.md` §E1 |

---

## Verification checklist (paste into chat when done)

After running Sections 2–3, paste this filled-out summary back to the agent so we can confirm activation succeeded without you having to ferry full command output:

```
Section 0 (preconditions): [ ] az found  [ ] logged in  [ ] rg exists  [ ] keys present
Section 1 (sync):          [ ] HEAD = c85e87d (or descendant)
Section 2 (activate):      [ ] flag flipped  [ ] make provision OK  [ ] make store-keys OK  [ ] make verify OK
Section 3 (verify):        [ ] make azure-probe shows Speech PASS  [ ] python load_speech_creds OK
Section 4 (e2e smoke):     [ ] (optional) transcribe → audit ran cleanly  -- OR --  [ ] deferred until first real episode
Section 5 (commit/push):   [ ] activation commit pushed
Section 6 (rollback):      [ ] not needed
```

Any failures → paste the failing command + last 10 lines of its output. I can debug from the logs without touching the live stack.
