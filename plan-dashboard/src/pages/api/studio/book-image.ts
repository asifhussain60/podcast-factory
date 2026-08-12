/**
 * book-image.ts — GET /api/studio/book-image?slug=&path=<session>/<file>
 *
 * Serves one illustration out of `content/<Bucket>/<slug>/book/images/` to the
 * Book Composer and the reader views.
 *
 * WHY A ROUTE AND NOT A RELATIVE PATH. `book.md` writes `images/<sid>/<guid>.jpg`,
 * relative to `book/`, and that is RIGHT — it is the directory the PDF is built
 * in, so the printed page resolves it as written. Nothing serves that directory
 * over HTTP, so the same source has to resolve two ways and this is the second
 * one. Exactly the split `_listener_book._media_image_srcs` already makes for the
 * Podcast Factory Library, which points the same src at its own gated `/media/`
 * route.
 *
 * WHY NOT `public/`. These are content, under `content/`, and copying 8 MB of a
 * book's diagrams into the site's static folder would make a second copy that
 * goes stale the moment the book is re-ingested. `visual-asset.ts` reached the
 * same conclusion for `book/visuals/` and this follows it deliberately.
 *
 * THE PATH HAS ONE LEVEL, AND THAT IS ENFORCED. `book/images/` is
 * `<session id>/<file>` and nothing else, so the parameter is validated against
 * that shape rather than sanitised — a validated shape cannot express `..` at
 * all, where a sanitiser has to be right about every way of writing it. The
 * resolved path is then checked to be inside the images directory anyway, on the
 * principle that a traversal guard is worth having twice.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { extname, join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiError, apiNotFound } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** `<session id>/<file>.<ext>` — digits, then one filename, then nothing. */
const PATH_RE = /^(\d+)\/([A-Za-z0-9][A-Za-z0-9._-]*\.(?:png|jpe?g|webp))$/;

const MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
};

export const GET: APIRoute = ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  const path = String(url.searchParams.get("path") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!PATH_RE.test(path)) return apiError("Invalid image path");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiNotFound(`Book not found: ${slug}`);

  const root = join(bookDir, "book", "images");
  const target = join(root, path);
  if (!target.startsWith(root + "/") || !existsSync(target)) {
    return apiNotFound("image not found");
  }

  const type = MIME[extname(target).toLowerCase()];
  if (!type) return apiError("Unsupported image type");

  return new Response(readFileSync(target), {
    status: 200,
    // Immutable: the filename is the GUID the KSESSIONS admin assigned, so a
    // different picture is a different name. Same reasoning the media route
    // uses, without the `private` — nothing here is gated, this whole site is.
    headers: { "content-type": type, "cache-control": "max-age=604800" },
  });
};
