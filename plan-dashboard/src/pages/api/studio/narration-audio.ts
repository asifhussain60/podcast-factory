/**
 * narration-audio.ts — GET /api/studio/narration-audio?slug=&chapter=
 *
 * Serves one chapter's rendered narration MP3 (book/narration/<anchor>.mp3)
 * to the Book Composer's read-aloud player (compose-narration.ts). The
 * assets live under content/ (not public/), so they need a server route —
 * same reasoning as visual-asset.ts, whose containment-check pattern this
 * mirrors.
 *
 * The manifest (book/narration/manifest.json), not a constructed filename, is
 * the source of truth for which file backs a chapter: `reader_narration.py`
 * keys the manifest by anchor_key but does not further slug-sanitize the MP3
 * filename it writes, so re-deriving the path here would be a second,
 * possibly-diverging answer to a question the manifest already answers.
 *
 * HEAD is supported (no body) because compose-narration.ts polls existence
 * with a HEAD request — the cheapest way to answer "does this chapter have
 * narration yet" without downloading it.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiError, apiNotFound } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

interface ManifestChapterEntry {
  audio?: string;
}
interface Manifest {
  chapters?: Record<string, ManifestChapterEntry>;
}

function resolveAudioPath(bookDir: string, chapterKey: string): string | null {
  const manifestPath = join(bookDir, "book", "narration", "manifest.json");
  if (!existsSync(manifestPath)) return null;
  let manifest: Manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch {
    return null;
  }
  const entry = manifest.chapters?.[chapterKey];
  const rel = entry?.audio;
  if (!rel || typeof rel !== "string") return null;

  const narrationDir = resolve(bookDir, "book", "narration");
  const target = resolve(bookDir, rel);
  // Containment guard: the manifest is JSON on disk, not something a request
  // can edit, but treat it as untrusted input anyway — the same discipline
  // visual-asset.ts applies to a filename that came off a query string.
  if (!target.startsWith(narrationDir + "/") || !existsSync(target))
    return null;
  return target;
}

function respond(
  bookDir: string,
  chapterKey: string,
  includeBody: boolean,
): Response {
  const target = resolveAudioPath(bookDir, chapterKey);
  if (!target) return apiNotFound("narration not available for this chapter");
  const size = statSync(target).size;
  return new Response(includeBody ? readFileSync(target) : null, {
    status: 200,
    headers: {
      "content-type": "audio/mpeg",
      "content-length": String(size),
      "cache-control": "no-store",
    },
  });
}

export const GET: APIRoute = ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  const chapter = String(url.searchParams.get("chapter") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapter) return apiError("Missing chapter");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiNotFound(`Book not found: ${slug}`);
  return respond(bookDir, chapter, true);
};

export const HEAD: APIRoute = ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  const chapter = String(url.searchParams.get("chapter") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapter) return apiError("Missing chapter");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiNotFound(`Book not found: ${slug}`);
  return respond(bookDir, chapter, false);
};
