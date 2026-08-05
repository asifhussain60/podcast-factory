# Google sign-in for Safina — set up once, reused by every app

Everything in phase 2 is built and proven except real sign-in, which needs a
Google OAuth client. Nothing else is blocked on this — the gates are all
verified with development sessions.

## Name it for the platform, not for this app

One Google Cloud project holds **many** OAuth clients. Each client has its own
ID, secret and redirect URIs, so apps stay isolated. What they share is the
CONSENT SCREEN — the branding, the scope list, the publishing status and the
test-user list all belong to the project, not the client.

So the project should be **Safina**, not "Podcast Factory". The placeholder page
already says "Part of the Safina platform", the apps live on `*.safinaverse.com`,
and `asif-academy` is already on that Cloudflare account. Every future Safina app
then needs a new client and nothing else — no second consent screen, no second
review.

| Layer | Value | Who sees it |
|---|---|---|
| Cloud project | `Safina` | Only Asif, in the console |
| Consent screen name | **Safina** | Everyone signing in, to any app |
| OAuth client | `Podcast Factory Listener` | Only Asif — client names are internal |
| Redirect URIs | Only this app's two | — |

Someone signing in reads "continue to Safina" rather than the site name they
clicked from. For an invite-only library where each person was invited
personally that is a non-issue, and it teaches them the platform name.

**When to split later.** Scope changes are project-wide. The three scopes below
are Google's non-sensitive tier and need no verification review. If some future
Safina app needs Drive or Gmail scopes, that app would drag the WHOLE project's
consent screen through verification — at which point move that one app to its
own project. Not a reason to split now.

## In the Google Cloud Console

1. **console.cloud.google.com** — create a project named **Safina** (or reuse it
   if it already exists).

2. **APIs & Services -> OAuth consent screen.**
   - User type: **External**. (Internal needs Google Workspace.)
   - App name: **Safina**. Support email: your own.
   - Scopes: add **only** `openid`, `.../auth/userinfo.email` and
     `.../auth/userinfo.profile`. Nothing else. Anything more widens the consent
     screen people see, gains us nothing, and — per above — would affect every
     app sharing this project.
   - Publishing status: while it is in **Testing**, only accounts listed under
     "Test users" can sign in. That is fine, even useful, since the site is
     invite-only anyway. Add your own address and anyone you plan to invite.
     Moving to Production later needs no code change.
   - Note the test-user list is shared by every app in the project. That does not
     weaken anything: Google's list was never the security boundary — the
     `invite` table is. Someone on the test list who has no invitation still
     lands on "no access".

3. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID.**
   - Application type: **Web application**.
   - Name: **Podcast Factory Listener** — internal only, never shown to users.
     One client per app; this is the piece you repeat for the next one.
   - **Authorized JavaScript origins** — add both:
     - `http://localhost:5273`
     - `https://podcast-factory.safinaverse.com`
   - **Authorized redirect URIs** — add both, exactly, including the path:
     - `http://localhost:5273/api/auth/callback/google`
     - `https://podcast-factory.safinaverse.com/api/auth/callback/google`

4. Copy the **Client ID** and **Client secret**.

## Where they go

Locally, in `listener/.dev.vars` (already created, gitignored — replace the two
placeholder lines):

    GOOGLE_CLIENT_ID=<client id>.apps.googleusercontent.com
    GOOGLE_CLIENT_SECRET=<client secret>

Then `cd listener && npm run dev` and sign in at http://localhost:5273.
Your address is already invited and already holds a whole-library grant, so you
should land on the library with both published books.

For production, when the account question below is settled: the client ID goes
into `wrangler.jsonc` under `vars` (it is not a secret), and the secret goes in
with `wrangler secret put GOOGLE_CLIENT_SECRET`. `BETTER_AUTH_SECRET` needs the
same treatment — generate a fresh one for production with
`openssl rand -base64 32`, never reuse the local one.

## The two Cloudflare problems — both resolved 2026-08-03

The site is live at <https://podcast-factory.safinaverse.com>. Both are recorded
in full in `infra/cloudflare/README.md`; in short:

1. **Wrangler is still logged in to `asifhussain60@hotmail.com`**, and that was
   left alone rather than changed globally. Exporting `CLOUDFLARE_API_TOKEN`
   makes wrangler use the gmail account for that command only — verified, it
   prints "The API Token is read from the CLOUDFLARE_API_TOKEN environment
   variable". Nothing on the machine had to be re-authenticated.

2. **`cf-deploy.sh` still cannot deploy this app** — it is Pages, this is a
   Worker. `npm run deploy` does it. The token turned out to be able to attach a
   Workers custom domain after all, but only through the ACCOUNT-level
   `workers/domains` endpoint; wrangler reaches for the zone-level
   `workers/routes` and is denied, so the deploy exits non-zero after a
   successful upload. The domain is attached and later deploys keep it.

**What is NOT resolved: R2 is not enabled on the account.** Creating the media
bucket is refused with "Please enable R2 through the Cloudflare Dashboard"
(code 10042) — a one-time opt-in only Asif can click. Until then the site has no
audio, no PDFs and no deck images; it knows they exist and says they are not
uploaded yet.

**And confirm the production redirect URI is registered on the OAuth client** —
`https://podcast-factory.safinaverse.com/api/auth/callback/google`. Sign-in on
the live site cannot complete without it.

## Adding the next Safina app later

Create a second OAuth client in the SAME project, with that app's own origins and
redirect URIs. Nothing else changes — no new consent screen, no new review, and
this app's client is untouched. Only if that app needs a sensitive scope (Drive,
Gmail) does it want a project of its own.

Also still open, unrelated: the logo mark is not chosen. All three are built;
`/brand` shows them side by side in every theme, and `DEFAULT_MARK` in
`app/components/brand/Logo.tsx` is the single line that changes.
