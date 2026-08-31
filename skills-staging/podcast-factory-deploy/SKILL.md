---
name: podcast-factory-deploy
description: "Deploy and run the podcast-factory repo's two components — the podcast-listener Cloudflare Worker (listener/, 'Podcast Factory Library') and the plan-dashboard Astro app (plan-dashboard/, 'Podcast Factory Astro Site') — for local and prod environments. ALWAYS invoke when the user says 'deploy the listener', 'deploy podcast-factory', 'push the listener live', 'deploy to podcast-factory.safinaverse.com', 'run plan-dashboard', 'preview the dashboard', 'ship the podcast site', or any request to build, run, or ship either component of this repo. Scoped ONLY to this repo — do not use for other Cloudflare/Safina deploys (see the account-level cloudflare-safina skill for that)."
---

# podcast-factory deploy

Project-scoped skill for `~/PROJECTS/podcast-factory`. Handles the two independently-deployable
pieces of this repo. They are NOT deployed together — always confirm which one (or both) the
user means before running anything.

## Component 1 — listener/ ("Podcast Factory Library")

A Cloudflare Worker (React Router + D1 + R2), the audience-facing site.

- **Account**: `asifhussain60@gmail.com` (Cloudflare account id `19cb05067ea7e704f94481df1685ec51`), zone `safinaverse.com`. This is the ONLY account this repo may deploy to — never proceed if the resolved account differs.
- **Prod URL**: `https://podcast-factory.safinaverse.com`
- **D1 database**: `podcast-listener` (`ed6e00d2-ec8f-47bf-af5d-66ffc43e79c0`, region ENAM)
- **R2 bucket**: `podcast-listener-media` (bound as `env.MEDIA`)

### Local
```bash
cd listener
npm run dev              # boots on the local dev server, Miniflare's own D1 + R2, no prod creds needed
npm run db:migrate       # wrangler d1 migrations apply podcast-listener --local
npm run db:seed:local    # seed-local-catalog.mjs
```

### Prod
Prefer the wrapper script over a bare `wrangler deploy` — it enforces the correct account and
also pushes book content/media, not just the Worker:
```bash
scripts/podcast/deploy_listener.sh <slug> [<slug> ...] [--dry-run] [--worker-only]
scripts/podcast/deploy_listener.sh --all [--dry-run]
```
- `--all` only re-pushes books the Listener already has — it will not publish a new book by itself. A book needs to be named explicitly the first time.
- Bare `npm run deploy` inside `listener/` (→ `wrangler deploy`) is fine for a **worker-only** push when you don't need content/media sync.
- **A non-zero exit from `wrangler deploy` is expected and not a failure** — the token can't reconcile the zone-level `workers/routes` endpoint, but the Worker itself has already uploaded through the account-level endpoint by then. Confirm success by the presence of the `Uploaded podcast-listener` line in the output, not the exit code.
- Never deploy from a token/account other than the one above; `deploy_listener.sh` checks this itself — do not bypass that check.
- Deploying never makes a book publicly visible — that's a separate manual toggle in `/admin` (`content_unit.status` / `open_to_all`). Don't imply a deploy "published" a book.

## Component 2 — plan-dashboard/ ("Podcast Factory Astro Site")

Astro app (Node adapter, SSR, standalone mode) — the internal planning/status dashboard
(Overview, Architecture, Infrastructure, Live Dashboard pages with an SSE feed).

### Local
```bash
cd plan-dashboard
npm install
npm run dev        # http://localhost:4322
npm run snapshot    # mechanical refresh of the three data snapshots (src/data/*.json), safe for CI
npm run build       # astro build, for a production bundle
npm run preview     # astro preview, serves the built bundle locally
```

### Prod — NOT SET UP YET
As of this skill's creation there is no deploy pipeline for plan-dashboard anywhere in this
repo: no Cloudflare Pages project, no wrangler config, no CI deploy job. It has only ever been
run locally or previewed locally (`npm run build && npm run preview`).

**Do not fabricate a prod deploy path.** If the user asks to "deploy plan-dashboard to prod":
1. Say plainly that no prod pipeline exists yet for this component.
2. Ask whether they want to set one up now (e.g. a new Cloudflare Pages project on the same
   Safina account, or a different host — the Node/SSR adapter means it needs a server, not
   static Pages hosting, unless the adapter is changed first).
3. Once a real path exists, update this section of the skill with the actual commands, the
   same way listener's section above is documented — don't leave future-you guessing either.

## Boundaries

- This skill never touches other repos or other Cloudflare projects on the Safina account
  (e.g. `asif-academy`). For anything outside podcast-factory, use the account-level
  cloudflare-safina skill instead.
- Secrets are never read or printed. Existence-check only
  (`security find-generic-password -s <service>`, no `-w`). See `infra/cloudflare/README.md`
  for the full secrets table if a value genuinely needs rotating — that's a human, not this skill.
