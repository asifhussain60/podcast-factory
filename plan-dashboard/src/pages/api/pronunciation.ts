/**
 * GET  /api/pronunciation?slug=X   — probe terms for a book, live library overlaid
 * POST /api/pronunciation          — apply corrections {slug, corrections:[...]}
 *
 * Writes go through the Python applier (apply_pronunciation_corrections.py) so all
 * pronunciation-library logic stays in ONE place (the pipeline owns the library;
 * this endpoint is a thin bridge). Mirrors the api/annotations.ts pattern.
 */
import type { APIRoute } from "astro";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { getProbe } from "../../lib/pronunciation";
import {
  getRepoRoot,
  getPythonBin,
  findContent,
} from "../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../lib/api-responses";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug");
  if (!slug) return apiError("Missing slug param");
  try {
    const detail = await getProbe(slug);
    if (!detail) return apiError("No probe found for that book", 404);
    return apiOk(detail);
  } catch (e) {
    return apiServerError(String(e));
  }
};

interface Correction {
  term: string;
  transliteration?: string;
  status: "ok" | "respell" | "unfixable" | "skip";
  phonetic?: string;
  gloss?: string;
  mangled_variants?: string[];
}

function runApplier(bookDir: string, payload: object): Promise<any> {
  const script = join(
    getRepoRoot(),
    "scripts",
    "podcast",
    "apply_pronunciation_corrections.py",
  );
  return new Promise((resolve, reject) => {
    const proc = spawn(getPythonBin(), [script, bookDir, "-"], {
      cwd: getRepoRoot(),
    });
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));
    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`applier exited ${code}: ${stderr || stdout}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        reject(new Error(`applier output not JSON: ${stdout}\n${String(e)}`));
      }
    });
    proc.stdin.write(JSON.stringify(payload));
    proc.stdin.end();
  });
}

export const POST: APIRoute = async ({ request }) => {
  let body: {
    slug: string;
    corrections: Correction[];
    confirmed_date?: string;
  };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { slug, corrections } = body;
  if (!slug || !Array.isArray(corrections)) {
    return apiError("Missing slug or corrections[]");
  }

  const ref = await findContent(slug);
  if (!ref) return apiError("content not found", 404);

  const payload = {
    book_slug: slug,
    confirmed_date: body.confirmed_date,
    corrections,
  };

  try {
    const result = await runApplier(ref.dir, payload);
    return apiOk(result);
  } catch (e) {
    return apiServerError(String(e));
  }
};
