/**
 * Morphology API — read-only detail lookups for the /corpus/morphology explorer.
 *
 *   GET /api/corpus/morphology?root=rHm     — one root's full record (family, POS, Lane)
 *   GET /api/corpus/morphology?verse=2:255  — one verse's Arabic + English (mushaf mirror)
 *
 * Everything comes from the committed local DBs (morphology.db, mirror.db,
 * lexicon.jsonl) — no model, no network. The list/search side needs no API at
 * all: the page ships the root inventory and searches client-side in the
 * shared fold space.
 */
import type { APIRoute } from "astro";

import { rootDetail, verseText } from "../../../lib/db/morphology.server";
import { apiError, apiOk } from "../../../lib/api-responses";

export const prerender = false;

const ROOT_RE = /^[A-Za-z'|>&<}{*$~`_-]{1,8}$/;
const VERSE_RE = /^(\d{1,3}):(\d{1,3})$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const root = url.searchParams.get("root");
  const verse = url.searchParams.get("verse");
  if (root) {
    if (!ROOT_RE.test(root)) return apiError("invalid root");
    const record = rootDetail(root);
    return record ? apiOk(record) : apiError("unknown root", 404);
  }
  if (verse) {
    const m = VERSE_RE.exec(verse);
    if (!m) return apiError("invalid verse ref");
    const record = verseText(Number(m[1]), Number(m[2]));
    return record
      ? apiOk({ ref: verse, ...record })
      : apiError("unknown verse", 404);
  }
  return apiError("missing root or verse parameter");
};
