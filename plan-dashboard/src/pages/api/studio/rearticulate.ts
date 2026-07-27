/**
 * rearticulate.ts — the Book Composer's Rearticulate action.
 *
 * POST { slug, chapterKey } — spawn scripts/podcast/rearticulate_chapter.py
 * DETACHED (a long chapter windows into multiple claude -p calls at a 900 s
 * timeout each; this can never run in-request) and return { pid }. The Python
 * engine resolves the chapter key through the pipeline's own anchor_key, runs
 * the fluency-pass gates per window (a failed window REVERTS to its base), and
 * records the result in _system/composer-edits.json exactly like a human
 * Composer save. Contract: docs/standards/book-articulation.md (REQ-BA-*).
 *
 * GET ?slug=<slug> — poll _system/rearticulate-status.json
 * ({ state: running | done | error, record }). The page polls this while the
 * chapter shimmers, then reloads from disk. Mirrors the intake launch/status
 * pattern (the proven detached-spawn shape).
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { spawnDetachedPython } from "../../../lib/intake-cli";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function statusPath(bookDir: string): string {
  return join(bookDir, "_system", "rearticulate-status.json");
}

function readStatus(bookDir: string): Record<string, unknown> | null {
  const path = statusPath(bookDir);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    return null;
  }
}

function pidAlive(pid: unknown): boolean {
  if (typeof pid !== "number" || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const slug = String(body.slug ?? "").trim();
  const chapterKey = String(body.chapterKey ?? "")
    .trim()
    .toLowerCase();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapterKey) return apiError("Missing chapterKey");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!existsSync(join(bookDir, "book", "book.md")))
    return apiError("book.md not found", 404);

  // One run per book at a time — a second spawn would race the first on book.md.
  const prior = readStatus(bookDir);
  if (prior?.state === "running" && pidAlive(prior.pid))
    return apiError("A rearticulation is already running for this book", 409);

  try {
    const pid = spawnDetachedPython("rearticulate_chapter.py", [
      slug,
      chapterKey,
    ]);
    // Stamp the status file NOW so the page's first poll can never read a stale
    // "done" from a previous run; the Python worker overwrites this in seconds
    // (same pid), and if it dies before doing so the GET's liveness check turns
    // this into an error instead of a forever-shimmer.
    writeFileSync(
      statusPath(bookDir),
      JSON.stringify(
        {
          chapter_key: chapterKey,
          state: "running",
          started_at: new Date().toISOString(),
          pid,
        },
        null,
        2,
      ) + "\n",
      "utf-8",
    );
    return apiOk({ slug, chapterKey, pid });
  } catch (e) {
    return apiServerError(`Launch failed: ${String(e)}`);
  }
};

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug") ?? "";
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  const status = readStatus(bookDir);
  if (!status) return apiOk({ state: "none" });
  // A "running" whose process died without writing a terminal state is an error,
  // not a forever-shimmer.
  if (status.state === "running" && !pidAlive(status.pid))
    return apiOk({ ...status, state: "error", error: "worker exited without a result" });
  return apiOk(status);
};
