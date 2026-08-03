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
        // openid/email/profile only. Nothing here needs Drive, Calendar or
        // anything else, and a wider scope is a wider consent screen.
        scope: ["openid", "email", "profile"],
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
            return { data: session };
          },
        },
      },
    },
  });
}

export type Auth = ReturnType<typeof createAuth>;
export type Session = Awaited<ReturnType<Auth["api"]["getSession"]>>;

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

/** Normalized admin address, for seeding an invite row on first boot. */
export function adminEmail(env: Env): string {
  return normalizeEmail(env.ADMIN_EMAIL);
}
