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
npm run db:migrate # applies migrations to the local D1
npm run dev        # real workerd via @cloudflare/vite-plugin, on :5273
npm run check      # typecheck + unit tests + build
npm run security   # runtime gate checks; needs `npm run dev` in another shell
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
| `app/server/*.server.ts` | Server-only. The suffix is enforced by the build |
| `app/middleware/` | The four gates. See "Access" below |
| `migrations/` | D1 migrations |
| `scripts/session-cookie.mjs` | Mints a local dev session — no Google needed |
| `scripts/security-smoke.mjs` | The runtime gate checks |

## Access

The site is invite-only AND per-book. Being invited lets you sign in; it does
not, by itself, let you see anything.

**The route tree is the policy.** `app/routes.ts` gates by POSITION — a route is
protected because of where it sits, never because code compared a pathname.
`compilePath` matches case-insensitively, so `/Admin/people` defeats any
`startsWith("/admin")` check. `test/routes.test.ts` fails if a route is added
outside the gate.

Four layers:

| Layer | Where | What it decides |
|---|---|---|
| 0 | `workers/app.ts` | `/api/auth/*` bypasses the router entirely, so sign-in needs no carve-out anywhere else |
| 1 | `root.tsx` | Resolves the session into context. Gates nothing |
| 2 | `routes/_authed.tsx` | Signed in, invited, not revoked. Signed out redirects; signed-in-but-not-invited does not |
| 3 | `routes/_authed._admin.tsx` | `ADMIN_EMAIL` only. 404, never 403 |
| 4 | `routes/book.$slug.tsx` | May read this unit |

**Gates are `middleware`, never loaders.** A loader gate is defeated by one
query parameter: `_routes` feeds `filterMatchesToLoad`, so
`/book/x.data?_routes=routes/book.$slug` runs the child loader and skips the
parent. Middleware wraps the whole dispatch, where that filter cannot reach.
`npm run security` fires exactly that request, plus a control proving the filter
really was applied.

**Grants key on email, not user id**, so access can be given to someone who has
never signed in. That makes the address a privilege bit, so every comparison —
the admin check and the grant lookup — goes through `normalizeEmail` in
`app/server/email.server.ts`. Dots and `+tags` fold on Gmail only; folding them
elsewhere would merge two different people.

**There is no admin bypass in the resolver.** Admin governs `/admin` and nothing
else; reading follows one rule for everyone, so there is one path to audit. The
administrator gets an ordinary seeded `library:*` grant, visible and revocable
in the UI like any other.

**Denial is 404, never 403**, and only `app/root.tsx` may export an
`ErrorBoundary` — a second boundary would make a denied 404 look different from
a real one and reveal which slugs exist.


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
- **No Google OAuth client yet.** Everything runs without one; only real
  sign-in cannot complete. `scripts/session-cookie.mjs` mints a valid local
  session so the gates are all provable meanwhile.
- **Wrangler is logged in to the wrong Cloudflare account.** It holds
  `asifhussain60@hotmail.com`; the `safinaverse.com` zone lives on the gmail
  account (`19cb05067ea7e704f94481df1685ec51`). `wrangler.jsonc` names the real
  custom domain, so `npm run deploy` fails loudly rather than publishing
  somewhere wrong. Note also that `cf-deploy.sh` CANNOT deploy this app — it is
  Pages-only, and this is a Worker.
- **`database_id` is a placeholder.** Local dev uses Miniflare's D1 and never
  reads it. The real one comes from `wrangler d1 create podcast-listener` run
  against the gmail account at deploy time.
- **The R2 binding is still commented out** — Wrangler fails the build on a
  binding whose resource does not exist, so it is uncommented in phase 3.
