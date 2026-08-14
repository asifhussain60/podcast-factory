/**
 * quote-kind.ts — the Book Composer's card-type control endpoint.
 *
 *   POST /api/studio/quote-kind
 *        body { slug, chapterKey, firstLine, kind, by? }
 *        kind is one of "hadith" | "poem" | "quote" | "" ("" clears the
 *        declaration, falling the block back to the default Saying card).
 *        Writes `_system/quote-kind.json` via quote-groups.mjs's sibling
 *        writer, writeQuoteKind in scripts/lib/quote-kind.mjs.
 *
 * Deliberately NOT an AI route — this is the deterministic write a person's
 * own menu pick becomes. Nothing here infers a kind from text; see that
 * module's own header for why that is a locked rule, not an oversight. A
 * separate route (quote-kind-suggest.ts) lets Gemini propose a kind, but
 * only this route ever writes one, and only when called with a kind a human
 * selected.
 */
import type { APIRoute } from "astro";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import {
  writeQuoteKind,
  QUOTE_KIND_IDS,
} from "../../../../scripts/lib/quote-kind.mjs";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
/** "" is accepted too — it clears a declaration back to the default card. */
const VALID_KINDS = new Set([...QUOTE_KIND_IDS, ""]);

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const chapterKey = String(body.chapterKey ?? "").trim();
  if (!chapterKey) return apiError("chapterKey is required");
  const firstLine = String(body.firstLine ?? "").trim();
  if (!firstLine) return apiError("firstLine is required");
  const kind = String(body.kind ?? "");
  if (!VALID_KINDS.has(kind))
    return apiError(
      `Invalid kind (expected one of: ${[...QUOTE_KIND_IDS].join(", ")}, or "" to clear)`,
    );
  const by = body.by === undefined ? undefined : String(body.by ?? "").trim();

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  try {
    writeQuoteKind(bookDir, chapterKey, firstLine, kind, by);
    return apiOk({ slug, chapterKey, firstLine, kind: kind || null });
  } catch (e) {
    return apiServerError((e as Error).message);
  }
};
