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
 * So exactly two things are kept: hashed build assets, which are immutable and
 * carry no one's data, and the Downloads document, which is the page a listener
 * with no signal actually needs.
 */

const VERSION = "v1";
const ASSETS = `pf-assets-${VERSION}`;
const DOCS = `pf-docs-${VERSION}`;

/** The one page that has to work with no network. */
const OFFLINE_PATH = "/downloads";

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

  if (isDownloadsRequest(url)) {
    event.respondWith(downloadsDocument(request));
    return;
  }

  // Any OTHER navigation, offline: send them to the page that works instead of
  // the browser's error. A redirect rather than serving the Downloads document
  // under the wrong URL — the document carries its own route data, and handing
  // it back for /book/x would hydrate a page that disagrees with the address.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const saved = await caches.match(OFFLINE_PATH, { cacheName: DOCS });
        return saved === undefined
          ? new Response("Offline.", { status: 503, headers: { "Content-Type": "text/plain" } })
          : Response.redirect(OFFLINE_PATH, 302);
      }),
    );
  }
});

/** The Downloads page, and the data React Router fetches when navigating to it. */
function isDownloadsRequest(url) {
  return url.pathname === OFFLINE_PATH || url.pathname === `${OFFLINE_PATH}.data`;
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
async function downloadsDocument(request) {
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
