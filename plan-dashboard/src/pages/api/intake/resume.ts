/**
 * POST /api/intake/resume  { slug, action: 'resume' | 'advance', work_slug? }
 *
 * Approval-card action (Q10): the operator approves a human-review gate
 * ('resume' → orchestrate_book --resume <slug>) or the between-volumes pause
 * ('advance' → orchestrate_work <work_slug> --advance). Spawns DETACHED under the
 * single-actor supervisor discipline; never runs the orchestrator in-request.
 *
 * Like /launch, this resumes a real cost-incurring run — call only from an
 * explicit approval click in the cockpit.
 */
import type { APIRoute } from 'astro';
import { spawnDetachedPython } from '../../../lib/intake-cli';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  let body: { slug?: string; action?: string; work_slug?: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { slug, action } = body;
  if (!slug) return apiError('missing slug');

  try {
    let pid: number;
    if (action === 'advance') {
      const work = body.work_slug || slug;
      pid = spawnDetachedPython('orchestrate_work.py', [work, '--advance']);
    } else if (action === 'resume') {
      pid = spawnDetachedPython('orchestrate_book.py', ['--resume', slug]);
    } else {
      return apiError("action must be 'resume' or 'advance'");
    }
    return apiOk({ slug, action, pid, launched: true });
  } catch (e) {
    return apiServerError(String(e));
  }
};
