/**
 * text-align.ts — the browser↔disk boundary for per-paragraph alignment.
 *
 *   GET /api/studio/text-align?slug=X   — every chapter's alignments
 *   PUT /api/studio/text-align
 *       { slug, chapterKey, paras: { "<paraFingerprint>": "center" | "right" } }
 *                                       — replace ONE chapter's map
 *
 * Writes `_system/text-align.json`; book.md is never touched. Guards mirror
 * text-colour.ts: slug shape, a bounded chapter key, and an allow-list on every
 * value before it can reach a class name.
 */
import type { APIRoute } from "astro";
import {
  readAlign,
  writeChapterAlign,
} from "../../../lib/reader/text-align.server";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
/** `anchorKey` output — lowercase words separated by single spaces. Bounded and
 *  free of dots and slashes, so a key can never be read as a path. */
const CHAPTER_KEY_RE = /^[^./\\]{1,200}$/;

export const GET: APIRoute = ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  try {
    return apiOk({ slug, ...readAlign(slug) });
  } catch (e) {
    return apiServerError(`Failed to read text-align.json: ${String(e)}`);
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
  const chapterKey = String(body.chapterKey ?? "").trim();
  if (!CHAPTER_KEY_RE.test(chapterKey)) return apiError("Invalid chapterKey");
  if (!body.paras || typeof body.paras !== "object")
    return apiError("paras must be an object");
  try {
    const doc = writeChapterAlign(slug, chapterKey, body.paras);
    return apiOk({ slug, chapterKey, paras: doc.chapters[chapterKey] ?? {} });
  } catch (e) {
    return apiServerError(`Failed to write text-align.json: ${String(e)}`);
  }
};
