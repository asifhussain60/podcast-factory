/**
 * The screenshots a commission's chapter list is worked out FROM, and the list
 * Claude Code works out from them.
 *
 *   POST   (multipart)  slug + images        -> saved, returns the set
 *   GET    ?slug=                            -> the set, plus any worked-out list
 *   DELETE ?slug=&name=                      -> remove one image
 *
 * WHY NOT THE STAGING AREA. `intake_staging.sweep_stale` deletes a staging
 * session after 24 hours, and these outlive that by design: a contents page
 * photographed today is the evidence for a chapter list settled next week. They
 * live in the brief's own folder, which is already the durable home for a
 * commission's files (see api/brief/generate.ts, which copies staged sources
 * there for exactly this reason).
 *
 * WHY NOT AN UPLOAD ROLE. A screenshot of a contents page is not source
 * material the pipeline reads — it is evidence for ONE decision. Given a role
 * it would arrive in front of the OCR step as though it were the book.
 *
 * NOTHING HERE CALLS A MODEL. The reading is done by Claude Code, which has the
 * transcript open beside the images; this endpoint stores what it is given and
 * hands back what was written. See CHAPTERS_NAME's shape below.
 */
import type { APIRoute } from "astro";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { getRepoRoot } from "../../../lib/content-paths";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);
/** A screenshot of a page of text. 25 MB is far above any of them and far below
 *  a size that would make the folder unwieldy. */
const MAX_BYTES = 25 * 1024 * 1024;
const MAX_IMAGES = 40;

/**
 * What Claude Code writes back, and the ONLY file this endpoint reads as a
 * result:
 *
 *   { "chapters": [ { "title": "Love of the World", "covered": true }, ... ],
 *     "note": "optional one-line summary of what was and was not covered" }
 *
 * `covered` is whether the TRANSCRIPT reaches that chapter, which is a
 * different question from whether the contents page lists it — this repo
 * learned that the hard way on `purification-of-the-heart`, whose book has 29
 * chapters and whose two recordings cover 24 of them.
 */
const CHAPTERS_NAME = "chapters.json";

export interface ChapterFinding {
  title: string;
  covered?: boolean;
}

function dirFor(slug: string): string {
  return join(
    getRepoRoot(),
    "content",
    "_system",
    "briefs",
    slug,
    "chapter-sources",
  );
}

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

/** Saved images, oldest first. The names are zero-padded on write, so the
 *  lexical order IS the order they were added. */
function listImages(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((n) => IMAGE_EXT.has(ext(n)))
    .sort();
}

/** The worked-out list, or null. A malformed file reads as absent rather than
 *  taking the page down — it is written by hand often enough to be typoed. */
export function readChapters(
  dir: string,
): { chapters: ChapterFinding[]; note?: string } | null {
  const p = join(dir, CHAPTERS_NAME);
  if (!existsSync(p)) return null;
  try {
    const parsed = JSON.parse(readFileSync(p, "utf8"));
    const raw = Array.isArray(parsed) ? parsed : parsed?.chapters;
    if (!Array.isArray(raw)) return null;
    const chapters: ChapterFinding[] = raw
      .map((c: unknown) =>
        typeof c === "string"
          ? { title: c.trim(), covered: true }
          : {
              title: String((c as ChapterFinding)?.title ?? "").trim(),
              // Absent means covered: a list with no coverage marks at all is a
              // plain contents page, and every chapter on it is in play.
              covered: (c as ChapterFinding)?.covered !== false,
            },
      )
      .filter((c) => c.title !== "");
    if (!chapters.length) return null;
    const note = typeof parsed?.note === "string" ? parsed.note : undefined;
    return { chapters, note };
  } catch {
    return null;
  }
}

function slugFrom(url: URL): string | null {
  const slug = (url.searchParams.get("slug") ?? "").trim();
  return SLUG_RE.test(slug) ? slug : null;
}

export const GET: APIRoute = async ({ url }) => {
  const slug = slugFrom(url);
  if (!slug) return apiError("Folder name is missing or malformed");
  try {
    const dir = dirFor(slug);
    return apiOk({ images: listImages(dir), found: readChapters(dir), dir });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return apiError("expected multipart/form-data");
  }

  const slug = (form.get("slug") as string | null)?.trim() ?? "";
  if (!SLUG_RE.test(slug))
    return apiError("Folder name is missing or malformed");

  const files = form
    .getAll("images")
    .filter(
      (f): f is File => typeof f === "object" && f !== null && "size" in f,
    );
  if (!files.length) return apiError("no images were sent");

  const dir = dirFor(slug);
  const rejected: { filename: string; reason: string }[] = [];
  try {
    mkdirSync(dir, { recursive: true });
    let n = listImages(dir).length;
    for (const f of files) {
      if (n >= MAX_IMAGES) {
        rejected.push({ filename: f.name, reason: `more than ${MAX_IMAGES}` });
        continue;
      }
      // A clipboard paste arrives as "image.png" every time, so the stored name
      // is the position — which is also what keeps the pages in the order they
      // were added, and the order a contents page has to be read in.
      const e = IMAGE_EXT.has(ext(f.name)) ? ext(f.name) : ".png";
      if (f.size > MAX_BYTES) {
        rejected.push({ filename: f.name, reason: "over 25 MB" });
        continue;
      }
      if (f.size === 0) {
        rejected.push({ filename: f.name, reason: "empty" });
        continue;
      }
      const bytes = Buffer.from(await f.arrayBuffer());
      writeFileSync(join(dir, `${String(n + 1).padStart(2, "0")}${e}`), bytes);
      n += 1;
    }
    return apiOk({ images: listImages(dir), rejected, dir });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const DELETE: APIRoute = async ({ url }) => {
  const slug = slugFrom(url);
  if (!slug) return apiError("Folder name is missing or malformed");
  const name = (url.searchParams.get("name") ?? "").trim();
  // Never join an unvalidated name onto a path: the only names accepted are the
  // ones this endpoint itself writes.
  if (!/^\d{2,}\.(png|jpe?g|webp|gif)$/.test(name))
    return apiError("not a file this endpoint wrote");
  try {
    const dir = dirFor(slug);
    rmSync(join(dir, name), { force: true });
    return apiOk({ images: listImages(dir) });
  } catch (e) {
    return apiServerError(String(e));
  }
};
