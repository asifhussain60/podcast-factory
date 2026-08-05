/**
 * Studio stage-review API (WC8 write-back loop).
 *   GET  /api/studio/review?slug=X&chapter=Y         — read per-stage approval state
 *   POST /api/studio/review  {slug,chapter,stage,approved,notes?} — set a stage's approval
 *   POST /api/studio/review  {slug,chapter,finalize}             — set the chapter finalize flag
 *
 * The editor calls POST when the reviewer approves a stage (or finalizes the chapter via the
 * Publish button); the orchestrator reads the same file to decide whether to resume.
 */
import type { APIRoute } from "astro";
import {
  readReview,
  setStageReview,
  setChapterFinalized,
} from "../../../lib/reader/stage-review";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug");
  const chapter = url.searchParams.get("chapter");
  if (!slug || !chapter || !SLUG_RE.test(slug))
    return apiError("Missing or invalid slug/chapter");
  try {
    return apiOk(readReview(slug, chapter));
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: {
    slug?: string;
    chapter?: string;
    stage?: string;
    approved?: boolean;
    notes?: string;
    finalize?: boolean;
  };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { slug, chapter, stage, approved, notes, finalize } = body;
  if (!slug || !chapter || !SLUG_RE.test(slug)) {
    return apiError("Missing or invalid slug/chapter");
  }
  try {
    // Chapter-level finalize (Publish button): {finalize:boolean}, no stage required.
    if (typeof finalize === "boolean") {
      return apiOk(setChapterFinalized(slug, chapter, finalize));
    }
    if (!stage) return apiError("Missing or invalid stage");
    return apiOk(
      setStageReview(slug, chapter, stage, approved !== false, notes),
    );
  } catch (e) {
    return apiServerError(String(e));
  }
};
