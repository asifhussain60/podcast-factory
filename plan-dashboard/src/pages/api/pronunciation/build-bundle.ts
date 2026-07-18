/**
 * POST /api/pronunciation/build-bundle
 *
 * Regenerates the NotebookLM probe bundle (00-framing.md, pronunciation-probe.md,
 * listen-checklist.md) by shelling to build_probe_bundle.py, then reads and
 * returns both file contents so the UI can display them for preview + copy.
 *
 * Body: { slug: string; format?: string; length?: string }
 */
import type { APIRoute } from "astro";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import {
  getRepoRoot,
  getPythonBin,
  findContent,
} from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

function runBundleBuilder(bookDir: string): Promise<string> {
  const script = join(
    getRepoRoot(),
    "scripts",
    "podcast",
    "probe",
    "build_probe_bundle.py",
  );
  return new Promise((resolve, reject) => {
    const proc = spawn(getPythonBin(), [script, bookDir], {
      cwd: getRepoRoot(),
    });
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));
    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) {
        reject(
          new Error(`build_probe_bundle exited ${code}: ${stderr || stdout}`),
        );
        return;
      }
      resolve(stdout.trim());
    });
  });
}

export const POST: APIRoute = async ({ request }) => {
  let body: { slug?: string; format?: string; length?: string };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { slug } = body;
  if (!slug) return apiError("Missing slug");

  const ref = await findContent(slug);
  if (!ref) return apiError("content not found", 404);

  try {
    await runBundleBuilder(ref.dir);

    const bundleDir = join(
      ref.dir,
      "_system",
      "probe",
      "EP00-pronunciation-probe",
    );
    const [source, framing] = await Promise.all([
      readFile(join(bundleDir, "pronunciation-probe.md"), "utf-8"),
      readFile(join(bundleDir, "00-framing.md"), "utf-8"),
    ]);

    return apiOk({ source, framing });
  } catch (e) {
    return apiServerError(String(e));
  }
};
