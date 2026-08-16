/**
 * Serves `/media/*` on localhost straight off the one disk copy every
 * recording, PDF and cover already has — instead of requiring a SECOND copy in
 * the local R2 bucket, which is what `--no-audio` in `upload_listener_media.py`
 * was written to avoid (Asif, 2026-08-10: "I do not want content copied twice
 * for books"). Before this plugin, that rule had a side effect nobody wanted:
 * the Listen tab (and the print edition, and chapter read-aloud) never
 * appeared on localhost at all for ANY book, because the app's only way to
 * play a recording was to fetch it from R2, and R2 locally was always empty by
 * design (2026-08-16 RCA).
 *
 * This is a Vite dev-server middleware, not Worker code — it runs in the
 * plain Node process Vite itself runs in, which is the ONLY part of this dev
 * stack with real filesystem access. The SSR loaders and the `/media/*`
 * resource route (`app/routes/media.$slug.$.tsx`) execute inside workerd (via
 * `@cloudflare/vite-plugin`, in dev exactly as in production), and workerd has
 * no disk at all — that constraint is what makes streaming from R2 the only
 * option there, and what makes this a Vite-layer fix rather than a Worker-code
 * one. `catalog.server.ts`'s `servable()` is the OTHER half of this fix: it is
 * what makes the Listen tab render in the first place, by treating a merely
 * INVENTORIED row (not yet uploaded_at-stamped) as playable in dev. The two
 * halves have to agree on what "playable" means, or one says yes and the other
 * 404s.
 *
 * Registered FIRST in `vite.config.ts`'s plugin list, with `apply: "serve"` —
 * that keeps it out of `react-router build` entirely (so it structurally
 * cannot ship to production) and, in dev, lets its middleware claim `/media/*`
 * before `@cloudflare/vite-plugin`'s own routing ever sees the request.
 *
 * Deliberately skips the entitlement check `app/middleware/entitled.ts` runs
 * for the real route. That check exists to stop one signed-in reader on the
 * live multi-tenant site from reaching a book nobody granted them — a concern
 * that does not exist on a single developer's own machine, where the only
 * "reader" who can reach `localhost:5273` is the person running it.
 */
import type { Connect, Plugin } from "vite";
import { DatabaseSync } from "node:sqlite";
import { createReadStream, existsSync } from "node:fs";
import { glob } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseRange } from "../app/lib/media-range.ts";

const LISTENER_DIR = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const REPO_ROOT = path.resolve(LISTENER_DIR, "..");
const D1_STATE_DIR = path.join(
  LISTENER_DIR,
  ".wrangler/state/v3/d1/miniflare-D1DatabaseObject",
);

interface MediaRow {
  content_type: string;
  bytes: number;
  source_path: string;
}

/** The local D1 sqlite file, found by content rather than by a name that can
 * change if the local database is ever recreated (it is a random per-object
 * hash, not something wrangler promises to keep stable). */
async function findLocalD1(): Promise<string | null> {
  if (!existsSync(D1_STATE_DIR)) return null;
  for await (const entry of glob("*.sqlite", { cwd: D1_STATE_DIR })) {
    const candidate = path.join(D1_STATE_DIR, entry);
    try {
      const db = new DatabaseSync(candidate, { readOnly: true });
      const hit = db
        .prepare("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'media_asset'")
        .get();
      db.close();
      if (hit) return candidate;
    } catch {
      // Not a sqlite file, or not this database — keep looking.
    }
  }
  return null;
}

function lookup(dbPath: string, key: string): MediaRow | undefined {
  const db = new DatabaseSync(dbPath, { readOnly: true });
  try {
    return db
      .prepare(`SELECT content_type, bytes, source_path FROM media_asset WHERE key = ?`)
      .get(key) as MediaRow | undefined;
  } finally {
    db.close();
  }
}

export function localMediaDevPlugin(): Plugin {
  return {
    name: "podcast-factory:local-media",
    apply: "serve",
    configureServer(server) {
      let dbPathPromise: Promise<string | null> | null = null;

      const handler: Connect.NextHandleFunction = async (req, res, next) => {
        if (!req.url?.startsWith("/media/")) return next();
        if (req.method !== "GET" && req.method !== "HEAD") return next();

        const key = decodeURIComponent(req.url.slice("/media/".length).split("?")[0] ?? "");
        if (!key) return next();

        dbPathPromise ??= findLocalD1();
        const dbPath = await dbPathPromise;
        if (dbPath === null) return next();

        let row: MediaRow | undefined;
        try {
          row = lookup(dbPath, key);
        } catch {
          return next();
        }
        if (row === undefined) return next();

        const filePath = path.join(REPO_ROOT, row.source_path);
        if (!existsSync(filePath)) return next();

        const range = req.method === "GET" ? parseRange(req.headers.range ?? null, row.bytes) : null;

        res.setHeader("Content-Type", row.content_type);
        res.setHeader("Accept-Ranges", "bytes");
        res.setHeader("Cache-Control", "private, max-age=604800");

        if (range !== null) {
          res.statusCode = 206;
          res.setHeader("Content-Length", String(range.length));
          res.setHeader(
            "Content-Range",
            `bytes ${range.offset}-${range.offset + range.length - 1}/${row.bytes}`,
          );
        } else {
          res.statusCode = 200;
          res.setHeader("Content-Length", String(row.bytes));
        }

        if (req.method === "HEAD") return void res.end();

        const stream =
          range === null
            ? createReadStream(filePath)
            : createReadStream(filePath, { start: range.offset, end: range.offset + range.length - 1 });
        stream.on("error", () => res.destroy());
        stream.pipe(res);
      };

      // Registered directly (not returned) so it lands in the middleware
      // stack ahead of @cloudflare/vite-plugin's own `/media/*` routing,
      // which it installs from a RETURNED configureServer closure — Vite
      // calls those only after every plugin's own body has run.
      server.middlewares.use(handler);
    },
  };
}
