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
  // Public because /no-access is: someone signed in with the wrong Google
  // account is outside the invited gate, and that is exactly the person who
  // needs to sign out. It ends the caller's own session and nobody else's.
  route("sign-out", "routes/sign-out.tsx"),
  route("no-access", "routes/no-access.tsx"),
  route("favicon.ico", "routes/favicon.ico.ts"),

  // Everything else. Pathless, so it adds a gate without adding a URL segment.
  layout("routes/_authed.tsx", [
    index("routes/home.tsx"),
    route("book/:slug", "routes/book.$slug.tsx"),
    route("book/:slug/read/:chapter", "routes/book.$slug.read.$chapter.tsx"),
    route("book/:slug/slides", "routes/book.$slug.slides.tsx"),

    // A reader's own marks in one book — position, bookmarks, highlights, notes.
    // A resource route, and it hangs off `book/:slug` rather than living under an
    // `/api/` prefix so that `requireUnitAccess` reads the SAME `params.slug` the
    // page did. Reusing the gate is the point: an endpoint addressed any other
    // way would need an access rule of its own.
    route("book/:slug/marks", "routes/book.$slug.marks.ts"),

    // Media sits INSIDE the gate like every page, and its `:slug` segment is
    // what `requireUnitAccess` reads — so a file URL runs the same check the
    // page ran. `run_worker_first` in wrangler.jsonc keeps /media/* away from
    // the static-asset server so this route is reached at all.
    route("media/:slug/*", "routes/media.$slug.$.tsx"),

    layout("routes/_authed._admin.tsx", [
      route("admin", "routes/admin._index.tsx"),
      route("admin/people", "routes/admin.people.tsx"),
      route("admin/content", "routes/admin.content.tsx"),
    ]),
  ]),
] satisfies RouteConfig;
