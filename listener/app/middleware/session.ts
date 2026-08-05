import { createContext, type MiddlewareFunction } from "react-router";

import { cloudflare } from "~/context";
import { createAuth, isAdminEmail } from "~/server/auth.server";
import { simulatedEmail } from "~/server/simulate.server";
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
  /**
   * Set only while the administrator is looking at the site as someone else.
   *
   * `viewer` is then the SIMULATED person and carries no trace of who is really
   * driving — deliberately, so that every gate and every query answers the
   * question "what can this person see" and nothing has to remember to ask a
   * second one. This field exists for the two things that DO need to know: the
   * banner that says so, and the write path that refuses.
   */
  simulating: { as: string; by: string } | null;
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

  /* ---- Seeing the site as somebody else --------------------------------
     THE ONE PLACE the viewer is swapped, so there is a single truth for every
     gate, every loader and every query downstream — none of which knows or
     needs to know that this happened.

     The condition is the whole security model: the cookie is read ONLY when the
     real session is the administrator's, so forged in anybody else's browser it
     is never consulted. And what it produces is always a DOWNGRADE —
     `isAdmin: false` unconditionally, including when the address simulated is
     the admin's own — so no value of it can add a capability to anyone. See
     server/simulate.server.ts.                                              */
  let simulating: SessionState["simulating"] = null;

  if (viewer !== null && viewer.isAdmin) {
    const as = simulatedEmail(request);
    if (as !== null) {
      simulating = { as, by: viewer.email };
      viewer = {
        email: as,
        rawEmail: as,
        // No display name to borrow: the person being simulated may never have
        // signed in, which is exactly the case worth checking.
        name: as,
        image: null,
        isAdmin: false,
      };
    }
  }

  context.set(session, { viewer, simulating });
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

/** The same tolerance, for the banner and the write guard. */
export function simulatingOf(
  context: Readonly<{ get: (c: typeof session) => SessionState }>,
): SessionState["simulating"] {
  try {
    return context.get(session).simulating;
  } catch {
    return null;
  }
}
