/**
 * read-along-audio.ts — stream a book's recording, seekably.
 *
 * GET ?slug=<slug>&path=<path inside the book folder>
 *
 * WHY THIS EXISTS BESIDE `api/library/file`. That endpoint reads a whole file
 * into a buffer and answers with it, which is right for a PDF and wrong twice
 * over here: these recordings are 500-600 MB each, so a buffered read is that
 * much memory per request, and without range support a browser cannot SEEK —
 * it can only play from the start. Read-along is seeking: every click on a
 * paragraph jumps the audio to the second that paragraph was spoken.
 *
 * So this streams, and answers a `Range` request with a 206 and only the bytes
 * asked for. `accept-ranges` is advertised unconditionally, because a player
 * that is not told the server supports ranges disables its own scrubber.
 *
 * The path safety is the same rule `api/library/file` applies and for the same
 * reason: `realpath` first, so a symlink cannot walk out of the book's folder,
 * and a resolved target outside it is refused rather than served.
 */
import type { APIRoute } from "astro";
import { createReadStream } from "node:fs";
import { realpath, stat } from "node:fs/promises";
import { normalize, resolve } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MIME: Record<string, string> = {
  ".mp3": "audio/mpeg",
  ".m4a": "audio/mp4",
  ".wav": "audio/wav",
  ".ogg": "audio/ogg",
};

/** `bytes=0-1023`, `bytes=500-`, `bytes=-500`. Null when absent or unusable. */
export function parseRange(
  header: string | null,
  size: number,
): { start: number; end: number } | null {
  if (!header) return null;
  const m = /^bytes=(\d*)-(\d*)$/.exec(header.trim());
  if (!m) return null;
  const [, rawStart, rawEnd] = m;
  if (rawStart === "" && rawEnd === "") return null;
  // A suffix range asks for the LAST n bytes, which players use to read the
  // trailing metadata of an MP3 before deciding how to scrub it.
  let start = rawStart === "" ? size - Number(rawEnd) : Number(rawStart);
  let end = rawStart === "" || rawEnd === "" ? size - 1 : Number(rawEnd);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  start = Math.max(0, start);
  end = Math.min(size - 1, end);
  if (start > end) return null;
  return { start, end };
}

export const GET: APIRoute = async ({ url, request }) => {
  const slug = url.searchParams.get("slug") ?? "";
  const relPath = url.searchParams.get("path") ?? "";
  if (!SLUG_RE.test(slug) || !relPath) {
    return new Response("missing slug or path", { status: 400 });
  }

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return new Response("content not found", { status: 404 });

  let target: string;
  try {
    // realpath follows symlinks BEFORE the containment check, so a link inside
    // the book folder cannot point at something outside it.
    target = await realpath(resolve(bookDir, normalize(relPath)));
    const dir = await realpath(resolve(bookDir));
    if (!target.startsWith(dir + "/")) {
      return new Response("path escapes content dir", { status: 400 });
    }
  } catch {
    return new Response("not found", { status: 404 });
  }

  const ext = target.slice(target.lastIndexOf(".")).toLowerCase();
  const mime = MIME[ext];
  if (!mime) return new Response("not an audio file", { status: 400 });

  const info = await stat(target).catch(() => null);
  if (!info || !info.isFile())
    return new Response("not found", { status: 404 });

  const range = parseRange(request.headers.get("range"), info.size);
  const headers: Record<string, string> = {
    "content-type": mime,
    "accept-ranges": "bytes",
  };

  if (!range) {
    headers["content-length"] = String(info.size);
    return new Response(createReadStream(target) as unknown as ReadableStream, {
      headers,
    });
  }

  headers["content-length"] = String(range.end - range.start + 1);
  headers["content-range"] = `bytes ${range.start}-${range.end}/${info.size}`;
  return new Response(
    createReadStream(target, {
      start: range.start,
      end: range.end,
    }) as unknown as ReadableStream,
    { status: 206, headers },
  );
};
