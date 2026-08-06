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

Read from the API on 2026-08-03, after the Podcast Factory Library went live:

| Kind | Name | Address | Notes |
|---|---|---|---|
| Pages | `asif-academy` | `asif-academy.pages.dev` | No custom domain attached |
| Workers | `podcast-listener` | `podcast-factory.safinaverse.com` | The account's first Worker |
| D1 | `podcast-listener` | `ed6e00d2-ec8f-47bf-af5d-66ffc43e79c0` | region ENAM |
| R2 | `podcast-listener-media` | bound as `env.MEDIA` | Standard class, ENAM, 139 MB |

The Worker's workers.dev address is deliberately **off**: the custom domain is
the only way in. Turn it on temporarily only to run a scripted check (§6).

---

## 3. Secrets, and where each one lives

Nothing secret is stored in this repo. Everything is either in the macOS
keychain (local development) or in Cloudflare's own secret store (production).

| Keychain service | What it is | Used by |
|---|---|---|
| `cloudflare_api_token` | Account-scoped Cloudflare API token | `cf-deploy.sh`; any manual API call |
| `listener_better_auth_secret` | Signs the Podcast Factory Library's session cookies | `listener/scripts/dev-vars.mjs` |
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
| List / upload Workers scripts | ✅ allowed |
| Create/deploy Pages project | ✅ allowed |
| Create a D1 database, run migrations | ✅ allowed |
| `wrangler secret put` | ✅ allowed |
| Attach a Workers custom domain, **account** endpoint | ✅ allowed — `PUT /accounts/{acc}/workers/domains` |
| Attach a Workers route, **zone** endpoint | ❌ denied — `/zones/{id}/workers/routes` |
| Read zone settings (`security_level`, bot management) | ❌ denied (`9109` / `10000`) |
| **Read zone DNS records** | ❌ **denied** (`10000 Authentication error`) |
| Create an R2 bucket, put and get objects | ✅ allowed (since R2 was enabled 2026-08-03) |
| `GET /user/tokens/verify` | ❌ denied — **expected, not a fault** |

The two Workers rows are the ones that matter and they are easy to misread. The
token CAN attach a custom domain — that is how `podcast-factory.safinaverse.com`
was attached — but only through the ACCOUNT-level endpoint. `wrangler deploy`
reaches for the ZONE-level one to reconcile its `routes` config, is denied, and
exits non-zero **after the Worker has already uploaded successfully**. Read the
`Uploaded podcast-listener` line rather than the exit code. Adding
**Workers Routes: Edit** on the zone to the token would remove the noise; nothing
is broken without it.

The last row confuses people. This is an **account-owned** token, so it cannot
describe itself through the user endpoint. `cf-deploy.sh` printing
`Token can't read /user … skipping email check` is the same thing and is
correct behaviour.

The token deliberately excludes Billing, Members and API-Tokens, and is
Registrar read-only.

**Known gap:** it cannot read zone DNS records or zone settings. Neither has
blocked anything — Pages and Workers custom domains both create their own DNS —
but if a standalone record is ever needed, add **DNS: Edit** on the zone.

### R2

R2 needs a one-time account opt-in in the dashboard before any bucket can exist;
without it every create is refused with `10042`. Asif enabled it on 2026-08-03
and the Podcast Factory Library's media went up the same day. The free tier is 10 GB of storage,
1M Class A and 10M Class B operations a month, and — the part that matters for
audio — **no egress charge at all**. At 139 MB the library uses about 1.4% of the
storage allowance.

Beware `wrangler r2 bucket info`: it reported `object_count: 0` and
`bucket_size: 0 B` immediately after 21 objects were uploaded successfully,
because those figures come from usage metrics that lag by hours rather than from
the bucket. To know whether an object is really there, fetch it back and compare:

```bash
npx wrangler r2 object get podcast-listener-media/<key> --remote --file=/tmp/x
shasum -a 256 /tmp/x
```

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

The **Podcast Factory Library** (`listener/`) is a Worker, and it is deployed —
live since 2026-08-03. It deploys with:

```bash
export CLOUDFLARE_API_TOKEN="$(security find-generic-password -s cloudflare_api_token -w | tr -d '[:space:]')"
export CLOUDFLARE_ACCOUNT_ID=19cb05067ea7e704f94481df1685ec51
cd listener && npm run deploy      # npm run build && wrangler deploy
```

