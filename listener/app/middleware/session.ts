import { createContext, type MiddlewareFunction } from "react-router";

import { cloudflare } from "~/context";
import { createAuth, isAdminEmail } from "~/server/auth.server";
import { tryNormalizeEmail } from "~/server/email.server";

export interface Viewer {
  /** Normalized. The only email any downstream code may act on. */
  email: string;
  rawEmail: string;
  name: string;
  image: string | null;
  isAdmin: boolean;
}

export interface SessionState {
  viewer: Viewer | null;
}

export const session = createContext<SessionState>();

/**
 * Layer 1 — resolve the session into context. Gates nothing.
 *
 * Lives on root so the sign-in page can render a header that knows whether
 * anyone is signed in. The real gates are layers 2 and 3.
 *
 * It ALWAYS sets a value, even `{ viewer: null }`, and every reader must
 * tolerate that. React Router runs no middleware when nothing matched — query()
 * short-circuits the 404 ahead of runServerMiddlewarePipeline
 * (router.js:1472-1486) — so on `GET /nonexistent` this never fires at all.
 * Code that assumed a populated context would throw there, turning a 404 into a
 * 500 and making the two trivially distinguishable.
 *
 * `emailVerified` is required. Better Auth maps it from Google's own
 * `email_verified` claim (@better-auth/core/src/social-providers/google.ts:234),
 * so for a real Google account it is always true — and requiring it means an
 * unverified row, however it came to exist, is nobody.
 */
export const withSession: MiddlewareFunction<Response> = async ({ request, context }, next) => {
  const { env } = context.get(cloudflare);

  let viewer: Viewer | null = null;

  try {
    const auth = createAuth(env);
    const result = await auth.api.getSession({ headers: request.headers });

    if (result?.user?.email && result.user.emailVerified) {
      const email = tryNormalizeEmail(result.user.email);
      if (email !== null) {
        viewer = {
          email,
          rawEmail: result.user.email,
          name: result.user.name || email,
          image: result.user.image ?? null,
          isAdmin: isAdminEmail(env, result.user.email),
        };
      }
    }
  } catch {
    // A session that cannot be resolved is a session that does not exist.
    // Never a reason to fail open.
    viewer = null;
  }

  context.set(session, { viewer });
  return next();
};

/**
 * Read the session, tolerating the case where the middleware never ran.
 *
 * `context.get` throws on an unset context, and there is exactly one situation
 * where it is unset: the hard-404 render path described above. Every consumer
 * goes through here so that path renders instead of exploding.
 */
export function viewerOf(context: Readonly<{ get: (c: typeof session) => SessionState }>): Viewer | null {
  try {
    return context.get(session).viewer;
  } catch {
    return null;
  }
}
