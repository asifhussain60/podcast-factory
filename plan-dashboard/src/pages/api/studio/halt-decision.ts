/**
 * halt-decision.ts — POST /api/studio/halt-decision
 *
 * Records a reviewer's decision on a pipeline halt (see lib/studio/halts.ts)
 * into BOOK_DIR/_system/halt-reviews.json — a map of haltId -> { decision,
 * notes, ts }. The orchestrator can read this file to decide whether to resume
 * past the halt. This endpoint never runs git or the pipeline; it only writes
 * the decision file.
 *
 * Body: { slug, haltId, decision: 'approved' | 'changes', notes? }
 */
import type { APIRoute } from "astro";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join, dirname } from "node:path";
import { findContent } from "../../../lib/content-paths";
import { HALTS, type HaltReviews } from "../../../lib/studio/halts";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const HALT_IDS = new Set(HALTS.map((h) => h.id));

export const POST: APIRoute = async ({ request }) => {
  let body: {
    slug?: string;
    haltId?: string;
    decision?: string;
    notes?: string;
  };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }

  const slug = String(body.slug ?? "").trim();
  const haltId = String(body.haltId ?? "").trim();
  const decision = String(body.decision ?? "").trim();
  const notes = typeof body.notes === "string" ? body.notes : "";

  if (!SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  if (!HALT_IDS.has(haltId)) return apiError("Unknown halt");
  if (decision !== "approved" && decision !== "changes")
    return apiError('decision must be "approved" or "changes"');
  if (decision === "changes" && !notes.trim())
    return apiError("Add a note describing the changes you want");
  if (notes.length > 8000)
    return apiError("Note is too long (max 8000 characters)");

  const ref = await findContent(slug);
  if (!ref) return apiError("Book not found", 404);

  const filePath = join(ref.dir, "_system", "halt-reviews.json");
  try {
    let reviews: HaltReviews = {};
    try {
      reviews = JSON.parse(await readFile(filePath, "utf-8")) as HaltReviews;
    } catch {
      /* first decision for this book */
    }
    reviews[haltId] = {
      decision: decision as "approved" | "changes",
      notes: notes.trim(),
      ts: new Date().toISOString(),
    };
    await mkdir(dirname(filePath), { recursive: true });
    await writeFile(filePath, JSON.stringify(reviews, null, 2) + "\n", "utf-8");
    return apiOk({ haltId, decision, saved: reviews[haltId] });
  } catch (e) {
    return apiServerError(String(e));
  }
};
