/**
 * GET  /api/intake/form-options                  → merged dropdown option-sets
 * POST /api/intake/form-options { action, field, value | old, new }
 *        action='add'    → add a value to a field's dropdown
 *        action='rename' → rename a value in a field's dropdown
 *
 * Thin pass-through to scripts/podcast/intake_form_options.py (the single source
 * of truth — defaults from the content-type registry + blueprint enums, user
 * deltas persisted to content/_system/intake/form-options.yml). The UI reads
 * these so its dropdowns can never offer a value the pipeline rejects.
 */
import type { APIRoute } from 'astro';
import { runPythonJson } from '../../../lib/intake-cli';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

export const GET: APIRoute = async () => {
  try {
    const out = (await runPythonJson('intake_form_options.py', ['get'])) as {
      ok: boolean;
      options?: Record<string, string[]>;
      error?: string;
    };
    if (!out.ok) return apiError(out.error ?? 'failed to read options');
    return apiOk({ options: out.options });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { action?: string; field?: string; value?: string; old?: string; new?: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { action, field } = body;
  if (!field) return apiError('Missing field');

  let args: string[];
  if (action === 'add') {
    if (!body.value) return apiError('add requires value');
    args = ['add', field, body.value];
  } else if (action === 'rename') {
    if (!body.old || !body.new) return apiError('rename requires old and new');
    args = ['rename', field, body.old, body.new];
  } else {
    return apiError("action must be 'add' or 'rename'");
  }

  try {
    const out = (await runPythonJson('intake_form_options.py', args)) as {
      ok: boolean;
      options?: Record<string, string[]>;
      error?: string;
    };
    if (!out.ok) return apiError(out.error ?? 'update failed');
    return apiOk({ options: out.options });
  } catch (e) {
    return apiServerError(String(e));
  }
};
