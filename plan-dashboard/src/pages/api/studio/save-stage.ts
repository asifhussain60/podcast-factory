/**
 * save-stage.ts — POST /api/studio/save-stage
 *
 * Writes the editor's content back to the stage artifact on disk
 * (_stages/<chapter>/<stage>.md). Called by the "Save & Approve" button
 * before the stage approval is recorded in the review JSON.
 *
 * Body: { slug, chapter, stage, content, comments? }
 *   content  — markdown text (from StudioPoc's simple PM serializer)
 *   comments — optional Record<string, string> (paragraph index → comment text)
 *
 * The existing stage file is preserved as <stage>.md.bak before overwrite
 * so the original AI output is always recoverable from disk.
 */
import type { APIRoute } from 'astro';
import { writeFileSync, existsSync, copyFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ALLOWED_STAGES = new Set([
  'source', 'core', 'denoised', 'normalized', 'augmented', 'narrator',
]);
// narrator stage artifact has a different filename.
const STAGE_FILENAMES: Record<string, string> = {
  narrator: 'additions-narrator.md',
};

const REPO_ROOT = join(
  new URL('../../../../../', import.meta.url).pathname,
);

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return apiError('Invalid JSON body'); }

  const slug    = String(body.slug    ?? '').trim();
  const chapter = String(body.chapter ?? '').trim();
  const stage   = String(body.stage   ?? '').trim();
  const content = String(body.content ?? '').trim();
  const comments = (body.comments ?? {}) as Record<string, string>;

  if (!SLUG_RE.test(slug))    return apiError('Invalid slug');
  if (!SLUG_RE.test(chapter)) return apiError('Invalid chapter slug');
  if (!ALLOWED_STAGES.has(stage)) return apiError(`Unknown stage "${stage}"`);
  if (!content) return apiError('Content is empty — nothing to save');

  try {
    const stagesDir = join(
      REPO_ROOT, 'content', 'drafts', 'books', slug, '_stages', chapter,
    );
    if (!existsSync(stagesDir)) {
      return apiError(`Stage directory not found: _stages/${chapter}`, 404);
    }

    const filename = STAGE_FILENAMES[stage] ?? `${stage}.md`;
    const stagePath = join(stagesDir, filename);
    const backupPath = join(stagesDir, filename.replace('.md', '.md.bak'));

    // Backup original before overwrite (idempotent — re-backup only if .bak doesn't exist yet).
    if (existsSync(stagePath) && !existsSync(backupPath)) {
      copyFileSync(stagePath, backupPath);
    }

    // Write the edited content.
    writeFileSync(stagePath, content, 'utf8');

    // Write comments alongside as <stage>-comments.json (non-destructive).
    if (Object.keys(comments).length > 0) {
      const commentsPath = join(stagesDir, `${stage}-comments.json`);
      writeFileSync(
        commentsPath,
        JSON.stringify({ slug, chapter, stage, comments }, null, 2) + '\n',
        'utf8',
      );
    }

    return apiOk({
      slug,
      chapter,
      stage,
      path: `_stages/${chapter}/${filename}`,
      backed_up: existsSync(backupPath),
    });
  } catch (e) {
    return apiServerError(`Failed to write stage file: ${String(e)}`);
  }
};
