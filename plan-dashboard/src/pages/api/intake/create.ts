/**
 * intake/create.ts — POST /api/intake/create
 *
 * Scaffolds the workshop folder for a new piece of content. Writes:
 *   content/drafts/<category>/<slug>/_system/meta.json
 *   content/drafts/<category>/<slug>/_system/editorial/book.json
 *
 * MUST NOT launch the pipeline. It only creates the folder structure so the
 * editorial cockpit can load and the user can set canonical decisions before
 * asking Claude to kick off intake.
 *
 * Body: { slug, category, title, sourceHint? }
 * Returns: { slug, category, path }
 */
import type { APIRoute } from 'astro';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const ALLOWED_CATEGORIES = new Set([
  'books', 'articles', 'documents', 'lectures', 'interviews', 'letters', 'asbaaq',
]);

const REPO_ROOT = join(
  new URL('../../../../../', import.meta.url).pathname,
);

function draftsPath(category: string, slug: string): string {
  return join(REPO_ROOT, 'content', 'drafts', category, slug);
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON body');
  }

  const slug = String(body.slug ?? '').trim().toLowerCase();
  const category = String(body.category ?? '').trim().toLowerCase();
  const title = String(body.title ?? '').trim();
  const sourceHint = String(body.sourceHint ?? '').trim();

  if (!slug || !SLUG_RE.test(slug)) {
    return apiError(
      'Invalid slug — must be lowercase letters, digits, and hyphens only (e.g. my-book-title)',
    );
  }
  if (!ALLOWED_CATEGORIES.has(category)) {
    return apiError(`Unknown category "${category}". Allowed: ${[...ALLOWED_CATEGORIES].join(', ')}`);
  }
  if (!title) {
    return apiError('Title is required');
  }

  const bookDir = draftsPath(category, slug);

  if (existsSync(join(bookDir, '_system', 'meta.json'))) {
    return apiError(`Content "${slug}" already exists at ${bookDir}`, 409);
  }

  try {
    const systemDir = join(bookDir, '_system');
    const editorialDir = join(systemDir, 'editorial');
    mkdirSync(editorialDir, { recursive: true });

    const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');

    // meta.json — intake record; read by the pipeline.
    writeFileSync(
      join(systemDir, 'meta.json'),
      JSON.stringify(
        { slug, category, title, source_hint: sourceHint || null, created_at: now },
        null,
        2,
      ) + '\n',
      'utf8',
    );

    // editorial/book.json — empty canonical editorial decisions for the cockpit.
    writeFileSync(
      join(editorialDir, 'book.json'),
      JSON.stringify({ slug, scope: 'book', cards: {}, updated_at: null }, null, 2) + '\n',
      'utf8',
    );

    return apiOk({
      slug,
      category,
      title,
      path: bookDir.replace(REPO_ROOT, ''),
    }, 201);
  } catch (e) {
    return apiServerError(`Failed to scaffold content folder: ${String(e)}`);
  }
};
