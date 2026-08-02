/**
 * text-colour.ts — the browser↔disk boundary for per-selection text colour.
 *
 *   GET /api/studio/text-colour?slug=X            — every chapter's spans
 *   PUT /api/studio/text-colour
 *       { slug, chapterKey, spans: [{ quote, ink }] }
 *                                                 — replace ONE chapter's spans
 *
 * Writes `_system/text-colour.json`. book.md is never touched — see
 * scripts/lib/text-colour.mjs for why that is the whole point of the design.
 * Guards mirror citation-style.ts: slug shape, a bounded chapter key, and an
 * allow-list on every ink before it can reach a class name.
 */
import type { APIRoute } from "astro";
import {
  readColours,
  writeChapterColours,
} from "../../../lib/reader/text-colour.server";
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
    return apiOk({ slug, ...readColours(slug) });
  } catch (e) {
    return apiServerError(`Failed to read text-colour.json: ${String(e)}`);
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
  if (!Array.isArray(body.spans)) return apiError("spans must be an array");
  try {
    const doc = writeChapterColours(slug, chapterKey, body.spans);
    return apiOk({ slug, chapterKey, spans: doc.chapters[chapterKey] ?? [] });
  } catch (e) {
    return apiServerError(`Failed to write text-colour.json: ${String(e)}`);
  }
};
