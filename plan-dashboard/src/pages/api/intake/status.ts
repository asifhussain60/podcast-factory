/**
 * GET /api/intake/status?slug=<slug>
 *
 * Read-only cockpit status for a running volume/book (Phase 6, Q10): phase,
 * cost-vs-cap, per-chapter progress, and the human-review gate (if halted at one).
 * Thin pass-through to intake_status.py. The UI is read-only while a volume runs
 * (single-writer rule) — this endpoint never mutates state.
 */
import type { APIRoute } from "astro";
import { runPythonJson } from "../../../lib/intake-cli";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug");
  if (!slug) return apiError("missing slug");
  try {
    const out = (await runPythonJson("intake_status.py", [slug])) as {
      ok: boolean;
      status?: unknown;
    };
    if (!out.ok) return apiError("content not found", 404);
    return apiOk({ status: out.status });
  } catch (e) {
    return apiServerError(String(e));
  }
};
