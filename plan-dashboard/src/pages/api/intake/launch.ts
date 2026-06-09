/**
 * POST /api/intake/launch
 *   { title, settings, staging_token, slug? | work_slug?+volume? }
 *
 * The Tier-2 spend gate (Q10). Runs intake_launch.py PREP (commit staged files →
 * canonical _source/, write series-config.yaml, upsert work.yml, scaffold state) —
 * which spends nothing — then spawns the resolved pipeline driver DETACHED so the
 * run survives the browser closing. The orchestrator is NEVER run in-request.
 *
 * This endpoint launches a real, cost-incurring pipeline run; it must only be
 * called from the cockpit's explicit pre-flight confirm (the user's Tier-2 OK).
 */
import type { APIRoute } from 'astro';
import { runPythonJson, spawnDetachedPython } from '../../../lib/intake-cli';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  let body: {
    title?: string;
    settings?: Record<string, unknown>;
    staging_token?: string;
    slug?: string;
    work_slug?: string;
    volume?: number;
  };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { title, settings, staging_token } = body;
  if (!title || !settings || !staging_token) {
    return apiError('need title, settings, and staging_token');
  }
  if (!body.slug && !body.work_slug) return apiError('need slug or work_slug');

  const prepArgs = [
    '--title', title,
    '--settings', JSON.stringify(settings),
    '--staging-token', staging_token,
  ];
  if (body.slug) prepArgs.push('--slug', body.slug);
  if (body.work_slug) prepArgs.push('--work', body.work_slug);
  if (body.volume != null) prepArgs.push('--volume', String(body.volume));

  try {
    // 1. Prep — no spend. Fails loudly (e.g. missing primary source) before launch.
    const prep = (await runPythonJson('intake_launch.py', prepArgs)) as {
      ok: boolean;
      result?: { slug: string; branch: string; launch: { script: string; args: string[] } };
      error?: string;
    };
    if (!prep.ok || !prep.result) return apiError(prep.error ?? 'launch prep failed');

    // 2. Detached spawn — survives the browser. The orchestrator never runs in-request.
    const { script, args } = prep.result.launch;
    const pid = spawnDetachedPython(script, args);

    return apiOk({
      slug: prep.result.slug,
      branch: prep.result.branch,
      launched: true,
      pid,
    });
  } catch (e) {
    return apiServerError(String(e));
  }
};
