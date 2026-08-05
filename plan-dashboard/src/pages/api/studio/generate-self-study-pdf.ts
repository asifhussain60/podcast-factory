/**
 * generate-self-study-pdf.ts — POST /api/studio/generate-self-study-pdf   body { slug }
 *
 * The Preview page's "Self-study PDF" button. Spawns
 * build_book_pdf.py <bookDir> --self-study --json, which first materializes
 * book/book-self-study.md (per-chapter Study summaries + KB-grounded Contextual
 * notes, via claude -p) and then renders book/book-self-study.pdf — a distinct
 * in-repo study artifact that never touches book.md / book.pdf or the Drive
 * publish. Synchronous by design (the user is waiting), but note it runs LLM
 * generation per chapter, so it takes minutes, not seconds. Mirrors
 * generate-book-pdf.ts's spawn-Python pattern.
 */
import type { APIRoute } from "astro";
import { spawn } from "node:child_process";
import { join } from "node:path";
import {
  findContentDirSync,
  getRepoRoot,
  getPythonBin,
} from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  const script = join(getRepoRoot(), "scripts", "podcast", "build_book_pdf.py");
  try {
    const result = await new Promise<Record<string, unknown>>(
      (resolve, reject) => {
        const proc = spawn(
          getPythonBin(),
          [script, bookDir, "--self-study", "--json"],
          { cwd: getRepoRoot() },
        );
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (d) => (stdout += d));
        proc.stderr.on("data", (d) => (stderr += d));
        proc.on("error", reject);
        proc.on("close", (code) => {
          // Parse the last JSON-looking line so any stray output can't break us.
          const line = stdout
            .trim()
            .split("\n")
            .filter((l) => l.trim().startsWith("{"))
            .pop();
          if (line) {
            try {
              resolve(JSON.parse(line));
              return;
            } catch {
              /* fall through */
            }
          }
          reject(
            new Error(
              `render exited ${code}: ${stderr.slice(0, 300) || stdout.slice(0, 300)}`,
            ),
          );
        });
      },
    );
    if (result.ok === false)
      return apiServerError(String(result.error ?? "render failed"));
    return apiOk(result);
  } catch (e) {
    return apiServerError(`Generate failed: ${String(e)}`);
  }
};
