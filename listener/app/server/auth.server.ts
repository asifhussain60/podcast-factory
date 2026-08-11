import { betterAuth } from "better-auth";

import { hasLiveInvite } from "./access.server";
import { normalizeEmail, tryNormalizeEmail } from "./email.server";

/**
 * Better Auth, constructed once PER REQUEST.
 *
 * It cannot be a module-level singleton: `env.DB` is a request-scoped binding
 * on Workers, so a config captured at module load would close over a binding
 * from whichever request happened to warm the isolate.
 *
 * `database: env.DB` is passed directly — the Kysely adapter duck-types a D1
 * handle (`batch` + `exec` + `prepare`) and picks its bundled D1SqliteDialect,
 * so there is no third-party dialect in the dependency tree.
 */
export function createAuth(env: Env) {
  return betterAuth({
    database: env.DB,
    baseURL: env.BETTER_AUTH_URL,
    secret: env.BETTER_AUTH_SECRET,
    basePath: "/api/auth",

    socialProviders: {
      google: {
        clientId: env.GOOGLE_CLIENT_ID,
        clientSecret: env.GOOGLE_CLIENT_SECRET,
        // No `scope` here on purpose. Better Auth's Google provider already
        // requests openid/email/profile, and naming them again APPENDS rather
        // than replaces — the authorization URL went out carrying
        // "email profile openid openid email profile". Harmless to Google, but
        // it made the request look like it had been configured twice by two
        // people who disagreed.
        //
        // The rule this leaves implicit: nothing here needs Drive, Calendar or
        // anything else, and a wider scope is a wider consent screen. If a scope
        // ever IS added, it also has to be declared on the project's Data access
        // page — and since that page is shared by every Safina app, a sensitive
        // scope added here would drag all of them into verification.
      },
    },

    emailAndPassword: { enabled: false },

    user: {
      // `user.email` IS the privilege bit — admin is an email comparison and
      // grants key on email. A self-service email change would therefore be a
      // self-service privilege change. Off, asserted by a test, and backed by a
      // D1 trigger in 0002_access.sql so it is structurally refused rather than
      // merely unconfigured.
      changeEmail: { enabled: false },
      deleteUser: { enabled: false },
    },

    session: {
      expiresIn: 60 * 60 * 24 * 30, // 30 days
      updateAge: 60 * 60 * 24, // rolling refresh, 1 day

      // MUST stay disabled. With the cookie cache on, getSession answers from a
      // signed cookie without touching the database — so revoking an invite
      // would keep working for the whole cache window even though the gate
      // re-checks on every request. Asserted by a test.
      cookieCache: { enabled: false },
    },

    advanced: {
      // The site is one origin; there is no cross-site embedding to support.
      defaultCookieAttributes: { sameSite: "lax", httpOnly: true },
    },

    databaseHooks: {
      user: {
        create: {
          // Refuse to create a user row at all for an address with no live
          // invite. This is an optimisation, not the gate: an uninvited person
          // must never be able to make us write rows, but the AUTHORITY is the
          // per-request check in app/middleware/authed.ts. Whether this hook can
          // abort creation across every Better Auth version is not something the
          // design leans on.
          before: async (user) => {
            if (!(await hasLiveInvite(env.DB, user.email))) return false;
            return { data: user };
          },
        },
      },
      session: {
        create: {
          // Fires on EVERY sign-in, unlike user.create.before which fires only
          // the first time. An invited-then-revoked person re-signing in is
          // exactly the case the user hook cannot see.
          before: async (session) => {
            const email = await emailForUserId(env, session.userId);
            if (email === null || !(await hasLiveInvite(env.DB, email))) return false;

            // Record the arrival. This is the ONLY writer of `redeemed_at`,
            // which existed unwritten from 0002 until 0006 — so the admin screen
            // showed everyone as never-having-signed-in, including people who
            // read daily.
            //
            // Deliberately after the gate and deliberately swallowing its own
            // failure: this is bookkeeping, and a sign-in that works must not
            // start failing because a column could not be updated.
            await markArrival(env, email).catch(() => {});

            return { data: session };
          },
        },
      },
    },
  });
}

export type Auth = ReturnType<typeof createAuth>;
export type Session = Awaited<ReturnType<Auth["api"]["getSession"]>>;

/**
 * Stamp first-ever and most-recent sign-in on the invite.
 *
 * `redeemed_at` is set only once — `COALESCE` keeps whatever is already there —
 * because "when did they first turn up" must not drift forward every time they
 * come back. `last_seen_at` is overwritten every time, which is its whole job.
 *
 * The address is normalized because `invite.email` is the normalized form; a raw
 * Google address with a dot in it would match no row and stamp nothing, silently
 * restoring the defect this fixes.
 */
async function markArrival(env: Env, rawEmail: string): Promise<void> {
  const now = new Date().toISOString();
  await env.DB.prepare(
    `UPDATE invite SET redeemed_at = COALESCE(redeemed_at, ?2), last_seen_at = ?2
      WHERE email = ?1`,
  )
    .bind(normalizeEmail(rawEmail), now)
    .run();
}

async function emailForUserId(env: Env, userId: string): Promise<string | null> {
  const row = await env.DB.prepare(`SELECT email FROM user WHERE id = ? LIMIT 1`)
    .bind(userId)
    .first<{ email: string }>();

  return row?.email ?? null;
}

/**
 * The single definition of admin.
 *
 * There is no `role` column, so no row write can escalate. The comparison runs
 * through normalizeEmail on BOTH sides — an admin check using a raw `===` while
 * the grant lookup normalizes is the divergence that quietly breaks everything.
 *
 * Fails closed when ADMIN_EMAIL is missing or unusable, which is what makes a
 * misconfigured environment lock everyone out rather than let everyone in.
 */
export function isAdminEmail(env: Env, sessionEmail: string | null | undefined): boolean {
  if (!sessionEmail) return false;

  const configured = tryNormalizeEmail(env.ADMIN_EMAIL ?? "");
  if (configured === null) return false;

  const actual = tryNormalizeEmail(sessionEmail);
  if (actual === null) return false;

  return actual === configured;
}

// `adminEmail(env)` lived here until 2026-08-11, documented as "for seeding an
// invite row on first boot". Nothing called it: the admin's invite is seeded by
// migrations/0001, and `test/config.test.ts` pins that the wrangler var, the
// seeded row and the 0002 triggers all name the SAME normalized address. It was
// the last survivor of a TypeScript seeding path the migration replaced, and the
// live check above (`isAdmin`, which fails closed) is the only resolver.
//
// Removed rather than left: it normalized with `normalizeEmail` where `isAdmin`
// uses `tryNormalizeEmail`, so a second, throwing answer to "who is the admin"
// sat one import away from anyone looking for one.
