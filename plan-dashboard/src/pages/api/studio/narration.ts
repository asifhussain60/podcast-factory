/**
 * narration.ts — the Book Composer's "Generate narration" action.
 *
 * POST { slug } — spawn scripts/podcast/generate_reader_narration.py DETACHED
 * (Azure TTS renders one clip per paragraph across the whole chapter set, so
 * it can never run in-request) and return { pid }. The Python engine is a
 * thin wrapper around reader_narration.render_reader_narration — the SAME
 * function the publish-time driver calls — so a chapter narrated here before
 * publish and a chapter narrated automatically at publish time can never
 * diverge, and re-renders are incremental (only chapters whose source text
 * changed since their last render are re-synthesized).
 *
 * GET ?slug=<slug> — poll _system/narration-status.json
 * ({ state: running | done | skipped | error, rendered, skipped, reason }).
 * Mirrors the rearticulate.ts launch/status pattern (the proven
 * detached-spawn shape) and studio/generate-book-pdf.ts's manifest read.
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
  return join(bookDir, "_system", "narration-status.json");
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
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!existsSync(join(bookDir, "book", "book.md")))
    return apiError("book.md not found", 404);

  // One run per book at a time — a second spawn would race the first on the
  // narration manifest.
  const prior = readStatus(bookDir);
  if (prior?.state === "running" && pidAlive(prior.pid))
    return apiError("Narration is already generating for this book", 409);

  try {
    const pid = spawnDetachedPython("generate_reader_narration.py", [slug]);
    // Stamp the status file NOW so the page's first poll can never read a
    // stale "done" from a previous run; the Python worker overwrites this in
    // seconds (same pid), and if it dies before doing so the GET's liveness
    // check turns this into an error instead of a forever-shimmer.
    writeFileSync(
      statusPath(bookDir),
      JSON.stringify(
        { state: "running", started_at: new Date().toISOString(), pid },
        null,
        2,
      ) + "\n",
      "utf-8",
    );
    return apiOk({ slug, pid });
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
  // A "running" whose process died without writing a terminal state is an
  // error, not a forever-shimmer.
  if (status.state === "running" && !pidAlive(status.pid))
    return apiOk({
      ...status,
      state: "error",
      error: "worker exited without a result",
    });
  return apiOk(status);
};
