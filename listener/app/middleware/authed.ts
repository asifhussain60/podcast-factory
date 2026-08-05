import { redirect, type MiddlewareFunction } from "react-router";

import { cloudflare } from "~/context";
import { safeNext } from "~/lib/nav";
import { hasLiveInvite } from "~/server/access.server";
import { session } from "./session";

/**
 * Layer 2 — you are signed in, invited, and not revoked.
 *
 * A MIDDLEWARE and not a loader, deliberately. A parent-loader gate is defeated
 * by a single query parameter: `_routes` feeds `filterMatchesToLoad`
 * (single-fetch.js:79-84), so `GET /book/x.data?_routes=routes/book.$slug` runs
 * the child loader and never calls the parent's. Middleware wraps the whole
 * queryImpl call (router.js:1493-1505), where that filter cannot reach it.
 *
 * The invite is re-checked on EVERY request, not just at sign-in. Sessions live
 * 30 days; if revocation only took effect at sign-in, a revoked person would
 * keep their access for up to a month. This, plus deleting their session rows
 * on revoke, plus cookieCache staying disabled, is what makes "revoke" mean
 * "immediately".
 */
export const requireInvited: MiddlewareFunction<Response> = async (
  { request, context },
  next,
) => {
  const viewer = context.get(session).viewer;

  // Signed out is NOT a 404. Asif emails someone a link to a book; if that
  // returned "not found" they would never see a sign-in prompt and would assume
  // the link was broken. Only a signed-in-but-not-entitled request 404s.
  if (viewer === null) {
    const url = new URL(request.url);
    // Strip the single-fetch suffix so the post-sign-in bounce lands on the page
    // rather than on its data endpoint.
    const target = url.pathname.replace(/\.data$/, "") + url.search;
    throw redirect(`/sign-in?next=${encodeURIComponent(safeNext(target))}`);
  }

  // The SAME predicate Better Auth's sign-in hooks use — one definition, in
  // access.server.ts. If these two could disagree, a revoked person would keep
  // whichever answer favoured them.
  const { env } = context.get(cloudflare);
  if (!(await hasLiveInvite(env.DB, viewer.email))) {
    throw redirect("/no-access");
  }

  return next();
};
