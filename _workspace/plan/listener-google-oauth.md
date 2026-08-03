# The one thing only Asif can do: the Google sign-in client

Everything in phase 2 is built and proven except real sign-in, which needs a
Google OAuth client. Nothing else is blocked on this — the gates are all
verified with development sessions.

## In the Google Cloud Console

1. **console.cloud.google.com** — create a project, or reuse one. Name it
   something you will recognise later, e.g. "Podcast Factory".

2. **APIs & Services -> OAuth consent screen.**
   - User type: **External**. (Internal needs Google Workspace.)
   - App name: **Podcast Factory**. Support email: your own.
   - Scopes: add **only** `openid`, `.../auth/userinfo.email` and
     `.../auth/userinfo.profile`. Nothing else. Anything more widens the consent
     screen people see and gains us nothing.
   - Publishing status: while it is in **Testing**, only accounts listed under
     "Test users" can sign in — which is fine, even useful, since the site is
     invite-only anyway. Add your own address and anyone you plan to invite.
     Moving to Production later needs no code change.

3. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID.**
   - Application type: **Web application**.
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

## The two Cloudflare problems, which are separate from the above

Neither blocks anything until you actually want the site online.

1. **Wrangler is logged in to the wrong account.** It currently holds
   `asifhussain60@hotmail.com`, which your own deploy playbook forbids. The
   `safinaverse.com` zone lives on the gmail account. Deploying would otherwise
   publish the Worker to the wrong account, where the domain could never attach.
   `wrangler.jsonc` names the real custom domain precisely so a wrong-account
   deploy fails loudly instead of half-working.

2. **`cf-deploy.sh` cannot deploy this app.** That script is Cloudflare Pages
   from end to end; the Listener is a Worker with static assets, which is a
   different product and a different API. It needs `wrangler deploy`. Also worth
   knowing: the gmail token in your keychain cannot read zone DNS records, and
   whether it can attach a *Workers* custom domain is untested — it may need a
   scope only you can add.

Also still open, unrelated: the logo mark is not chosen. All three are built;
`/brand` shows them side by side in every theme, and `DEFAULT_MARK` in
`app/components/brand/Logo.tsx` is the single line that changes.
