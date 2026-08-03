import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

/**
 * This file IS the access policy.
 *
 * Gating is POSITIONAL — a route's protection comes from where it sits in this
 * tree, never from a pathname comparison in code. That is not a style
 * preference: `compilePath` matches case-insensitively unless a route opts out
 * (react-router/lib/router/utils.js:510-530), so a gate written as
 * `pathname.startsWith("/admin")` is defeated by `GET /Admin/people`, and the
 * `.data` suffix is stripped only after middleware has already seen the URL.
 *
 * Two rules, both enforced by test/routes.test.ts:
 *
 *   1. Every route is a descendant of `_authed`, except the public ones named
 *      in PUBLIC_ROUTE_FILES there.
 *   2. Nothing under a gate exports its own ErrorBoundary, or a denied 404 and
 *      a genuine 404 would render differently and become distinguishable.
 *
 * `/api/auth/*` is deliberately absent: workers/app.ts answers it before React
 * Router runs, so sign-in needs no carve-out here.
 */
export default [
  // Public — the entire list.
  route("sign-in", "routes/sign-in.tsx"),
  route("no-access", "routes/no-access.tsx"),
  route("favicon.ico", "routes/favicon.ico.ts"),
  // Not part of the product: the three candidate marks side by side, in every
  // theme, so the choice is made from the real thing. Delete once settled.
  route("brand", "routes/brand.tsx"),

  // Everything else. Pathless, so it adds a gate without adding a URL segment.
  layout("routes/_authed.tsx", [
    index("routes/home.tsx"),
    route("book/:slug", "routes/book.$slug.tsx"),

    layout("routes/_authed._admin.tsx", [
      route("admin", "routes/admin._index.tsx"),
      route("admin/people", "routes/admin.people.tsx"),
      route("admin/content", "routes/admin.content.tsx"),
    ]),
  ]),
] satisfies RouteConfig;
