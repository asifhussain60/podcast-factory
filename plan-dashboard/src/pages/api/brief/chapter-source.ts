/**
 * GET /api/brief/chapter-source?slug=…&name=…  -> the bytes of one saved screenshot.
 *
 * Its own route because the thumbnails in ChapterSources are <img src>, which
 * needs a URL that answers with image bytes — the JSON endpoint beside it
 * (chapter-sources.ts, plural) lists and stores them but cannot serve one.
 *
 * `name` is matched against the exact shape that endpoint writes and nothing
 * else, so no value from the query string is ever joined onto a path as given.
 * A dev-only surface still reads local files, and "it is only local" is how
 * path traversal ships.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { getRepoRoot } from "../../../lib/content-paths";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const NAME_RE = /^\d{2,}\.(png|jpe?g|webp|gif)$/;

const MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

export const GET: APIRoute = async ({ url }) => {
  const slug = (url.searchParams.get("slug") ?? "").trim();
  const name = (url.searchParams.get("name") ?? "").trim();
  if (!SLUG_RE.test(slug) || !NAME_RE.test(name))
    return new Response("not found", { status: 404 });

  const path = join(
    getRepoRoot(),
    "content",
    "_system",
    "briefs",
    slug,
    "chapter-sources",
    name,
  );
  if (!existsSync(path)) return new Response("not found", { status: 404 });

  const ext = name.slice(name.lastIndexOf(".")).toLowerCase();
  return new Response(new Uint8Array(readFileSync(path)), {
    headers: {
      "content-type": MIME[ext] ?? "application/octet-stream",
      // The bytes never change under a name — a new page is written to the next
      // number — but the name is reused after a delete, so this must revalidate.
      "cache-control": "no-cache",
    },
  });
};
