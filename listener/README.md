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
npm run deploy     # build + wrangler deploy — see "Deploying" below
```

Content is pushed in from the repo root, not from here:

```bash
python3 scripts/podcast/publish_to_listener.py <slug> [--remote] [--dry-run]
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
| `app/server/catalog.server.ts` | What a unit CONTAINS. Decides nothing about access |
| `app/styles/reader.css` | The reading column, styled by the renderer's own class names |
| `scripts/session-cookie.mjs` | Mints a local dev session — no Google needed |
| `scripts/security-smoke.mjs` | The runtime gate checks |
| `scripts/render-chapters.mjs` | Bridge to plain-dashboard's `renderMarkdown` |

## Content

`scripts/podcast/publish_to_listener.py` reads one book out of
`content/<Bucket>/<slug>/` and writes its chapters, episodes and media inventory
into D1. It is the only writer of those tables.

**It never names `content_unit.status` or `open_to_all`.** Those two columns
decide whether a unit is readable and whether it is open to everyone; they belong
to the admin screens. When the publish step has to create a `content_unit` row it
omits both and lets the schema defaults apply, so a newly published book is a
draft nobody can see until a human says otherwise. `test/catalog.test.ts` greps
for exactly that.

**Chapter prose is rendered at publish time** by `renderMarkdown` from
`plan-dashboard/src/lib/reader/markdown.ts` — the same function behind the
printed PDF, so the page and the print edition cannot disagree about a paragraph.
That coupling is pinned by a golden fixture in `test/fixtures/`, which also
asserts that every class the renderer emits has a rule in `reader.css`.

**Chapters are keyed by `anchor_key`**, the Book Composer's own heading
normalisation, so a chapter keeps its identity across a re-compose that renumbers
it.

**Absence is the normal state.** Most books have no audio, most have no deck,
some have no PDF. Every list is allowed to be empty and every media reference is
nullable; a `media_asset` row with `uploaded_at` NULL means the file is on Asif's
disk but not in R2, and the site says so rather than offering a link that 404s.

**Episodes are not chapters.** *The Master and the Disciple* is nine chapters and
twenty episodes, drawn along different lines from the same source. The book page
shows both lists side by side under one title and says as much. The
`episode_chapter` bridge is populated ONLY from a hand-written
`_system/listener-episode-chapters.json`; nothing infers it, because a chapter
contract's `source_chapter_ref` points into a third segmentation again and a
wrong answer on a religious text is worse than none.

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

## Deploying

Live at **<https://podcast-factory.safinaverse.com>** since 2026-08-03, on the
`asifhussain60@gmail.com` Cloudflare account. `cf-deploy.sh` CANNOT deploy this
app — that script is Cloudflare Pages end to end and this is a Worker.

**Every remote command needs the account token in the environment**, because
`wrangler` on this machine is logged in as `asifhussain60@hotmail.com` and would
otherwise target the wrong account:

```bash
export CLOUDFLARE_API_TOKEN="$(security find-generic-password -s cloudflare_api_token -w | tr -d '[:space:]')"
export CLOUDFLARE_ACCOUNT_ID=19cb05067ea7e704f94481df1685ec51
npm run deploy
```

**`npm run deploy` exits non-zero even when it worked.** The Worker uploads
first and succeeds; wrangler then reads `/zones/{id}/workers/routes` to reconcile
the custom domain, and the account token is denied on that one endpoint. The
domain is already attached — it was attached through the ACCOUNT-level
`workers/domains` endpoint, which the same token is allowed to call. Check the
`Uploaded podcast-listener` line, not the exit code. See
`infra/cloudflare/README.md` §7.

**Probing production from a script does not work.** Bot Fight Mode on the zone
answers non-browser requests with a managed challenge, so `curl` gets a 403. To
run a scripted check, turn the workers.dev address on for the duration and off
again — see the comment on `workers_dev` in `wrangler.jsonc`.

## Open

- **The mark is not chosen.** All three are built; `DEFAULT_MARK` in
  `app/components/brand/Logo.tsx` is the one line that changes. `/brand` renders
  them side by side in every theme, at full size and at favicon size. Delete
  that route once the choice is made.
- **R2 is not enabled on the account**, so no media has been uploaded: the
  bucket create fails with "Please enable R2 through the Cloudflare Dashboard"
  (code 10042), and wrangler refuses to deploy a binding whose bucket does not
  exist, which is why `r2_buckets` is still commented out in `wrangler.jsonc`.
  Everything textual works without it. Once R2 is on: create the bucket,
  uncomment the binding, upload, and stamp `uploaded_at` on the `media_asset`
  rows — the UI turns each piece on by itself.
- **Notes and highlights are not built.** The design brief's "notes without a
  home" problem — a note anchored to a sentence a re-compose deleted — needs its
  own data model and is deliberately a separate phase.
- **Confirm the production redirect URI** is registered on the Google OAuth
  client: `https://podcast-factory.safinaverse.com/api/auth/callback/google`.
  Sign-in on the live site fails without it. See
  `_workspace/plan/listener-google-oauth.md`.
