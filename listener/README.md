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

Going live is one command, run from the repo root:

```bash
scripts/podcast/deploy_listener.sh <slug> [<slug> …] [--dry-run]
```

It verifies the Cloudflare account, deploys the Worker, publishes each book and
uploads its media — and it never writes `status` or `open_to_all`, so nothing it
does can make a book visible. `publish_to_library.py` calls it at the end of a
normal publish; `--skip-listener` opts out. The two halves can also be run alone:

```bash
python3 scripts/podcast/publish_to_listener.py <slug> [--remote] [--dry-run]
python3 scripts/podcast/upload_listener_media.py [<slug>] [--remote] [--dry-run]
```

`npm run fonts -- --check` verifies the committed faces are current without
writing; it is the gate that catches a stale copy.

## Layout

| Path | What |
|---|---|
| `app/root.tsx` | Document shell, theme bootstrap, error boundary |
| `app/routes.ts` | Route table |
| `app/styles/podcast-factory.css` | The WHOLE design system, in seven numbered sections. §3 is the only place a palette lives |
| `app/components/brand/` | The mark and the wordmark lockups |
| `workers/app.ts` | Worker entry — hands every request to React Router |
| `wrangler.jsonc` | Bindings, staged per phase |
| `app/server/*.server.ts` | Server-only. The suffix is enforced by the build |
| `app/middleware/` | The four gates. See "Access" below |
| `migrations/` | D1 migrations |
| `app/server/catalog.server.ts` | What a unit CONTAINS. Decides nothing about access |
| `app/styles/podcast-factory.css` §7 | The reading column, styled by the renderer's own class names |
| `scripts/session-cookie.mjs` | Mints a local dev session — no Google needed |
| `scripts/security-smoke.mjs` | The runtime gate checks |
| `scripts/smoke.mjs` | `npm run smoke` — every route, three identities, four widths |
| `scripts/shots.mjs` | `npm run shots` — the same, as PNGs to look at |
| `scripts/routes.mjs`, `scripts/fixtures.mjs` | What those two share: the route manifest and the test identities |
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
asserts that every class the renderer emits has a rule in §7.

**Chapters are keyed by `anchor_key`**, the Book Composer's own heading
normalisation, so a chapter keeps its identity across a re-compose that renumbers
it.

**Absence is the normal state.** Most books have no audio, most have no deck,
some have no PDF. Every list is allowed to be empty and every media reference is
nullable; a `media_asset` row with `uploaded_at` NULL means the file is on Asif's
disk but not in R2, and the site says so rather than offering a link that 404s.

`upload_listener_media.py` is what turns those rows into objects, and it is a
separate script because it is the slow part (one recording is 70 MB) and the
retryable part. It stamps each row the moment that file lands rather than all of
them at the end, so an interrupted run leaves the site telling the truth about
exactly what is there. `media_asset` is also the one table the publish step does
NOT clear and rewrite: `uploaded_at` survives a re-publish when the file's sha256
is unchanged and is cleared when it is not — otherwise fixing a typo in one
chapter would report every recording as vanished and re-upload all of them.

**Episodes are not chapters.** *The Master and the Disciple* is nine chapters and
twenty episodes, drawn along different lines from the same source. The book page
shows both lists side by side under one title and says as much. The
`episode_chapter` bridge is populated ONLY from a hand-written
`_system/listener-episode-chapters.json`; nothing infers it, because a chapter
contract's `source_chapter_ref` points into a third segmentation again and a
wrong answer on a religious text is worse than none.

**Episodes group into SESSIONS, and the folder names are the source.** Recordings
live at `m4a/Episodes/`: `Audio/` holds the untouched masters, and one folder per
session named `Session 2 — Spiritual Symbols: The Architecture of Creation` holds
the mp3s that actually ship. Number and title are read off that folder name;
nothing is inferred from episode counts or runtimes. The SQL table is
`book_session`, not `session` — Better Auth owns that name.

