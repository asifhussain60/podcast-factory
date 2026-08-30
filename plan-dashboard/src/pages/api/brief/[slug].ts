/**
 * GET /api/brief/<slug> → a stored commission brief, for the launcher hand-off.
 *
 * Read-only. /studio/new?brief=<slug> uses this to pre-fill its form from a
 * brief that has already been reviewed, so the deciding surface feeds the
 * running surface rather than duplicating it.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  apiOk,
  apiError,
  apiNotFound,
  apiServerError,
} from "../../../lib/api-responses";
import { briefDirFor } from "./generate";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = async ({ params }) => {
  const slug = params.slug ?? "";
  if (!SLUG_RE.test(slug)) return apiError("malformed slug");
  const file = join(briefDirFor(slug), "brief.json");
  if (!existsSync(file)) return apiNotFound(`no brief for ${slug}`);
  try {
    return apiOk(JSON.parse(readFileSync(file, "utf8")));
  } catch (e) {
    return apiServerError(`brief for ${slug} is unreadable: ${String(e)}`);
  }
};
