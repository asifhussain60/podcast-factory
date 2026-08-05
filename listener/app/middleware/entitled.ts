import type { MiddlewareFunction } from "react-router";

import { cloudflare } from "~/context";
import { canRead } from "~/server/access.server";
import { notFound } from "./deny";
import { session } from "./session";

/**
 * Layer 4 — you may read THIS unit.
 *
 * Sits on the book route itself and reads `params.slug`, rather than on a shared
 * parent that would have to re-derive the slug from the URL. Pathname parsing is
 * where these gates go wrong: `compilePath` matches case-insensitively unless a
 * route opts out (utils.js:510-530), and the `.data` suffix is stripped only
 * after middleware sees `request.url`.
 *
 * Denial is a 404 through `notFound()`, so a book that exists but is not granted
 * is indistinguishable from a slug that was never real.
 */
export const requireUnitAccess: MiddlewareFunction<Response> = async (
  { params, context },
  next,
) => {
  const slug = params.slug;
  if (!slug) notFound();

  const viewer = context.get(session).viewer;
  if (viewer === null) notFound();

  const { env } = context.get(cloudflare);
  if (!(await canRead(env.DB, viewer.email, slug))) notFound();

  return next();
};
