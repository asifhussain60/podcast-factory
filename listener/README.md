# Podcast Factory Listener

The audience-facing site: sign in, listen, read, annotate. Deployed to Cloudflare
Workers on its own subdomain.

**This is not the admin site.** `plan-dashboard/` is the authoring tool Asif uses
(the Book Composer, intake, pipeline views). The two share a repository and
nothing else — the Listener has its own dependencies, its own palette, its own
database, and imports nothing from `plan-dashboard/` at runtime.

## Why it lives in this repo

The publish step has to run on the machine that holds the media. Audio
(`content/**/m4a/**`), book PDFs (`content/**/book/*.pdf`) and deck page images
are all gitignored, so they exist only on Asif's disk — and that disk has this
repo checked out. Same-repo also lets `publish_to_listener.py` import
`find_content` from `scripts/podcast/_paths.py` directly instead of maintaining a
copy that would drift.

## Stack

React 19 · React Router 8 (framework mode) · Vite 8 · Tailwind 4 · Cloudflare
Workers, D1 and R2 · Better Auth with Google.

Server rendering is on because it lets one `<audio>` element live in the root
layout and survive every navigation, and because it puts the API in the same
Worker as the UI. It is **not** here for SEO — the site is invite-only and
`robots` is `noindex`.

## Commands

```bash
npm install
npm run fonts      # copies the self-hosted faces into public/fonts/
npm run dev        # real workerd via @cloudflare/vite-plugin
npm run typecheck
npm run build
npm run deploy
```

`npm run fonts -- --check` verifies the committed faces are current without
writing; it is the gate that catches a stale copy.

## Layout

| Path | What |
|---|---|
| `app/root.tsx` | Document shell, theme bootstrap, error boundary |
| `app/routes.ts` | Route table |
| `app/styles/` | `theme.css` is the Verdigris palette; `fonts.css` the faces |
| `app/components/brand/` | The three candidate marks and the wordmark lockups |
| `workers/app.ts` | Worker entry — hands every request to React Router |
| `wrangler.jsonc` | Bindings, staged per phase |
| `migrations/` | D1 migrations, added from phase 2 |

## Theme

Verdigris: warm-neutral stone, aged-copper accent, in its own `--l-*` namespace
so an admin-site `--c-*` token pasted in is inert rather than subtly wrong.
Three real themes — light, sepia, dark — switched by `data-theme` on `<html>`,
with an inline script in `<head>` that applies the stored choice before first
paint.

Tailwind utilities come from `@theme inline` mapping onto those runtime
variables, so `bg-l-surface` follows the active theme rather than baking a
colour in at build time.

## Open

- **The mark is not chosen.** All three are built; `DEFAULT_MARK` in
  `app/components/brand/Logo.tsx` is the one line that changes. `/brand` renders
  them side by side in every theme, at full size and at favicon size. Delete
  that route once the choice is made.
- **The domain is not set.** `wrangler.jsonc` ships on `workers_dev` until Asif
  supplies the Cloudflare zone; then swap in a `custom_domain` route and add the
  Google OAuth redirect URI.
- **D1 and R2 bindings are commented out** in `wrangler.jsonc` — Wrangler fails
  the build on a binding whose resource does not exist, so each is uncommented
  in the phase that creates it.
