# Cloudflare Pages — salty-lamps-proposal

Full deployment record for the Salty Lamps website redesign proposal site.

**Last reconciled:** 2026-05-31

---

## TL;DR (redeploy from scratch)

```bash
cd "Salty Lamps/salty-lamps-proposal"
./cloudflare-deploy.command     # double-click in Finder, or run in terminal
```

The script handles: wrangler install → Cloudflare login → `npm run build` → `wrangler pages deploy`.

---

## Project details

| Field | Value |
|---|---|
| **Project name** | `salty-lamps-proposal` |
| **Live URL** | https://salty-lamps-proposal.pages.dev |
| **Deployment alias** | https://main.salty-lamps-proposal.pages.dev |
| **Cloudflare account** | asifhussain60@gmail.com |
| **Production branch** | `master` |
| **Build command** | `npm run build` |
| **Build output dir** | `dist` |
| **Framework** | React 18 + Vite 5 |
| **CDN** | Cloudflare global edge (free tier) |
| **SSL** | Automatic (Cloudflare-managed) |
| **Plan** | Free — unlimited bandwidth, 500 builds/month |

---

## Repository location

```
/Users/asifhussain/PROJECTS/DevProjects/Salty Lamps/salty-lamps-proposal/
```

Git repo root is one level up: `/Users/asifhussain/PROJECTS/DevProjects/Salty Lamps/`  
Branch: `master`

---

## Deploy script

`salty-lamps-proposal/cloudflare-deploy.command` — double-click in Finder or run in terminal.

What it does (4 steps):
1. `npm install --save-dev wrangler` — installs wrangler locally if needed
2. `npx wrangler login` — opens browser OAuth flow; authenticate as asifhussain60@gmail.com
3. `npm run build` — Vite production build → `dist/`
4. `npx wrangler pages deploy dist --project-name salty-lamps-proposal --branch master`

### Manual deploy (without the script)

```bash
cd "Salty Lamps/salty-lamps-proposal"
npm run build
npx wrangler pages deploy dist \
  --project-name salty-lamps-proposal \
  --branch master \
  --commit-dirty=true
```

---

## Environment variables

Vite bakes `VITE_*` env vars into the JS bundle at build time. They live in `.env.local` at the project root (not committed to git).

| Variable | Value | Purpose |
|---|---|---|
| `VITE_SUPABASE_URL` | `https://babguqugvxagijmnsgsj.supabase.co` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | `sb_publishable_8rpQsGmtH11e1UM2FEuWtg_7U6qXylD` | Supabase publishable key (safe for browser) |

**Important:** Because Vite bakes these at build time, `.env.local` must be present and populated before running `npm run build`. The deployed JS bundle contains the values — Cloudflare Pages environment variables are NOT needed separately.

`.env.local` template:
```
VITE_SUPABASE_URL=https://babguqugvxagijmnsgsj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_8rpQsGmtH11e1UM2FEuWtg_7U6qXylD
```

---

## Known issue — wrangler.toml warning

Every deploy prints this warning:

```
▲ [WARNING] Pages now has wrangler.toml support.
  We detected a configuration file at .../wrangler.toml but it is missing
  the "pages_build_output_dir" field, required by Pages.
```

**Fix (when needed):** add `pages_build_output_dir = "dist"` to `wrangler.toml`. Currently suppressed with `--commit-dirty=true` flag; the warning is cosmetic and does not affect deployment.

---

## Wrangler

- **Version in use:** 4.95.0 (installed locally per-project, not global)
- **Auth:** OAuth via browser — `npx wrangler login` — tied to asifhussain60@gmail.com
- **Token storage:** `~/.wrangler/config/` (managed by wrangler automatically)

---

## What's deployed

The proposal site is a 7-tab interactive presentation for the Salty Lamps website redesign project:

| Tab | Content |
|---|---|
| Cover | Intro and value proposition |
| Diagnosis | Current site audit + vision docs |
| Strategy | Competitor analysis + B2C/B2B marketing strategy |
| Design | Homepage wireframe + tech stack + site blueprint |
| Growth | SEO ranking strategy + organic traffic timeline |
| Roadmap | 6-phase build plan (20 weeks) |
| Pricing | Hosting cost tiers (dev = £0; services scale with traffic) |

**Notes panel:** A global slide-in panel (✏️ Notes button on the nav bar) with:
- Freeform text notes tab (autosaved)
- Brainstorm board tab (draggable post-its via `react-rnd`)
- Both persist to Supabase (see `supabase/salty-lamps-notes.md`) and localStorage

---

## Tech stack

```
React 18 + Vite 5
Tailwind CSS v4
react-rnd 10.5.3        — draggable post-it board
@supabase/supabase-js   — notes persistence
Cloudflare Pages        — hosting + CDN + SSL
```

---

## Quick-reference URLs

| Surface | URL |
|---|---|
| Live site | https://salty-lamps-proposal.pages.dev |
| Cloudflare Pages dashboard | https://dash.cloudflare.com/pages |
| Cloudflare account home | https://dash.cloudflare.com |
| Wrangler docs | https://developers.cloudflare.com/workers/wrangler/ |

---

## See also

- [`supabase/salty-lamps-notes.md`](../supabase/salty-lamps-notes.md) — Supabase project wired to this site's notes panel.
- [`cloudflare/README.md`](README.md) — index of all Cloudflare projects.
