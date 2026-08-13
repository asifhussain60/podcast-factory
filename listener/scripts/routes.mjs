/**
 * Every page this site serves, and who is supposed to see it.
 *
 * ONE manifest, shared by the runtime gate (`smoke.mjs`) and the screenshot
 * harness (`shots.mjs`), because two lists would drift and the one that drifted
 * would be the one that stopped visiting the page that broke.
 *
 * `who` names the identity a route is visited AS:
 *
 *   anon    signed out
 *   admin   the configured ADMIN_EMAIL
 *   reader  invited, granted exactly one book
 *   nobody  invited, granted nothing — the default-deny case
 *
 * `expect` is the status that identity must get. A route listed for `nobody`
 * with `expect: 404` is an ACCESS ASSERTION, not merely a page visit: the whole
 * security model is that a book you were not given is indistinguishable from a
 * book that does not exist, and this is where that is fired rather than reasoned
 * about.
 *
 * `:slug` and `:chapter` are filled in at run time from whatever the local
 * database actually holds, so the manifest never names a book that has to exist.
 */

/** Routes with no parameters. */
export const STATIC_ROUTES = [
  { path: "/sign-in", who: "anon", expect: 200, label: "sign-in" },
  { path: "/no-access", who: "anon", expect: 200, label: "no-access" },
  { path: "/", who: "admin", expect: 200, label: "library" },
  { path: "/", who: "reader", expect: 200, label: "library-one-book" },
  { path: "/", who: "nobody", expect: 200, label: "library-empty" },

  // What the site does. Behind the gate like every other page, and visited as
  // all three signed-in identities because it must not depend on holding a book:
  // somebody invited and given nothing yet is precisely the reader who needs it,
  // and the invitation message links here.
  { path: "/about", who: "admin", expect: 200, label: "about" },
  { path: "/about", who: "reader", expect: 200, label: "about-reader" },
  { path: "/about", who: "nobody", expect: 200, label: "about-no-books" },
  { path: "/about", who: "anon", expect: 302, label: "about-signed-out" },

  // Advanced search. Reached from a button on the library, so it is visited as
  // the identities that see that button — including the reader granted one book,
  // since the page must not depend on holding more than that.
  { path: "/search", who: "admin", expect: 200, label: "search" },
  { path: "/search", who: "reader", expect: 200, label: "search-reader" },
  { path: "/search", who: "anon", expect: 302, label: "search-signed-out" },

  // The page ASKING something, not merely loading. An empty search box exercises
  // none of the index, the join to `visible`, or the facet counts — so a query
  // that returns real rows for the administrator is fired here, and the same
  // query is fired as the two identities who must see less of it. `nobody` is
  // the one that matters most: invited, granted nothing, and therefore entitled
  // to a page that loads and finds NOTHING. A 200 with results there would be
  // the whole access model failing quietly, which is why it is asserted by a
  // script rather than reasoned about.
  { path: "/search?q=intellect", who: "admin", expect: 200, label: "search-query" },
  { path: "/search?q=intellect", who: "reader", expect: 200, label: "search-query-reader" },
  { path: "/search?q=intellect", who: "nobody", expect: 200, label: "search-query-no-books" },
  // A reference query, which takes the other branch of the loader entirely.
  { path: "/search?q=2%3A255", who: "admin", expect: 200, label: "search-reference" },
  // Arabic, folded — the case a Latin-only harness would never catch.
  {
    path: "/search?q=%D9%88%D9%84%D9%8A",
    who: "admin",
    expect: 200,
    label: "search-arabic",
  },

  // What is kept on this device. Visited as somebody holding nothing too — the
  // page has to be reachable and empty rather than absent, or a listener whose
  // last book was withdrawn meets a 404 where their downloads used to be.
  { path: "/downloads", who: "admin", expect: 200, label: "downloads" },
  { path: "/downloads", who: "reader", expect: 200, label: "downloads-reader" },
  { path: "/downloads", who: "nobody", expect: 200, label: "downloads-empty" },
  { path: "/downloads", who: "anon", expect: 302, label: "downloads-signed-out" },

  // The lease. Signed out it must REDIRECT rather than answer: the client reads
  // a redirect as "could not find out" and deletes nothing, which is what stops
  // a signed-out moment from wiping a library.
  { path: "/offline/allowed", who: "reader", expect: 200, label: "offline-allowed" },
  { path: "/offline/allowed", who: "anon", expect: 302, label: "offline-allowed-signed-out" },

  // The offline reading shell. Its document carries nothing about anybody — the
  // chapters are read from the device after it loads — which is what makes it
  // safe for the service worker to keep. Visited with no book named, which is
  // the state the worker's own fallback can land somebody in.
  { path: "/read-offline", who: "admin", expect: 200, label: "read-offline" },
  { path: "/read-offline", who: "reader", expect: 200, label: "read-offline-reader" },
  { path: "/read-offline", who: "anon", expect: 302, label: "read-offline-signed-out" },

  // `/admin` IS the people screen — the Overview tab it used to open on was
  // retired, and its numbers now sit above both tabs.
  { path: "/admin", who: "admin", expect: 200, label: "admin-people" },
  { path: "/admin/content", who: "admin", expect: 200, label: "admin-content" },

  // Signed out, everything behind the gate redirects rather than 404s — the
  // caller is not being told the page does not exist, they are being told to
  // sign in. The distinction only holds for people who are not signed in.
  { path: "/", who: "anon", expect: 302, label: "library-signed-out" },
  { path: "/admin", who: "anon", expect: 302, label: "admin-signed-out" },

  // Admin is a 404 for everyone else, never a 403: a 403 confirms the page is
  // there. `/Admin/content` is the case-variant probe — `compilePath` matches
  // case-insensitively, so a gate written as a pathname comparison would let it
  // through, and this is the request that proves the gate is positional. It must
  // name a route that EXISTS and is nested, or a 404 would prove only that
  // React Router matched nothing: it was `/Admin/people` until the people screen
  // moved up to `/admin` and that path stopped existing.
  { path: "/admin", who: "reader", expect: 404, label: "admin-denied" },
  { path: "/Admin/content", who: "reader", expect: 404, label: "admin-denied-case" },
];

