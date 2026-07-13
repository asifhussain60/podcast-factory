/**
 * visual-asset.ts — GET /api/studio/visual-asset?slug=&file=
 *
 * Serves a candidate visual (book/visuals/<file>) to the Book Composer preview.
 * The assets live under content/ (not public/), so they need a server route.
 * Read-only; strict slug + filename validation guards against traversal.
 */
import type { APIRoute } from 'astro';
import { existsSync, readFileSync } from 'node:fs';
import { join, extname, basename } from 'node:path';
import { findContentDirSync } from '../../../lib/content-paths';
import { apiError, apiNotFound } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const FILE_RE = /^[A-Za-z0-9._-]+\.(svg|png|jpe?g|webp)$/;
const MIME: Record<string, string> = {
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp',
};

export const GET: APIRoute = ({ url }) => {
  const slug = String(url.searchParams.get('slug') ?? '').trim();
  const file = String(url.searchParams.get('file') ?? '').trim();
  if (!SLUG_RE.test(slug)) return apiError('Invalid slug');
  if (!FILE_RE.test(file) || basename(file) !== file) return apiError('Invalid file');

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiNotFound(`Book not found: ${slug}`);
  const target = join(bookDir, 'book', 'visuals', file);
  if (!target.startsWith(join(bookDir, 'book', 'visuals') + '/') || !existsSync(target)) {
    return apiNotFound('asset not found');
  }
  const type = MIME[extname(target).toLowerCase()];
  if (!type) return apiError('Unsupported asset type');
  return new Response(readFileSync(target), { status: 200, headers: { 'content-type': type } });
};
