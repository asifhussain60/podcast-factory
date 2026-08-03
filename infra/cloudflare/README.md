# Cloudflare — canonical reference

Everything needed to understand, deploy to, or recover this repo's Cloudflare
setup. **Last verified against the live API: 2026-08-03.** Every table below was
read from Cloudflare, not copied from an earlier document.

---

## 1. The account, and the one that is not it

| | |
|---|---|
| **Account** | `asifhussain60@gmail.com` |
| **Account ID** | `19cb05067ea7e704f94481df1685ec51` |
| **Zone** | `safinaverse.com` — id `2f20d3aca658682d767a232696362a50`, status **active** |
| **workers.dev subdomain** | `asifhussain60-19c` |
| **Dashboard** | <https://dash.cloudflare.com> |

**There is a second Cloudflare account, `asifhussain60@hotmail.com`
(`844bc687926c910d5ad9d79c40ad1f2f`), and nothing in this repo may deploy to
it.** It does not hold the `safinaverse.com` zone, so anything published there
can never be reached at a Safina address. It is named here only so the mistake
is recognisable — see §7, where it is an active hazard right now.

---

## 2. What is actually deployed today

Read from the API on 2026-08-03:

| Kind | Name | Address | Notes |
|---|---|---|---|
| Pages | `asif-academy` | `asif-academy.pages.dev` | No custom domain attached |
| Workers | *(none)* | — | The Listener would be the account's first Worker |

`podcast-factory.safinaverse.com` currently resolves to nothing. It is
unclaimed, and no Pages project is squatting on it.

---

## 3. Secrets, and where each one lives

Nothing secret is stored in this repo. Everything is either in the macOS
keychain (local development) or in Cloudflare's own secret store (production).

| Keychain service | What it is | Used by |
|---|---|---|
| `cloudflare_api_token` | Account-scoped Cloudflare API token | `cf-deploy.sh`; any manual API call |
| `listener_better_auth_secret` | Signs the Listener's session cookies | `listener/scripts/dev-vars.mjs` |
| `safina_google_client_secret` | Google OAuth client secret for Safina sign-in | `listener/scripts/dev-vars.mjs` |

### Rules that apply to all three

- **Asif stores and rotates them; no tool writes to the keychain.** The command
  prompts for the value rather than taking it as an argument, so it never enters
  shell history:

  ```bash
  security add-generic-password -U -a "$USER" -s <service> -w
  ```

- **Existence checks only.** `security find-generic-password -s <service>`
  without `-w` confirms an item is present without reading it. Scripts that must
  read a value (`dev-vars.mjs`) write it straight to a mode-600 file and never
  print it.

- **A stored token usually carries a trailing newline**, which produces
  Cloudflare API error `6111 Invalid format for Authorization header`. Strip it:
  `tr -d '[:space:]'`. `cf-deploy.sh` already does; a hand-rolled `curl` will not.

### The API token's actual permissions

Tested directly on 2026-08-03, because the token's scope list is not visible
anywhere else:

| Operation | Result |
|---|---|
| List zones | ✅ allowed |
| List Pages projects | ✅ allowed |
| List Workers scripts | ✅ allowed |
| Create/deploy Pages project | ✅ allowed (this is its main job) |
| **Read zone DNS records** | ❌ **denied** (`10000 Authentication error`) |
| `GET /user/tokens/verify` | ❌ denied — **expected, not a fault** |

That last row confuses people. This is an **account-owned** token, so it cannot
describe itself through the user endpoint. `cf-deploy.sh` printing
`Token can't read /user … skipping email check` is the same thing and is
correct behaviour.

The token deliberately excludes Billing, Members and API-Tokens, and is
Registrar read-only.

**Known gap:** it cannot read DNS, and whether it can *attach a Workers custom
domain* is untested — that needs a write call nobody has made yet. If a Workers
domain attach fails on permissions, add **Workers Routes: Edit** on the zone
(and **DNS: Edit** if a standalone record is ever needed).

---

## 4. Deploying a Pages site — `cf-deploy.sh`

Location: `~/PROJECTS/cloudflare-safina/cf-deploy.sh` (a separate repo, not this
one). Requires `jq`, `curl`, and `wrangler` or `npx`.

It hard-aborts unless account `19cb0506…` is visible to the token, which is what
stops a wrong-account deploy.

| Command | Effect |
|---|---|
| `cf-deploy.sh whoami` | Verify identity and account |
| `cf-deploy.sh list` | List Pages projects |
| `cf-deploy.sh deploy <app> <dir>` | Create-or-reuse a project, deploy `<dir>`, attach `<app>.safinaverse.com` |
| `cf-deploy.sh placeholder <app>` | Deploy a generated "coming soon" page and attach the subdomain |
| `cf-deploy.sh root <dir>` | Deploy to the apex (`safinaverse.com` + `www`) |
| `cf-deploy.sh domain <project> <fqdn>` | Attach an extra domain to an existing project |

