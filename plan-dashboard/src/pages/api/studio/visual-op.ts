/**
 * visual-op.ts — POST /api/studio/visual-op
 *
 * On-demand artifact ops for the Book Composer's Artifacts tab, spawning
 * scripts/podcast/composer_visual.py:
 *   { action: 'generate', slug, prompt, fromFile?, anchor? } -> Gemini makes/edits
 *      one raster, registers it in book/visuals/index.json, returns { id, file, caption }.
 *   { action: 'delete', slug, id } -> drops the index entry + unlinks the file.
 *
 * Generate is a real Gemini image call (paid, ~$0.04/image) — Tier-authorized for
 * this pipeline. Mirrors generate-book-pdf.ts's spawn-Python pattern.
 */
import type { APIRoute } from 'astro';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { findContentDirSync, getRepoRoot, getPythonBin } from '../../../lib/content-paths';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return apiError('Invalid JSON body'); }

  const slug = String(body.slug ?? '').trim();
  const action = String(body.action ?? '').trim();
  if (!SLUG_RE.test(slug)) return apiError('Invalid slug');
  if (action !== 'generate' && action !== 'delete') return apiError('Unknown action');

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  const args = ['--book-dir', bookDir, '--action', action, '--json'];
  if (action === 'generate') {
    const prompt = String(body.prompt ?? '').trim();
    if (!prompt) return apiError('A description is required to generate an image');
    args.push('--prompt', prompt);
    if (body.fromFile) args.push('--from-file', String(body.fromFile));
    if (body.anchor) args.push('--anchor', String(body.anchor));
  } else {
    const id = String(body.id ?? '').trim();
    if (!id) return apiError('An artifact id is required to delete');
    args.push('--id', id);
  }

  const script = join(getRepoRoot(), 'scripts', 'podcast', 'composer_visual.py');
  try {
    const result = await new Promise<Record<string, unknown>>((resolve, reject) => {
      const proc = spawn(getPythonBin(), [script, ...args], { cwd: getRepoRoot() });
      let stdout = '';
      let stderr = '';
      proc.stdout.on('data', (d) => (stdout += d));
      proc.stderr.on('data', (d) => (stderr += d));
      proc.on('error', reject);
      proc.on('close', (code) => {
        const line = stdout.trim().split('\n').filter((l) => l.trim().startsWith('{')).pop();
        if (line) { try { resolve(JSON.parse(line)); return; } catch { /* fall through */ } }
        reject(new Error(`visual-op exited ${code}: ${stderr.slice(0, 300) || stdout.slice(0, 300)}`));
      });
    });
    if (result.ok === false) return apiServerError(String(result.error ?? 'visual-op failed'));
    return apiOk(result);
  } catch (e) {
    return apiServerError(`Visual op failed: ${String(e)}`);
  }
};