The token exports are not optional — see §7.

Its custom domain is declared in `listener/wrangler.jsonc` rather than attached
by a script:

```jsonc
"routes": [{ "pattern": "podcast-factory.safinaverse.com", "custom_domain": true }],
"workers_dev": false
```

That route only resolves on the account holding the zone, so a deploy from the
wrong account **fails loudly instead of silently publishing somewhere wrong.**
That is deliberate.

### What the first deploy actually did — 2026-08-03

All of it with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` exported (§7),
which makes wrangler ignore its hotmail login for that command.

1. `wrangler d1 create podcast-listener` → `ed6e00d2-ec8f-47bf-af5d-66ffc43e79c0`,
   written into `wrangler.jsonc`. Local Miniflare never reads that id.
2. `wrangler d1 migrations apply podcast-listener --remote` — four migrations.
3. Secrets, generated or read and piped so no value was ever printed:
   ```bash
   openssl rand -base64 32 | npx wrangler secret put BETTER_AUTH_SECRET
   security find-generic-password -s safina_google_client_secret -w \
     | tr -d '\n' | npx wrangler secret put GOOGLE_CLIENT_SECRET
   ```
   The production `BETTER_AUTH_SECRET` is a FRESH value, not the development one,
   and is kept nowhere but Cloudflare — losing it costs one re-generate, which
   signs everyone out and nothing worse. `GOOGLE_CLIENT_ID` is **not** a secret
   and sits in `wrangler.jsonc` under `vars`; it travels in the browser's address
   bar during sign-in.
4. `npm run deploy` — Worker uploaded, then the routes reconcile failed on
   permissions (§3). Not fatal.
5. The custom domain, attached by hand through the endpoint the token CAN reach:
   ```bash
   curl -X PUT -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
     -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/domains" \
     --data '{"environment":"production","hostname":"podcast-factory.safinaverse.com",
              "service":"podcast-listener","zone_id":"2f20d3aca658682d767a232696362a50"}'
   ```
   DNS and the certificate follow automatically. This is a one-time step;
   later deploys keep the domain.
6. Content: `python3 scripts/podcast/publish_to_listener.py <slug> --remote`.

**Still outstanding:** confirm the Google OAuth client lists the production
redirect URI `https://podcast-factory.safinaverse.com/api/auth/callback/google`,
or sign-in on the live site cannot complete. See
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

# The Podcast Factory Library's address resolves to Cloudflare.
dig +short podcast-factory.safinaverse.com
```

### Why `curl https://podcast-factory.safinaverse.com` returns 403

Something on the zone — Bot Fight Mode, most likely — answers non-browser
traffic with a managed challenge: `cf-mitigated: challenge`, an interstitial
body, no Worker involved. A real browser passes it and never sees it. The token
cannot read zone settings, so this was identified from the response headers
rather than from configuration.

It only matters for scripted checks. To run one, turn the workers.dev address on
for the duration and off again — workers.dev is a different zone, so the
challenge does not apply:

```bash
ACC=19cb05067ea7e704f94481df1685ec51
curl -s -X POST -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/scripts/podcast-listener/subdomain" \
  --data '{"enabled":true,"previews_enabled":false}'

# ... probe https://podcast-listener.asifhussain60-19c.workers.dev ...
# Allow ~30s: the address 404s until it propagates.

# And OFF again. The site is invite-only; a second public address is a second
# thing to remember about.
curl -s -X POST ... --data '{"enabled":false,"previews_enabled":false}'
```

---

## 7. Standing hazard — wrangler is logged into the wrong account

`wrangler whoami` reports **`asifhussain60@hotmail.com`** (account
`844bc687926c910d5ad9d79c40ad1f2f`). Its stored OAuth credentials live at
`~/Library/Preferences/.wrangler/config/default.toml`.

Every remote command in this document therefore exports the token first.
**Verified 2026-08-03:** with `CLOUDFLARE_API_TOKEN` set, `wrangler whoami`
reports the gmail account and says *"The API Token is read from the
CLOUDFLARE_API_TOKEN environment variable"* — the environment beats the stored
login, so the token route is sufficient and nothing global has to change.

The hazard is only that forgetting the export is silent: the command runs, it
just runs somewhere else. `wrangler.jsonc` names the real custom domain, which is
what turns a wrong-account deploy into a loud failure rather than a quiet one.

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