**DNS and SSL are automatic.** Attaching a custom domain to a Pages project
makes Cloudflare create the record and issue the certificate itself. That is why
the token needs no DNS write permission for the Pages path.

**Convention:** one Pages project per app, named `<app>`, served at
`<app>.safinaverse.com`. Re-deploying updates in place; the domain attaches once.

---

## 5. Deploying a Worker — a different path entirely

**`cf-deploy.sh` cannot deploy a Worker.** It is Cloudflare Pages end to end —
`wrangler pages deploy` and the `/pages/projects/{name}/domains` API. Pages and
Workers are different products with different APIs, and a Worker with static
assets is not a Pages project.

The **Podcast Factory Listener** (`listener/`) is a Worker. It deploys with:

```bash
cd listener && npm run deploy      # npm run build && wrangler deploy
```

Its custom domain is declared in `listener/wrangler.jsonc` rather than attached
by a script:

```jsonc
"routes": [{ "pattern": "podcast-factory.safinaverse.com", "custom_domain": true }],
"workers_dev": false
```

That route only resolves on the account holding the zone, so a deploy from the
wrong account **fails loudly instead of silently publishing somewhere wrong.**
That is deliberate.

### Before the first Worker deploy

1. Fix the wrangler login (§7) — nothing else matters until then.
2. Create the D1 database and put the real id in `wrangler.jsonc`; the committed
   `database_id` is a placeholder that local Miniflare never reads:
   ```bash
   cd listener && npx wrangler d1 create podcast-listener
   npx wrangler d1 migrations apply podcast-listener --remote
   ```
3. Upload the production secrets — never the local development values:
   ```bash
   npx wrangler secret put BETTER_AUTH_SECRET      # openssl rand -base64 32, a FRESH one
   npx wrangler secret put GOOGLE_CLIENT_SECRET    # the same Google client secret
   ```
   `GOOGLE_CLIENT_ID` is **not** a secret and already sits in `wrangler.jsonc`
   under `vars`; it travels in the browser's address bar during sign-in.
4. Confirm the Google OAuth client lists the production redirect URI —
   `https://podcast-factory.safinaverse.com/api/auth/callback/google`. See
   `_workspace/plan/listener-google-oauth.md`.

---

## 6. Verifying the setup

All read-only, all safe to run at any time:

```bash
# Identity and account. The "can't read /user" line is expected.
~/PROJECTS/cloudflare-safina/cf-deploy.sh whoami

# What Pages projects exist.
~/PROJECTS/cloudflare-safina/cf-deploy.sh list

# Which account wrangler itself is logged into — see §7.
cd listener && npx wrangler whoami

# Keychain items present, without reading any value.
for s in cloudflare_api_token listener_better_auth_secret safina_google_client_secret; do
  security find-generic-password -s "$s" >/dev/null 2>&1 \
    && echo "ok      $s" || echo "MISSING $s"
done

# Has the subdomain been claimed yet?
dig +short podcast-factory.safinaverse.com
```

---

## 7. Open hazard — wrangler is logged into the wrong account

As of 2026-08-03, `wrangler whoami` reports **`asifhussain60@hotmail.com`**
(account `844bc687926c910d5ad9d79c40ad1f2f`). Its stored OAuth credentials live
at `~/Library/Preferences/.wrangler/config/default.toml`.

This matters because `wrangler` prefers its own stored login over the keychain
token, so `npm run deploy` today would target the wrong account.

Two ways to fix it, in order of preference:

```bash
# Preferred: use the account-scoped token for this command only. Nothing persists.
export CLOUDFLARE_API_TOKEN="$(security find-generic-password -s cloudflare_api_token -w | tr -d '[:space:]')"
export CLOUDFLARE_ACCOUNT_ID=19cb05067ea7e704f94481df1685ec51
cd listener && npm run deploy
```

```bash
# Alternative: re-authenticate wrangler as the gmail account. This replaces the
# stored login globally, affecting every other project on this machine that
# relies on it.
npx wrangler login
```

---

## 8. What used to be in this directory

Until 2026-08-03 this held a deployment record for **`salty-lamps-proposal`**, a
separate personal project unrelated to podcast-factory. It was removed because
it was **wrong in a way that mattered**: it stated
`Cloudflare account: asifhussain60@gmail.com`, and the gmail account has only
ever held `asif-academy`. The project is in fact on the hotmail account. A
document that names the wrong account is worse than no document, because it
invites exactly the mistake §7 exists to prevent.

The site is still live at `salty-lamps-proposal.pages.dev`, and its source repo
is not on this machine. Nothing was destroyed — git keeps every version:

```bash
git log --oneline --diff-filter=D -- infra/cloudflare/salty-lamps-proposal.md
git show <sha>^:infra/cloudflare/salty-lamps-proposal.md
```

Its Supabase companion moved to `SaltyLamps/infra/supabase-proposal-notes.md`
on the same day, so no Salty Lamps material remains in this repo.
