import type { MiddlewareFunction } from "react-router";

import { notFound } from "./deny";
import { session } from "./session";

/**
 * Layer 3 — admin.
 *
 * Nested inside the invited gate, so by the time this runs the viewer is
 * already signed in and invited. `isAdmin` was computed in layer 1 by comparing
 * normalizeEmail(session email) against normalizeEmail(ADMIN_EMAIL); there is
 * no role column anywhere, so no row write grants admin, and the comparison
 * fails closed when ADMIN_EMAIL is missing or unusable.
 *
 * 404 rather than 403 for a signed-in non-admin — a 403 confirms the surface
 * exists. Both `/admin/*` and `/api/admin/*` nest under the layout carrying
 * this middleware; resource routes inherit parent middleware
 * (router.js:2283 flat-maps the whole matched chain), so the API routes are
 * covered by the same single declaration.
 */
export const requireAdmin: MiddlewareFunction<Response> = async ({ context }, next) => {
  const viewer = context.get(session).viewer;
  if (viewer === null || !viewer.isAdmin) notFound();
  return next();
};
