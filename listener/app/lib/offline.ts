/**
 * Episodes kept on the device.
 *
 * WHY INDEXEDDB AND AN OBJECT URL, rather than a service worker that answers
 * requests for /media/* out of the Cache API. Both would work on paper; only
 * this one is reliable on the device almost all of this listening happens on.
 *
 *   1. A media element will not play a response that cannot be seeked, so a
 *      service worker serving audio has to parse the Range header and hand back
 *      a synthetic 206 itself — the Cache API cannot store a partial response,
 *      so it must cache the whole object and slice it per request. That is a
 *      second implementation of byte-range serving living in the browser, next
 *      to the real one in routes/media.$slug.$.tsx.
 *   2. Media requests reaching the service worker at all has a long history of
 *      WebKit bugs behind it.
 *
 * A blob URL has neither problem: seeking is the browser's own, and nothing is
 * intercepted. The service worker in public/sw.js therefore does not touch audio
 * at all — it exists so the SITE opens with no network, which is a different job.
 *
 * WHAT IS DELIBERATELY NOT HERE: any decision about who may keep an episode.
 * Downloading is available for whatever the book page already showed this
 * viewer, and the book page is behind `requireUnitAccess` — so the entitlement
 * rule is enforced in the one place it is written, not restated here. What this
 * file does own is the LEASE: `purgeExcept` below deletes what a viewer may no
 * longer read, and it is written to be safe when the answer is unknown.
 */

const DB_NAME = "pf-offline";
const DB_VERSION = 1;

/** Metadata only. Read to draw a list, so it must never carry the audio. */
const META = "meta";
/** key -> Blob. Read once at startup and otherwise only written. */
const BLOBS = "blobs";

/**
 * Chunk size while downloading.
 *
 * The obvious loop — read the whole body into an array of Uint8Arrays, then
 * `new Blob(chunks)` — holds the entire episode in memory first, and these run
 * to 97 MB. Collecting into intermediate Blobs instead caps that: a Blob is
 * disk-backed, and `new Blob([blobA, blobB])` concatenates by reference rather
 * than by reading either one back. So the peak is this number, not the episode.
 */
const CHUNK_BYTES = 4 * 1024 * 1024;

export interface DownloadMeta {
  /** The player's own identity for an episode — `/media/<audioKey>`. */
  src: string;
  slug: string;
  bookTitle: string;
  number: number;
  title: string;
  durationS: number | null;
  /** WebVTT text, kept beside the audio so the transcript works offline too. */
  transcript: string | null;
  bytes: number;
  savedAt: number;
}

/* ---- The database ------------------------------------------------------- */

function idb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("no IndexedDB"));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(META)) db.createObjectStore(META, { keyPath: "src" });
      if (!db.objectStoreNames.contains(BLOBS)) db.createObjectStore(BLOBS);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB refused to open"));
  });
}

/** One transaction, promisified. `mode` decides whether it may write. */
function tx<T>(
  stores: string[],
  mode: IDBTransactionMode,
  body: (t: IDBTransaction) => Promise<T> | T,
): Promise<T> {
  return idb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(stores, mode);
        let result: T;
        // Resolve on COMPLETE, not on the last request's success: a write is not
        // durable until the transaction commits, and resolving early would let a
        // caller report "downloaded" for bytes that are still in flight.
        t.oncomplete = () => resolve(result);
        t.onerror = () => reject(t.error ?? new Error("offline store write failed"));
        t.onabort = () => reject(t.error ?? new Error("offline store aborted"));
        void Promise.resolve(body(t)).then((value) => {
          result = value;
        }, reject);
      }),
  );
}

/** One IDBRequest, promisified. */
function done<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("offline store read failed"));
  });
}

/* ---- What is playable right now ----------------------------------------- */

/**
 * `/media/…` -> a blob URL for the copy on this device.
 *
 * Filled by `hydrate()` at startup and read SYNCHRONOUSLY by the player, which
 * is the whole reason it exists. `play()` must call `element.play()` inside the
 * gesture that asked for it — every mobile browser refuses playback started from
 * an async continuation — so resolving a source cannot involve awaiting a
 * database read. Startup pays that cost once instead.
 */
