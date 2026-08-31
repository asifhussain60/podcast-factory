/**
 * read-along.ts — the timings that already exist for one chapter.
 *
 * GET ?slug=<slug>&chapter=<anchor-key>
 *   -> { cues, durationS, audio, voice, engine } | { cues: [] }
 *
 * Reads `book/narration/manifest.json` off disk and hands back ONE chapter's
 * entry. It renders nothing, generates nothing and costs nothing — the manifest
 * is written by the pipeline (`sessions/read_along.py` for a recorded session,
 * `reader_narration.py` for a synthesised one) and this is a read.
 *
 * `engine` is passed through rather than hidden because it changes what the
 * Composer is showing: `author-recording` means the speaker's own voice, and
 * `azure-speech-neural-tts` means a synthesised one. A surface that cannot tell
 * them apart would describe a machine reading as the author reading.
 *
 * An absent manifest is `{ cues: [] }` and a 200, not a 404: a book whose
 * chapters have not been timed yet is an ordinary state, and the Composer draws
 * no transport for it. A 404 would make every untimed book log an error.
 *
 * Sibling of narration.ts, which SPAWNS the synthesiser. This one never writes.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiError, apiOk, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug") ?? "";
  const chapter = url.searchParams.get("chapter") ?? "";
  if (!SLUG_RE.test(slug)) return apiError("bad slug");
  if (!chapter.trim()) return apiError("missing chapter");

  try {
    const bookDir = findContentDirSync(slug);
    if (!bookDir) return apiError("content not found", 404);

    const path = join(bookDir, "book", "narration", "manifest.json");
    if (!existsSync(path)) return apiOk({ cues: [] });

    const manifest = JSON.parse(readFileSync(path, "utf8")) as {
      engine?: string;
      chapters?: Record<
        string,
        {
          title?: string;
          episode?: number;
          audio?: string;
          durationS?: number;
          duration_s?: number;
          voice?: string;
          cues?: unknown[];
        }
      >;
    };

    const entry = manifest.chapters?.[chapter];
    if (!entry) return apiOk({ cues: [] });

    return apiOk({
      cues: Array.isArray(entry.cues) ? entry.cues : [],
      durationS: entry.durationS ?? entry.duration_s ?? 0,
      // The path INSIDE the book folder; the caller asks the audio endpoint for
      // it rather than being handed a filesystem path it could not fetch.
      audio: entry.audio ?? "",
      episode: entry.episode ?? null,
      voice: entry.voice ?? "",
      engine: manifest.engine ?? "",
    });
  } catch (err) {
    return apiServerError(err instanceof Error ? err.message : String(err));
  }
};
