/**
 * rename-book.ts — POST /api/studio/rename-book
 *
 * Runs the vetted scripts/podcast/rename_book.py synchronously. That script owns
 * ALL the safety (clean-tree guard, collision + volume refusal, atomic folder +
 * git-branch + meta + state + card-meta + knowledge-DB + ledger updates with
 * rollback). This endpoint is a thin, validated wrapper — it never touches git/fs
 * itself. On success it returns the new reader URL to redirect to.
 *
 * Body: { oldSlug, newSlug }
 */
import type { APIRoute } from 'astro';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { getRepoRoot } from '../../../lib/content-paths';
import { apiOk, apiError } from '../../../lib/api-responses';

const pexec = promisify(execFile);
export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); } catch { return apiError('Invalid JSON body'); }

  const oldSlug = String(body.oldSlug ?? '').trim();
  const newSlug = String(body.newSlug ?? '').trim();
  if (!SLUG_RE.test(oldSlug)) return apiError('Invalid current slug');
  if (!SLUG_RE.test(newSlug)) return apiError('New slug must be lowercase-kebab-case (a-z, 0-9, hyphens)');
  if (oldSlug === newSlug) return apiError('New slug is the same as the current slug');

  try {
    const { stdout } = await pexec(
      'python3',
      ['scripts/podcast/rename_book.py', oldSlug, newSlug],
      { cwd: getRepoRoot(), timeout: 120_000 },
    );
    return apiOk({ oldSlug, newSlug, redirect: `/studio/${newSlug}`, log: stdout.trim() });
  } catch (e: unknown) {
    const err = e as { stderr?: string; message?: string };
    const msg = (err.stderr || err.message || 'Rename failed').toString().trim()
      .replace(/^rename_book:\s*ERROR\s*—\s*/, '');
    return apiError(msg, 400);
  }
};
