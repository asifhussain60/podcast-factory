/**
 * draft.ts — POST/DELETE /api/studio/draft
 *
 * The "retain my edits without approving" half of the Studio two-phase model.
 *   POST   { slug, chapter, stage, content } — autosave in-progress edits to the
 *           per-stage draft (overwrites). Called debounced as the reviewer edits.
 *   DELETE { slug, chapter, stage }          — discard the draft (revert to canonical).
 *
 * Approval is a SEPARATE action (save-stage.ts): it promotes the draft to the
 * canonical chapter file and deletes the draft. See lib/reader/stage-draft.ts.
 */
import type { APIRoute } from "astro";
import { writeDraft, deleteDraft } from "../../../lib/reader/stage-draft";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ALLOWED_STAGES = new Set([
  "source",
  "core",
  "denoised",
  "normalized",
  "augmented",
  "narrator",
]);

function parseKey(
  body: Record<string, unknown>,
): { slug: string; chapter: string; stage: string } | Response {
  const slug = String(body.slug ?? "").trim();
  const chapter = String(body.chapter ?? "").trim();
  const stage = String(body.stage ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!SLUG_RE.test(chapter)) return apiError("Invalid chapter slug");
  if (!ALLOWED_STAGES.has(stage)) return apiError(`Unknown stage "${stage}"`);
  if (!findContentDirSync(slug))
    return apiError(`Book not found: ${slug}`, 404);
  return { slug, chapter, stage };
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const key = parseKey(body);
  if (key instanceof Response) return key;
  const content = String(body.content ?? "");
  if (!content.trim()) return apiError("Content is empty — nothing to draft");

  try {
    writeDraft(key.slug, key.chapter, key.stage, content);
    return apiOk({ ...key, saved: true });
  } catch (e) {
    return apiServerError(`Failed to write draft: ${String(e)}`);
  }
};

export const DELETE: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const key = parseKey(body);
  if (key instanceof Response) return key;

  try {
    const removed = deleteDraft(key.slug, key.chapter, key.stage);
    return apiOk({ ...key, removed });
  } catch (e) {
    return apiServerError(`Failed to delete draft: ${String(e)}`);
  }
};
