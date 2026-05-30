# `infra/` — asif-deploy infrastructure setup

Everything you need to stand up the asif-deploy stack on a fresh macOS or Linux machine. **Single source of truth** for Cloudflare account, Pages projects, Zero Trust / Access SSO, and AI surface wiring.

## TL;DR — fire and forget

```bash
git clone <repo-url> ~/Code/asif-deploy
cd ~/Code/asif-deploy
./infra/setup.sh
```

That's it. The script is idempotent, takes ~5 minutes the first time (mostly waiting for `wrangler login` + you pasting one API token), zero minutes on re-runs.

Re-running is safe: every phase checks state before acting and reports "already configured" if so. To re-do one phase: `./infra/setup.sh --only 8`. To skip phases: `./infra/setup.sh --skip 11`.

## What the script does, end to end

The 11 phases mirror the manual setup we did interactively, so if anything fails you can drop into the manual fallback for that phase. Each phase is independently re-runnable.

| # | Phase | Action | Manual fallback |
|---|---|---|---|
| 0 | Prerequisites | Installs (via brew/apt/dnf) `node`, `jq`, `curl`, `python3`. | [§Phase 0 — Prerequisites](#phase-0--prerequisites) |
| 1 | wrangler | `npm i -g wrangler` if missing. | [§Phase 1 — wrangler install](#phase-1--wrangler-install) |
| 2 | CLI symlink | `ln -s bin/asif-deploy ~/.local/bin/asif-deploy`. | [§Phase 2 — CLI symlink](#phase-2--cli-symlink) |
| 3 | wrangler OAuth | `wrangler login` (opens browser if not already logged in). | [§Phase 3 — wrangler OAuth login](#phase-3--wrangler-oauth-login) |
| 4 | API token | Prompts for a Cloudflare API token, verifies, stores in macOS keychain (or `~/.config/asif-deploy/cf_api_token` on Linux). Required for Cloudflare Access management — wrangler's OAuth doesn't cover it. | [§Phase 4 — API token](#phase-4--api-token) |
| 5 | Pages projects | Creates `asif-studio` and `asif-studio-private` projects (production_branch=main) if absent. | [§Phase 5 — Pages projects](#phase-5--pages-projects) |
| 6 | Zero Trust org | Ensures the account has a Zero Trust organization (Cloudflare auth-domain like `<team>.cloudflareaccess.com`). | [§Phase 6 — Zero Trust org](#phase-6--zero-trust-org) |
| 7 | Identity provider | Adds the **One-Time PIN** IdP (email-based, no external OAuth setup). Google/GitHub can be added later by hand — see [§Adding Google or GitHub later](#adding-google-or-github-later). | [§Phase 7 — Identity provider](#phase-7--identity-provider) |
| 8 | Access app + policy | Creates an Access application on `*.<private-project>.pages.dev` with an Allow policy whose include list is your email. | [§Phase 8 — Access app + policy](#phase-8--access-app--policy) |
| 9 | Public smoke test | Deploys `examples/asif-studio-landing/` to the public project, asserts the URL responds. | [§Phase 9 — Public smoke test](#phase-9--public-smoke-test) |
| 10 | Private smoke test | Deploys a minimal `examples/private-smoke/` to the private project, asserts the URL serves a Cloudflare Access login page (not the content) when unauthenticated. | [§Phase 10 — Private smoke test](#phase-10--private-smoke-test) |
| 11 | AI surface wrappers | Copies the Claude Code agent, VS Code Copilot prompt, and surfaces the Cowork `.skill` bundle so deploy is invokable from each surface. | [§Phase 11 — AI surface wrappers](#phase-11--ai-surface-wrappers) |

## Architecture recap

```
┌────────────────────────── Cloudflare account ──────────────────────────┐
│                                                                        │
│   Pages project: asif-studio              Pages project: asif-studio-  │
│   (public, free CDN)                      private (SSO-gated)          │
│                                                                        │
│   <slug>.asif-studio.pages.dev            <slug>.asif-studio-private   │
│                                              .pages.dev                │
│                                                ↑                       │
│   Zero Trust ──→ Access application ──→ Policy (include: email allowlist)
│                                                ↑                       │
│                                          One-Time PIN IdP              │
│                                          (email→6-digit code)          │
└────────────────────────────────────────────────────────────────────────┘
              ↑
         wrangler pages deploy <dir> --project-name <p> --branch <slug>
              ↑
         asif-deploy CLI (one Python file, wraps wrangler)
              ↑
         AI surface wrappers (Claude Code / Cowork / Copilot)
```

## Why this shape

**Why two projects instead of one with path-based routing?** Cloudflare Access policies attach to *applications*, applications attach to *domains*, and `wrangler pages deploy` replaces the entire content of a project on each deploy. Two projects = two policy scopes = independent public/private without a per-deploy build step that merges content into one tree. Trade-off: longer URLs (subdomain instead of subfolder). Worth it for the SSO simplicity.

**Why One-Time PIN as the default IdP?** It's the only IdP that needs zero external setup — Cloudflare itself sends the email. Google/GitHub/Microsoft OAuth all require you to click through their respective developer consoles to create OAuth apps, which can't be automated from a single script. OTP gets you SSO in one API call.

**Why an API token in addition to `wrangler login`?** `wrangler login` issues an OAuth token scoped to Workers + Pages + a few other things. It does *not* include `Account: Access: Apps and Policies: Edit`. For programmatic Access management you need a separate API token. The script verifies the token before storing.

**Why bash, not Python?** Setup script runs before Python's `asif-deploy` CLI is necessarily callable. macOS and Linux ship bash 3.2+ universally. We use only POSIX features + a few bashisms (`local`, `[[`, parameter expansion) — no associative arrays, no bash 4-only features. Should run on any Mac out of the box.

## CLI usage after setup

```bash
asif-deploy ./my-site                              # public  → <my-site>.asif-studio.pages.dev
asif-deploy ./client-doc --private                 # gated   → <client-doc>.asif-studio-private.pages.dev
asif-deploy ./demo --slug q4-pitch -m "v3"         # explicit slug + commit context
asif-deploy ./demo --slug q4-pitch --json          # JSON output for AI/CI
asif-deploy ./demo --dry-run                       # plan, don't execute
asif-deploy --doctor                               # verify install + auth
asif-deploy --list                                 # recent deploys across both projects
```

## Adding viewers to the private allowlist later

Two ways, pick one:

```bash
# Quick — re-run phase 8 with a different ASIF_DEPLOY_EMAIL env var to add another
ASIF_DEPLOY_EMAIL=friend@example.com ./infra/setup.sh --only 8

# Manual — Cloudflare dashboard → Zero Trust → Access → Applications →
# asif-studio-private → Policies → Allowed users → Edit → add email
```

If you want to allow your whole domain at once (e.g., everyone at `@yourcompany.com`), change the policy's include rule from `Emails` to `Emails ending in` via the dashboard.

## Adding Google or GitHub later

OTP works fine for "small invited list." If you want viewers to click "Sign in with Google" instead of pasting a 6-digit code:

1. Cloudflare dashboard → **Zero Trust** → **Settings** → **Authentication** → **Login methods** → **Add new** → **Google**.
2. Cloudflare shows a redirect URI like `https://<team>.cloudflareaccess.com/cdn-cgi/access/callback`. Copy it.
3. In a new tab: [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → Create OAuth client ID → Web application → paste the redirect URI → create. Copy the Client ID + Secret back into Cloudflare.
4. Cloudflare → save IdP.
5. Cloudflare → Access app `asif-studio-private` → enable Google in the IdP list → save.

Same flow for GitHub via [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers).

These IdP additions don't break the OTP fallback — viewers will see a "Sign in with…" multi-button login page.

## Cost

| | Free tier | What you'd pay if you exceed |
|---|---|---|
| Cloudflare Pages | 500 deploys/month, unlimited bandwidth, 100 custom domains | $20/month → 5,000 deploys |
| Cloudflare Access | 50 users on the free Zero Trust plan | $7/user/month above 50 |
| Cloudflare DNS / cert | unlimited | n/a |

For Asif's use case (a handful of share recipients, a few deploys per day), this is **$0/month forever**.

---

## Manual fallback — phase by phase

These are the same actions the script performs, written out for when you need to debug or skip the script.

### Phase 0 — Prerequisites

```bash
# macOS
brew install node jq

# Debian/Ubuntu
sudo apt-get install -y nodejs npm jq curl python3

# Fedora/RHEL
sudo dnf install -y nodejs npm jq curl python3
```

Verify:

```bash
node --version    # any v18+
jq --version      # any 1.6+
curl --version    # any 7+
python3 --version # any 3.9+
```

### Phase 1 — wrangler install

```bash
npm i -g wrangler
wrangler --version    # 4.x
```

If `npm i -g` requires sudo, your npm prefix is `/usr/local`. Either `sudo npm i -g wrangler` once (fine) or fix the prefix:

```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH    # add to .zshrc
```

### Phase 2 — CLI symlink

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/bin/asif-deploy" ~/.local/bin/asif-deploy

# Add to .zshrc if not already there:
export PATH="$HOME/.local/bin:$PATH"

asif-deploy --version    # 0.1.0
```

### Phase 3 — wrangler OAuth login

```bash
wrangler login           # opens browser, OAuth flow
wrangler whoami          # confirms login
```

If you have multiple Cloudflare accounts: `wrangler whoami` lists them. Pick the one that owns the Pages projects (or will own them).

### Phase 4 — API token

[Dashboard → My Profile → API Tokens → Create Token → Create Custom Token](https://dash.cloudflare.com/profile/api-tokens).

| Permission group | Permission | Access |
|---|---|---|
| Account | Cloudflare Pages | Edit |
| Account | Access: Apps and Policies | Edit |
| Account | Access: Organizations, Identity Providers, and Groups | Edit |
| Account | Account Settings | Read |
| User | User Details | Read |

Account resources: **Include → All accounts** (or specifically your account).
TTL: leave as **no expiry** (or set 1 year, your call).

Verify:

```bash
TOKEN="..."
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify | jq .
# expect: { "success": true, "result": { "status": "active" } }
```

Store on macOS:

```bash
security delete-generic-password -s cloudflare_asif_deploy_api_token -a "$USER" 2>/dev/null
security add-generic-password -s cloudflare_asif_deploy_api_token -a "$USER" -w "$TOKEN"
```

Retrieve:

```bash
TOKEN=$(security find-generic-password -s cloudflare_asif_deploy_api_token -a "$USER" -w)
```

On Linux: store in `~/.config/asif-deploy/cf_api_token` with `chmod 600`.

### Phase 5 — Pages projects

```bash
wrangler pages project create asif-studio          --production-branch main
wrangler pages project create asif-studio-private  --production-branch main
wrangler pages project list
```

Or via API:

```bash
ACCT=$(curl -sS -H "Authorization: Bearer $TOKEN" "$CF_API/accounts" | jq -r '.result[0].id')
for p in asif-studio asif-studio-private; do
  curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data "{\"name\":\"$p\",\"production_branch\":\"main\"}" \
    "$CF_API/accounts/$ACCT/pages/projects" | jq '.success'
done
```

### Phase 6 — Zero Trust org

Cloudflare dashboard → **Zero Trust** (sidebar). First time: pick a team name (becomes `<team>.cloudflareaccess.com`), pick the free plan, accept.

Or via API:

```bash
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"name":"asif-deploy","auth_domain":"asif-deploy.cloudflareaccess.com"}' \
  "$CF_API/accounts/$ACCT/access/organizations" | jq '.success'
```

### Phase 7 — Identity provider

OTP via API:

```bash
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"name":"One-Time PIN","type":"onetimepin","config":{}}' \
  "$CF_API/accounts/$ACCT/access/identity_providers" | jq '.success'
```

### Phase 8 — Access app + policy

Create the application:

```bash
APP=$(curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"name":"asif-studio-private","domain":"*.asif-studio-private.pages.dev","type":"self_hosted","session_duration":"24h"}' \
  "$CF_API/accounts/$ACCT/access/apps" | jq -r '.result.id')
```

Create the policy:

```bash
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"name":"Allowed users","decision":"allow","precedence":1,"include":[{"email":{"email":"you@example.com"}}]}' \
  "$CF_API/accounts/$ACCT/access/apps/$APP/policies" | jq '.success'
```

### Phase 9 — Public smoke test

```bash
asif-deploy ./examples/asif-studio-landing --slug main -m "smoke test"
curl -sI https://asif-studio.pages.dev | head -3   # expect HTTP/2 200
```

### Phase 10 — Private smoke test

```bash
asif-deploy ./examples/private-smoke --slug smoke --private
curl -sI https://smoke.asif-studio-private.pages.dev | head -5
# expect HTTP/2 302 (redirect to cloudflareaccess.com login)
```

### Phase 11 — AI surface wrappers

```bash
# Claude Code
mkdir -p ~/.claude/agents
cp wrappers/claude-code/site-deployer.md ~/.claude/agents/

# Cowork
open wrappers/cowork-skill/site-deployer.skill   # opens in Cowork → "Save skill"

# VS Code Copilot (user-level, available in every repo)
mkdir -p "$HOME/Library/Application Support/Code/User/prompts"
cp wrappers/copilot/deploy-site.prompt.md "$HOME/Library/Application Support/Code/User/prompts/"
# In VS Code settings.json: "chat.promptFiles": true
```

---

## Troubleshooting

### `wrangler whoami` says I'm logged in but `--doctor` says I'm not

Known quirk in our doctor — the CLI captures wrangler's stdout including its banner, which `grep` can match against. Doesn't affect actual deploys. Will be patched.

### Private deploy returns the content without prompting for login

Check that the Access application's `domain` field is `*.asif-studio-private.pages.dev` (with the wildcard). Without the wildcard, only the bare `asif-studio-private.pages.dev` is gated and your `<slug>.asif-studio-private.pages.dev` URLs slip through.

```bash
ACCT=...; TOKEN=...
curl -sS -H "Authorization: Bearer $TOKEN" "$CF_API/accounts/$ACCT/access/apps" \
  | jq '.result[] | {name, domain}'
```

### Login email never arrives (OTP)

- Cloudflare sends from `no-reply@notify.cloudflare.com`. Check spam.
- The login page expires the code after 5 minutes — request a fresh one.
- If you typed your email wrong on the login page, it'll silently never send. There's no "wrong email" error.

### `cf_api … unauthorized`

Token expired, revoked, or wrong scopes. Re-create with the scopes in §Phase 4 and re-run `./infra/setup.sh --reset-token --only 4`.

### Deploy succeeds but URL 404s

Check that `index.html` exists at the root of the deployed directory, not in a subfolder. Cloudflare Pages serves `<root>/index.html` for `/`. If your source has `dist/index.html`, deploy `./dist`, not the parent.

### "Zero Trust subscription required" on Access API calls

The account hasn't activated Zero Trust yet. Either re-run Phase 6, or open the dashboard once and accept the free plan terms.

---

## File layout in this directory

```
infra/
├── README.md         this file
└── setup.sh          fire-and-forget installer (run me)
```

That's it — deliberately flat. All operational knowledge lives in this one README; the script lives next to it.

## Plan-first gate note

Per podcast-factory's `CLAUDE.md`:

> **Plan-first execution gate (LOCKED 2026-05-27).** No pipeline work, code change, or new feature executes without … a plan entry … and Asif's explicit approval.

This `infra/` lives inside `asif-deploy`, **not** inside podcast-factory. The gate applies to podcast-factory pipeline work. asif-deploy is a sibling tool repo with its own lifecycle. If you ever want this material moved into podcast-factory, that's a plan entry + dashboard regen + approval.

The previous Cloudflare scaffold inside podcast-factory (`infra/cloudflare/`, `docs/cloudflare/`, `wrangler.toml`, etc.) was retired 2026-05-22. None of that has been recreated. Three orphan launchd plists (`com.asif.cloudflared-journal.plist`, `com.asif.babu-journal-proxy.plist`, `com.asif.babu-journal-static.plist`) referencing deleted journal scripts were deleted as part of this work — see the session log for evidence.
