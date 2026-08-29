import {
  type RouteConfig,
  index,
  layout,
  route,
} from "@react-router/dev/routes";

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
  // Public for the same reason, and it matters more: while the administrator is
  // simulating somebody, they are not an administrator, so `/admin` answers 404
  // — and simulating a revoked person redirects every gated page to /no-access.
  // A stop control behind either gate is one the simulation can lock you out of.
  // It takes no argument and grants nothing: it clears one cookie in the
  // caller's own browser.
  route("stop-simulating", "routes/stop-simulating.tsx"),
  route("favicon.ico", "routes/favicon.ico.ts"),

  // Everything else. Pathless, so it adds a gate without adding a URL segment.
  layout("routes/_authed.tsx", [
    // HOME is the chooser: two tiles, one per collection, each saying what it
    // is. INSIDE the gate like everything else, and for the same reason
    // `/about` is — it counts what this reader may see, so it is already an
    // answer about a private library.
    index("routes/welcome.tsx"),

    // The shelf. It was the index until 2026-08-29; Asif moved it so that the
    // masthead logo, the Home button and a bare visit to the site all arrive at
    // the chooser instead. Its own path rather than a redirect from `/`, so a
    // link to the grid is still a link to the grid.
    route("library", "routes/home.tsx"),

    // What the site does, for the people invited to it. INSIDE the gate like
    // everything else: it is offered from the masthead of every signed-in page,
    // and the invitation message links to it, which the gate handles by carrying
    // the destination in `?next=` and returning here after sign-in. It reads
    // nothing from the database, so it names no book and needs no access rule of
    // its own beyond this position.
    route("about", "routes/about.tsx"),

    // Advanced search. Its own page rather than more controls on the library,
    // because the library's box narrows a grid it is already holding and this
    // asks the catalogue a question — a different act, and one that wants room.
    // Gated like everything else: what it can find is what `visibleUnits`
    // returns for the person asking, never the catalogue.
    route("search", "routes/search.tsx"),

    // What is kept on this device, and the check that keeps it honest.
    //
    // `/downloads` is the ONE page the service worker keeps a copy of, so it is
    // what a listener with no signal reaches. It renders its list on the client
    // from IndexedDB rather than from its loader, which is what lets the stale
    // cached copy still be correct.
    route("downloads", "routes/downloads.tsx"),
    route("offline/allowed", "routes/offline.allowed.ts"),

    // Reading a downloaded chapter. A SEPARATE page from the reader, and one
    // route with the book in the query rather than in the path — both for
    // reasons that are load-bearing rather than stylistic; see the module.
    route("read-offline", "routes/read-offline.tsx"),

    route("book/:slug", "routes/book.$slug.tsx"),
    route("book/:slug/read/:chapter", "routes/book.$slug.read.$chapter.tsx"),
    route("book/:slug/slides", "routes/book.$slug.slides.tsx"),

    // A reader's own marks in one book — position, bookmarks, highlights, notes.
    // A resource route, and it hangs off `book/:slug` rather than living under an
    // `/api/` prefix so that `requireUnitAccess` reads the SAME `params.slug` the
    // page did. Reusing the gate is the point: an endpoint addressed any other
    // way would need an access rule of its own.
    route("book/:slug/marks", "routes/book.$slug.marks.ts"),

    // A whole book's prose, for keeping on the device. Hangs off `book/:slug`
    // for the same reason `marks` does: `requireUnitAccess` then reads the SAME
    // `params.slug` the reading page did.
    route("book/:slug/text", "routes/book.$slug.text.ts"),

    // Media sits INSIDE the gate like every page, and its `:slug` segment is
    // what `requireUnitAccess` reads — so a file URL runs the same check the
    // page ran. `run_worker_first` in wrangler.jsonc keeps /media/* away from
    // the static-asset server so this route is reached at all.
    route("media/:slug/*", "routes/media.$slug.$.tsx"),

    // `/admin` IS the people screen. It used to be an Overview tab holding five
    // numbers and two links, so the page an administrator actually works on was
    // never the one that opened; the numbers moved into the section's own header,
    // where both tabs show them. `/admin/content` remains the nested route the
    // case-variant probe in scripts/routes.mjs fires at.
    layout("routes/_authed._admin.tsx", [
      route("admin", "routes/admin._index.tsx"),
      route("admin/content", "routes/admin.content.tsx"),
      route("admin/usage", "routes/admin.usage.tsx"),
    ]),
  ]),
] satisfies RouteConfig;
