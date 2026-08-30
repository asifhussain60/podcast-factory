/**
 * POST /api/intake/upload  (multipart/form-data)
 *   fields: token? (reuse session), files (one or more), role_<filename>? (optional)
 *
 * Stages mixed-type uploads (Q6). Uses Astro's native formData() — buffered, no
 * new dep (npm install is policy-blocked). Each file is validated (allow-list +
 * size cap), registered in the staging manifest via intake_staging.py (the single
 * source of truth for the staging lifecycle), and its bytes written to the
 * resolver-based staging dir. Nothing touches the canonical _source/ until the
 * final confirm. Returns the session token + file records + role validation.
 */
import type { APIRoute } from "astro";
import { writeFile } from "node:fs/promises";
import { runPythonJson } from "../../../lib/intake-cli";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

// Mirror of intake_staging.ALLOWED_EXT / MAX_FILE_BYTES for a fast client-facing
// reject (the Python register() is the authoritative gate).
const ALLOWED_EXT = new Set([
  ".pdf",
  ".mp3",
  ".m4a",
  ".wav",
  ".txt",
  ".md",
  ".docx",
]);
// Kept in sync with intake_staging.MAX_FILE_BYTES (scripts/podcast/intake_staging.py) —
// raised from 500 MB (2026-08-30) for real sermon-length lecture recordings.
const MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024;

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

export const POST: APIRoute = async ({ request }) => {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return apiError("expected multipart/form-data");
  }

  // Resolve (or create) the staging session token.
  let token = (form.get("token") as string | null)?.trim() || "";
  if (!token) {
    const created = (await runPythonJson("intake_staging.py", ["new"])) as {
      token: string;
    };
    token = created.token;
  }

  const files = form
    .getAll("files")
    .filter((f): f is File => f instanceof File);
  if (files.length === 0) return apiError("no files in upload");

  const staged: unknown[] = [];
  const rejected: { filename: string; reason: string }[] = [];
  try {
    for (const file of files) {
      const name = file.name;
      if (!ALLOWED_EXT.has(ext(name))) {
        rejected.push({ filename: name, reason: "file type not allowed" });
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        rejected.push({ filename: name, reason: "exceeds size cap" });
        continue;
      }
      const role = (form.get(`role_${name}`) as string | null) || undefined;
      const args = ["register", token, name, ...(role ? ["--role", role] : [])];
      const reg = (await runPythonJson("intake_staging.py", args)) as {
        ok: boolean;
        file?: Record<string, unknown>;
        stored_path?: string;
        error?: string;
      };
      if (!reg.ok || !reg.stored_path) {
        rejected.push({
          filename: name,
          reason: reg.error ?? "register failed",
        });
        continue;
      }
      await writeFile(reg.stored_path, Buffer.from(await file.arrayBuffer()));
      staged.push(reg.file);
    }

    const validation = await runPythonJson("intake_staging.py", [
      "validate",
      token,
    ]);
    return apiOk({ token, staged, rejected, validation });
  } catch (e) {
    return apiServerError(String(e));
  }
};
