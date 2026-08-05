/**
 * GET /api/intake/preflight?slug=<slug>&chapters=<n>&perChapterCap=<usd>&bookCap=<usd>
 *
 * Returns a pre-flight cost/time estimate (chapter_count × historical mean,
 * capped per-chapter) + the caps in effect, for the intake cockpit's pre-launch
 * summary. Thin pass-through to scripts/podcast/intake_preflight.py. Read-only —
 * authorises NOTHING; the launch confirm is the Tier-2 spend gate.
 */
import type { APIRoute } from "astro";
import { runPythonJson } from "../../../lib/intake-cli";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug");
  const chapters = url.searchParams.get("chapters");
  if (!slug && !chapters) return apiError("need slug or chapters");

  const args: string[] = [];
  if (chapters) args.push("--chapters", chapters);
  else if (slug) args.push("--slug", slug);
  const perCap = url.searchParams.get("perChapterCap");
  const bookCap = url.searchParams.get("bookCap");
  if (perCap) args.push("--per-chapter-cap", perCap);
  if (bookCap) args.push("--book-cap", bookCap);

  try {
    const out = (await runPythonJson("intake_preflight.py", args)) as {
      ok: boolean;
      estimate?: unknown;
      error?: string;
    };
    if (!out.ok) return apiError(out.error ?? "estimate failed");
    return apiOk({ estimate: out.estimate });
  } catch (e) {
    return apiServerError(String(e));
  }
};