/** Routes needing a book the signed-in identity can actually open. */
export const BOOK_ROUTES = [
  { path: "/book/:slug", who: "reader", expect: 200, label: "book" },
  { path: "/book/:slug/read/:chapter", who: "reader", expect: 200, label: "reader" },
  { path: "/book/:slug/marks", who: "reader", expect: 200, label: "marks" },

  // A whole book's prose, for keeping on the device. Same gate as the page, so
  // the denied case must be a 404 exactly like the page's.
  { path: "/book/:slug/text", who: "reader", expect: 200, label: "book-text" },

  // The same chapter, to the one account whose right-hand drawer is the Scholar
  // Companion rather than its own notes. Shot separately because it is a
  // DIFFERENT PAGE — a different panel, and tinted sentences in the prose — and
  // the reader shot above, taken as an ordinary reader, can never show it.
  {
    path: "/book/:slug/read/:chapter",
    who: "admin",
    expect: 200,
    label: "reader-companion",
  },

  // The same book, to someone who was never given it.
  { path: "/book/:slug", who: "nobody", expect: 404, label: "book-denied" },
  { path: "/book/:slug/read/:chapter", who: "nobody", expect: 404, label: "reader-denied" },
  { path: "/book/:slug/marks", who: "nobody", expect: 404, label: "marks-denied" },
  { path: "/book/:slug/text", who: "nobody", expect: 404, label: "book-text-denied" },
];

/** Routes only worth visiting when the book has the thing they show. */
export const OPTIONAL_ROUTES = [
  { path: "/book/:slug/slides", who: "reader", expect: 200, label: "slides", needs: "deck" },
];

/** The widths every surface is checked and shot at. */
export const WIDTHS = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "tablet-wide", width: 1024, height: 768 },
  { name: "desktop", width: 1440, height: 900 },
];

export const THEMES = ["light", "sepia", "dark"];