const urls = new Map<string, string>();

/** Metadata for what is on the device, kept in step with `urls`. */
let index: DownloadMeta[] = [];

const listeners = new Set<() => void>();

function announce() {
  for (const fn of listeners) fn();
}

/** Re-render me when what is downloaded changes. Returns the unsubscribe. */
export function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** What is on the device, newest first. A snapshot; safe to render directly. */
export function downloads(): DownloadMeta[] {
  return index;
}

/** The local copy of this episode, or null to play it from the network. */
export function localUrl(src: string): string | null {
  return urls.get(src) ?? null;
}

export function isDownloaded(src: string): boolean {
  return urls.has(src);
}

export function totalBytes(): number {
  return index.reduce((sum, item) => sum + item.bytes, 0);
}

/**
 * Read every stored episode and mint a blob URL for each.
 *
 * Called once, from the agent mounted in the authenticated layout. Reading a
 * Blob OUT of IndexedDB does not read its bytes — the handle is disk-backed, and
 * `createObjectURL` only registers it — so this stays cheap with a full library
 * downloaded.
 */
export async function hydrate(): Promise<void> {
  try {
    const [meta, blobs] = await tx([META, BLOBS], "readonly", async (t) => {
      const m = await done(t.objectStore(META).getAll() as IDBRequest<DownloadMeta[]>);
      const b = await done(t.objectStore(BLOBS).getAll() as IDBRequest<Blob[]>);
      const keys = await done(t.objectStore(BLOBS).getAllKeys() as IDBRequest<IDBValidKey[]>);
      return [m, new Map(keys.map((k, i) => [String(k), b[i]]))] as const;
    });

    for (const url of urls.values()) URL.revokeObjectURL(url);
    urls.clear();

    for (const item of meta) {
      const blob = blobs.get(item.src);
      // Metadata with no audio behind it is not a download. It is reachable if a
      // write was interrupted between the two stores, and showing it would offer
      // a Play that does nothing.
      if (blob === undefined) continue;
      urls.set(item.src, URL.createObjectURL(blob));
    }

    index = meta
      .filter((item) => urls.has(item.src))
      .sort((a, b) => b.savedAt - a.savedAt);
    announce();
  } catch {
    // No IndexedDB, or the browser refused it (private browsing on some
    // platforms). The site works exactly as it did before downloads existed.
  }
}

/* ---- Getting one -------------------------------------------------------- */

export interface DownloadProgress {
  /** Bytes written so far. */
  loaded: number;
  /** What the server said the whole thing is, or null when it did not say. */
  total: number | null;
}

/**
 * Fetch an episode and keep it, reporting progress as it goes.
 *
 * `credentials: "same-origin"` is the default for a same-origin fetch and is
 * stated anyway: this request is answered by the media route, which runs the
 * same grant check the book page ran, and it is the cookie that makes that
 * check about the right person.
 */
