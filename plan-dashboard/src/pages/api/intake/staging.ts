/**
 * GET  /api/intake/staging?token=<t>           → { files, validation }
 * POST /api/intake/staging { token, action, file_id, role? }
 *        action='set-role' → change a staged file's role
 *        action='remove'   → drop a staged file
 *
 * Staging-session operations for Screen 1 (role edits + removal). Thin
 * pass-through to intake_staging.py. Read/edit only — the canonical _source/ is
 * untouched until the final confirm.
 */
import type { APIRoute } from 'astro';
import { runPythonJson } from '../../../lib/intake-cli';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const token = url.searchParams.get('token');
  if (!token) return apiError('missing token');
  try {
    const list = (await runPythonJson('intake_staging.py', ['list', token])) as {
      files?: unknown[];
    };
    const validation = await runPythonJson('intake_staging.py', ['validate', token]);
    return apiOk({ files: list.files ?? [], validation });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { token?: string; action?: string; file_id?: string; role?: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { token, action, file_id } = body;
  if (!token || !file_id) return apiError('missing token or file_id');

  let args: string[];
  if (action === 'set-role') {
    if (!body.role) return apiError('set-role requires role');
    args = ['set-role', token, file_id, body.role];
  } else if (action === 'remove') {
    args = ['remove', token, file_id];
  } else {
    return apiError("action must be 'set-role' or 'remove'");
  }

  try {
    const out = (await runPythonJson('intake_staging.py', args)) as { ok: boolean; error?: string };
    if (!out.ok) return apiError(out.error ?? 'staging op failed');
    const validation = await runPythonJson('intake_staging.py', ['validate', token]);
    return apiOk({ result: out, validation });
  } catch (e) {
    return apiServerError(String(e));
  }
};