A session's number is its POSITION IN THE SERIES, never its index in the source.
Degrees of Excellence went live under a lone "Session 4" — one folder, numbered
from the source chapter the treatise happens to occupy — which reads to a reader
as a book missing three of its parts. `publish_to_listener.session_concerns` now
reports non-contiguous numbering, and reports a book whose plan derives sessions
it has no folders for, as a note beside `unmatched_audio`. It never blocks: the
folders stay authoritative, because inferring the grouping instead would start
publishing groupings for half-recorded books.

**A book too small for sessions is FLAT, and that is a third layout.** Under the
eight-episode threshold the recordings sit straight in `m4a/Episodes/` with no
`Session N` folder at all — Ayyuha al-Walad's four. Until 2026-08-04 this shape
was read by neither branch (the session scan collects only directories, the loose
scan does not recurse), so such a book attached zero recordings *and* reported
nothing unmatched. All three layouts are pinned by
`scripts/podcast/tests/test_listener_book.py`.

**Arranging recordings into `m4a/Episodes/` is what marks a podcast finished.**
Files loose in `m4a/` are working files and are never uploaded: that folder is
where raw NotebookLM output lands under whatever name it was given, for a podcast
that may be half-made. The publish step reports them and moves on.

**A book may have SEVERAL slide decks, one per chapter.** That is the pipeline's
default (`_content_profile.slide_deck_mode`; `book` is the override), and the
Listener was the piece out of step — it looked in one hardcoded folder and keyed
pages `<slug>/deck/page-NN.jpg`, so four decks all offering `page-01.jpg` collided
on the primary key and three vanished. Since migration 0010 the key carries the
deck and `media_asset` holds `deck_id` + `deck_title`. A deck is named from its
own source's H1, never from the reading chapter of the same ordinal: deck folders
are numbered against the podcast chapter set, which for several books is a
different segmentation. The Slides tab draws a chooser only when there is more
than one deck.

**The page adapts to what a book has.** Two columns only when there is both a
reading edition and a podcast you can actually play; one half alone gets the full
width. A book with episodes but no recordings gets no Listen column at all — the
summary line says how many are planned instead.

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

One authored stylesheet, `app/styles/podcast-factory.css`, in seven numbered
sections. Colour lives in its own `--l-*` namespace so an admin-site `--c-*`
token pasted in is inert rather than subtly wrong; the theme-independent system
(spacing, radii, elevation, the type ramp) is `--pf-*`.

**§3 is the only place a palette lives.** Three themes — light, sepia, dark —
switched by `data-theme` on `<html>`, with an inline script in `<head>` that
applies the stored choice before first paint. There is deliberately no
`prefers-color-scheme` block: the script resolves the system preference and
always stamps the attribute, so each palette is declared exactly once. Adding a
fourth is one block in §3 plus one name in `THEMES`.

`test/theme.test.ts` re-derives every contrast ratio on every run and holds each
palette to AA, including the four highlight colours — both that ink stays legible
ON a highlight, and that the highlight is visible AGAINST the page, which is what
a reader who cannot separate the hues actually sees.

Tailwind utilities come from `@theme inline` mapping onto those runtime
variables, under a `pf-` prefix. They are barely used — the components are
`.pf-*` classes — and the prefix is not cosmetic: Tailwind reserves t/r/b/l/s/e/
x/y for sides, so `--color-l-rule` silently compiles to `border-left-color`.

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

- **No Content Security Policy.** Blocked on the two inline `<head>` scripts,
  which need a nonce (`workers/app.ts`). They cannot simply be moved to files:
  they must run before first paint or the theme and the type size visibly snap
  into place on every load.
- **`wrangler r2 bucket info` reports 0 objects and 0 B even when the bucket is
  full.** Those figures come from Cloudflare's usage metrics, which lag by hours.
  To check whether an object is really there, fetch it back and compare:
  `npx wrangler r2 object get podcast-listener-media/<key> --remote --file=…`.
- **Notes and highlights are not built.** The design brief's "notes without a
  home" problem — a note anchored to a sentence a re-compose deleted — needs its
  own data model and is deliberately a separate phase.
- **Confirm the production redirect URI** is registered on the Google OAuth
  client: `https://podcast-factory.safinaverse.com/api/auth/callback/google`.
  Sign-in on the live site fails without it. See
  `_workspace/plan/listener-google-oauth.md`.
