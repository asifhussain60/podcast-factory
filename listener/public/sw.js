/*
 * The service worker exists for ONE job: so the site opens with no network.
 *
 * It deliberately does NOT touch audio. Downloaded episodes live in IndexedDB
 * and play from a blob URL (see app/lib/offline.ts) — nothing about playback
 * passes through here, which is what keeps byte-range serving in the one place
 * it is implemented, on the server.
 *
 * WHAT IT WILL NOT CACHE, and why each one is a rule rather than an oversight:
 *
 *   /media/*      entitled bytes. Audio has its own store; everything else there
 *                 — print editions, deck pages — is re-fetched, so a withdrawn
 *                 book leaves nothing behind in a cache this file controls.
 *   /api/*        the auth surface. A cached sign-in response is a cached
 *                 identity.
 *   /book/*       a chapter's HTML can carry Scholar Companion cards, which one
 *                 account may see. Caching a document here would put them in a
 *                 store no `viewer.isAdmin` check guards.
 *   anything      a redirect to /sign-in is what a signed-out request looks
 *   redirected    like; caching one serves it back to a session that is fine.
 *
 * So exactly two KINDS of thing are kept: hashed build assets, which are
 * immutable and carry no one's data, and the two shell documents — /downloads
 * and /read-offline. Both shells are safe to keep for the same reason, and it is
 * the reason they exist as separate pages at all: their documents say nothing
 * about anybody. Everything on either one is read from IndexedDB after it loads,
 * so a stored copy discloses nothing that a signed-out visitor could not already
 * see, and there is no Companion card anywhere in them.
 */

const VERSION = "v1";
const ASSETS = `pf-assets-${VERSION}`;
const DOCS = `pf-docs-${VERSION}`;

/** The one page that has to work with no network. */
const OFFLINE_PATH = "/downloads";

/**
 * The offline READING shell.
 *
 * A page whose document says nothing about anybody — everything on it is read
 * from IndexedDB after it loads — which is what makes it safe to keep when a
 * /book document is not. The book and chapter travel in the QUERY, and this
 * cache is keyed by path, so one stored copy serves every chapter of every
 * downloaded book. Keyed by path is not an implementation detail here: a
 * per-chapter key would mean only the chapters already opened online could be
 * opened offline, which is exactly backwards.
 */
const READ_PATH = "/read-offline";

/** /book/<slug>/read/<chapter> — the page we cannot cache, and can redirect. */
const READER_URL = /^\/book\/([^/]+)\/read\/([^/]+)\/?$/;

/** Immutable, hashed, and nobody's private data. */
const CACHEABLE_ASSET = /^\/(assets|fonts|brand)\//;

self.addEventListener("install", (event) => {
  // Take over as soon as the new worker is ready rather than waiting for every
  // tab to close. There is no persisted format here to migrate, and the caches
  // are versioned, so an old page meeting a new worker loses nothing.
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([ASSETS, DOCS]);
      const names = await caches.keys();
      await Promise.all(names.map((name) => (keep.has(name) ? null : caches.delete(name))));
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  // Sign-out. The page tells us rather than us watching for the POST, because
  // the sign-out form is a navigation and the response we would see is the
  // redirect, not the outcome.
  if (event.data === "pf-signed-out") {
    event.waitUntil(caches.delete(DOCS));
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (CACHEABLE_ASSET.test(url.pathname)) {
    event.respondWith(asset(request));
    return;
  }

  if (isShellRequest(url)) {
    event.respondWith(shellDocument(request));
    return;
  }

  // Any OTHER navigation, offline: send them to a page that works instead of
  // the browser's error. A redirect rather than serving a cached document under
  // the wrong URL — a document carries its own route data, and handing the
  // Downloads page back for /book/x would hydrate a page that disagrees with
  // the address.
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => fallback(url)));
  }
});

/** The two shells that must survive with no network, and their route data. */
function isShellRequest(url) {
  const path = url.pathname.replace(/\.data$/, "");
  return path === OFFLINE_PATH || path === READ_PATH;
}

/**
 * Hashed and immutable, so the cached copy is always right and the network is
 * only for the first miss. A hashed name changing IS the invalidation.
 */
async function asset(request) {
  const cached = await caches.match(request, { cacheName: ASSETS });
  if (cached !== undefined) return cached;

  const response = await fetch(request);
  if (response.ok && !response.redirected) {
    const cache = await caches.open(ASSETS);
    await cache.put(request, response.clone());
  }
  return response;
}

/**
 * Network first, and keep the answer.
 *
 * Network first rather than cache first because this page is the record of what
 * is on the device, and a stale shell is worth having only when there is no
 * fresh one. `response.redirected` is the signed-out case and must never be the
 * copy we keep.
 */
async function shellDocument(request) {
  try {
    const response = await fetch(request);
    if (response.ok && !response.redirected) {
      const cache = await caches.open(DOCS);
      // Keyed by PATH, not by the request: a `.data` request carries query
      // parameters that vary per navigation, and keying on them would fill the
      // cache with copies none of which the offline fallback could find.
      await cache.put(new URL(request.url).pathname, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(new URL(request.url).pathname, { cacheName: DOCS });
    if (cached !== undefined) return cached;
    throw error;
  }
}

/**
 * Where a failed navigation goes.
 *
 * A reader who tapped a CHAPTER is sent to the offline reader for that same
 * chapter, not to a list — the URL already says what they wanted, and throwing
 * that away to show them an index is making them ask twice. Everything else
 * goes to Downloads, which is the page that can always say what is here.
 */
async function fallback(url) {
  const reader = READER_URL.exec(url.pathname);
  if (reader !== null && (await caches.match(READ_PATH, { cacheName: DOCS })) !== undefined) {
    const to = new URL(READ_PATH, url.origin);
    // Decoded before re-encoding: the chapter key is percent-encoded in the
    // path, and carrying it across as-is would double-encode it and match no
    // chapter at all.
    to.searchParams.set("book", decodeURIComponent(reader[1]));
    to.searchParams.set("chapter", decodeURIComponent(reader[2]));
    return Response.redirect(to.toString(), 302);
  }

  const saved = await caches.match(OFFLINE_PATH, { cacheName: DOCS });
  return saved === undefined
    ? new Response("Offline.", { status: 503, headers: { "Content-Type": "text/plain" } })
    : Response.redirect(OFFLINE_PATH, 302);
}