export async function download(
  meta: Omit<DownloadMeta, "bytes" | "savedAt" | "transcript"> & {
    transcriptSrc: string | null;
  },
  onProgress?: (progress: DownloadProgress) => void,
): Promise<void> {
  const response = await fetch(meta.src, { credentials: "same-origin" });
  if (!response.ok || response.body === null) {
    throw new Error(`Could not fetch this episode (${response.status})`);
  }

  const header = response.headers.get("Content-Length");
  const total = header === null ? null : Number(header);
  const type = response.headers.get("Content-Type") ?? "audio/mp4";

  const reader = response.body.getReader();
  const parts: Blob[] = [];
  let pending: BlobPart[] = [];
  let pendingBytes = 0;
  let loaded = 0;

  for (;;) {
    const { done: finished, value } = await reader.read();
    if (finished) break;
    pending.push(value);
    pendingBytes += value.byteLength;
    loaded += value.byteLength;
    if (pendingBytes >= CHUNK_BYTES) {
      parts.push(new Blob(pending));
      pending = [];
      pendingBytes = 0;
    }
    onProgress?.({ loaded, total: total === null || !Number.isFinite(total) ? null : total });
  }
  if (pending.length > 0) parts.push(new Blob(pending));

  const blob = new Blob(parts, { type });

  // The words, if this episode has any. A failure here is not a failed
  // download: the audio is the point, and a missing transcript offline is the
  // same as a missing transcript online.
  let transcript: string | null = null;
  if (meta.transcriptSrc !== null) {
    transcript = await fetch(meta.transcriptSrc, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.text() : null))
      .catch(() => null);
  }

  const record: DownloadMeta = {
    src: meta.src,
    slug: meta.slug,
    bookTitle: meta.bookTitle,
    number: meta.number,
    title: meta.title,
    durationS: meta.durationS,
    transcript,
    bytes: blob.size,
    savedAt: Date.now(),
  };

  // Both stores in ONE transaction. Written separately, an interrupted download
  // can leave metadata with no audio behind it — a row offering a Play that
  // does nothing.
  await tx([META, BLOBS], "readwrite", (t) => {
    t.objectStore(BLOBS).put(blob, record.src);
    t.objectStore(META).put(record);
  });

  const previous = urls.get(record.src);
  if (previous !== undefined) URL.revokeObjectURL(previous);
  urls.set(record.src, URL.createObjectURL(blob));
  index = [record, ...index.filter((item) => item.src !== record.src)].sort(
    (a, b) => b.savedAt - a.savedAt,
  );
  announce();
}

/** The stored transcript for an episode, or null. Used offline. */
export function localTranscript(src: string): string | null {
  return index.find((item) => item.src === src)?.transcript ?? null;
}

/* ---- Letting go of them ------------------------------------------------- */

async function forget(sources: string[]): Promise<void> {
  if (sources.length === 0) return;

  await tx([META, BLOBS], "readwrite", (t) => {
    for (const src of sources) {
      t.objectStore(BLOBS).delete(src);
      t.objectStore(META).delete(src);
    }
  });

  for (const src of sources) {
    const url = urls.get(src);
    if (url !== undefined) URL.revokeObjectURL(url);
    urls.delete(src);
  }
  index = index.filter((item) => !sources.includes(item.src));
  announce();
}

/** Remove one episode. */
export function remove(src: string): Promise<void> {
  return forget([src]);
}

/** Remove every episode of one book. */
export function removeBook(slug: string): Promise<void> {
  return forget(index.filter((item) => item.slug === slug).map((item) => item.src));
}

/** Remove everything. */
export function removeAll(): Promise<void> {
  return forget(index.map((item) => item.src));
}

/**
 * THE LEASE. Delete downloads for any book this viewer may no longer read.
 *
 * Asif's decision, 2026-08-11: an episode on a phone cannot be re-checked the
 * way `routes/media.$slug.$.tsx` re-checks every byte range it serves, so
 * withdrawing access takes effect the next time the app opens with a network
 * rather than immediately. This is the function that makes "next time" true.
 *
 * It takes the ALLOWED list and removes the complement, and the caller must pass
 * null — never an empty array — when it could not find out. The two are
 * indistinguishable to the reader and opposite in effect: a viewer who genuinely
 * holds nothing should lose their downloads, and a request that failed must
 * change nothing at all. Making the caller choose the shape is what keeps a
 * network error from wiping a library on a plane.
 */
export function purgeExcept(allowed: string[] | null): Promise<void> {
  return forget(sourcesToPurge(index, allowed));
}

/**
 * The lease's whole decision, as a function of two values.
 *
 * Split out from `purgeExcept` so it can be tested without a database, because
 * the rule it encodes is the one place in this feature where a wrong answer
 * destroys something the reader cannot get back on a plane. The two cases that
 * must never merge:
 *
 *   allowed === null   we could not find out — offline, or the request was
 *                      bounced to sign-in. Delete NOTHING.
 *   allowed === []     we asked and this viewer holds nothing. Delete
 *                      everything.
 */
export function sourcesToPurge(
  held: readonly DownloadMeta[],
  allowed: string[] | null,
): string[] {
  if (allowed === null) return [];
  const keep = new Set(allowed);
  return held.filter((item) => !keep.has(item.slug)).map((item) => item.src);
}
