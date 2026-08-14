/**
 * image-layout.ts — the Book Composer's per-image resize/align endpoint.
 *
 *   POST /api/studio/image-layout
 *        body { slug, chapterKey, src, height_px?, align? }
 *        Omitting a field (or passing the default: height_px 350, align
 *        "center") clears that part of the declaration. Writes
 *        `_system/image-layout.json` via image-layout.mjs's writeImageLayout.
 *
 * Deterministic, not AI — a drag-resize is a plain number, never a model
 * call. Mirrors quote-kind.ts's shape.
 */
import type { APIRoute } from "astro";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import {
  writeImageLayout,
  ALIGN_IDS,
  MIN_HEIGHT_PX,
  MAX_HEIGHT_PX,
} from "../../../../scripts/lib/image-layout.mjs";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const chapterKey = String(body.chapterKey ?? "").trim();
  if (!chapterKey) return apiError("chapterKey is required");
  const src = String(body.src ?? "").trim();
  if (!src) return apiError("src is required");

  const heightRaw = body.height_px;
  const height_px =
    heightRaw === undefined || heightRaw === null
      ? undefined
      : Number(heightRaw);
  if (
    height_px !== undefined &&
    (!Number.isInteger(height_px) ||
      height_px < MIN_HEIGHT_PX ||
      height_px > MAX_HEIGHT_PX)
  )
    return apiError(
      `height_px must be an integer ${MIN_HEIGHT_PX}-${MAX_HEIGHT_PX}`,
    );

  const alignRaw = body.align;
  if (alignRaw !== undefined && !ALIGN_IDS.includes(String(alignRaw)))
    return apiError(`align must be one of: ${ALIGN_IDS.join(", ")}`);
  const align = alignRaw === undefined ? undefined : String(alignRaw);

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  try {
    writeImageLayout(bookDir, chapterKey, src, { height_px, align });
    return apiOk({
      slug,
      chapterKey,
      src,
      height_px: height_px ?? null,
      align: align ?? null,
    });
  } catch (e) {
    return apiServerError((e as Error).message);
  }
};
