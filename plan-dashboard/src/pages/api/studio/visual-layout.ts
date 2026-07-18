/**
 * visual-layout.ts — the Book Composer contract endpoint (Book Pipeline v2).
 *
 *   PUT  /api/studio/visual-layout   body { slug, placements }
 *        Validates + normalizes placements against book.visual-layout/v1 (via the
 *        shared visual-layout.mjs mirror) and writes book/visual-layout.json.
 *        The prior file is backed up as .bak before overwrite.
 *
 * Modeled on save-stage.ts: prerender=false, SLUG_RE validation,
 * findContentDirSync resolution, .bak safety, apiOk/apiError envelopes. The
 * artifact is written as JSON (not YAML) so the Python renderer reads it with
 * stdlib json — the same TS-writes / Python-reads convention as editorial.ts.
 */
import type { APIRoute } from "astro";
import {
  writeFileSync,
  readFileSync,
  existsSync,
  copyFileSync,
  mkdirSync,
} from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
// Shared contract mirror (also consumed by render-book-pdf.mjs + _visual_layout.py).
import { validateLayout, SCHEMA } from "../../../../scripts/visual-layout.mjs";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

// GET /api/studio/visual-layout?slug= — return the current curated layout so the
// Composer (or any client) can re-fetch the contract without a full page reload.
// Reads book/visual-layout.json through the shared validator; absent file => [].
export const GET: APIRoute = async ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  const target = join(bookDir, "book", "visual-layout.json");
  if (!existsSync(target))
    return apiOk({ slug, schema: SCHEMA, placements: [], warnings: [] });
  try {
    const raw = JSON.parse(readFileSync(target, "utf8"));
    const { placements, warnings } = validateLayout(raw);
    return apiOk({ slug, schema: SCHEMA, placements, warnings });
  } catch (e) {
    return apiServerError(`Failed to read visual-layout.json: ${String(e)}`);
  }
};

export const PUT: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const rawPlacements = Array.isArray(body.placements) ? body.placements : [];

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  // Normalize + validate through the shared contract (center=>standalone, wrap
  // width cap, enum fallbacks) so an out-of-contract placement can never persist.
  const { placements, warnings } = validateLayout({
    schema: SCHEMA,
    placements: rawPlacements,
  });

  try {
    const bookSubdir = join(bookDir, "book");
    mkdirSync(bookSubdir, { recursive: true });
    const target = join(bookSubdir, "visual-layout.json");
    const backup = `${target}.bak`;
    if (existsSync(target) && !existsSync(backup)) copyFileSync(target, backup);

    writeFileSync(
      target,
      JSON.stringify({ schema: SCHEMA, placements }, null, 2) + "\n",
      "utf8",
    );
    return apiOk({ slug, count: placements.length, warnings });
  } catch (e) {
    return apiServerError(`Failed to write visual-layout.json: ${String(e)}`);
  }
};
