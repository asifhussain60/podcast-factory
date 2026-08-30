/**
 * POST /api/brief/reveal { bucket } → open that content shelf in Finder.
 *
 * The Astro site runs as a local Node process, so it can do what the browser
 * cannot: show the operator the folder their commission will land in, beside
 * the neighbours already there.
 *
 * This spawns a process, so the rules are tight and deliberate:
 *   - the client sends a BUCKET NAME, never a path, and it is checked against
 *     the BUCKETS allowlist before anything else happens;
 *   - the path is resolved server-side through bucketDir(), the same resolver
 *     the rest of the site uses, so a traversal attempt has nothing to reach;
 *   - `open` is spawned with an argument ARRAY and no shell, so nothing in the
 *     value can be interpreted as a command even if the allowlist were wrong;
 *   - macOS only, reported plainly rather than failing silently elsewhere.
 */
import type { APIRoute } from "astro";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { BUCKETS, bucketDir, type Bucket } from "../../../lib/content-paths";

export const prerender = false;

const ALLOWED = new Set<string>(BUCKETS);

export const POST: APIRoute = async ({ request }) => {
  if (process.platform !== "darwin") {
    return apiError("Finder is only available on macOS", 501);
  }

  let body: { bucket?: string };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const bucket = (body.bucket ?? "").trim();
  if (!ALLOWED.has(bucket)) {
    return apiError(`Not a content shelf: ${bucket || "(none)"}`);
  }

  const dir = bucketDir(bucket as Bucket);
  try {
    // A shelf with no content yet has no folder. Creating it is the honest
    // thing to do here -- it is where this piece is going regardless, and an
    // empty directory is exactly what Finder should show.
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    spawn("open", [dir], { detached: true, stdio: "ignore" }).unref();
    return apiOk({ opened: dir });
  } catch (e) {
    return apiServerError(`Could not open ${dir}: ${String(e)}`);
  }
};
