/**
 * book-md.ts — PUT /api/studio/book-md   body { slug, chapterKey, markdown }
 *
 * The Book Composer's chapter editor writes here. It replaces ONE chapter's body
 * in book/book.md — the composed reading edition the Composer previews — leaving
 * the `## Heading` line and every other chapter untouched. `chapterKey` is the
 * normalized heading key (mirrors lib/reader/composer.ts anchorKey); `markdown`
 * is the chapter body only (no heading), from the TipTap serializer.
 *
 * book.md is the last-mile reading edition (composed by a rare, manual, cached
 * LLM pass); a hand-edit here is durable in normal use. The prior file is kept as
 * book.md.bak (once) so the original is always recoverable.
 */
import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'node:fs';
import { join } from 'node:path';
import { findContentDirSync } from '../../../lib/content-paths';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Normalize a heading to a comparable key — mirror of composer.ts anchorKey. */
function anchorKey(s: string): string {
  return s.replace(/<[^>]+>/g, '').replace(/^#{1,6}\s+/, '')
    .replace(/^\d+\.\s*/, '').trim().toLowerCase();
}

export const PUT: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return apiError('Invalid JSON body'); }

  const slug = String(body.slug ?? '').trim();
  const chapterKey = String(body.chapterKey ?? '').trim().toLowerCase();
  const markdown = String(body.markdown ?? '').trim();

  if (!SLUG_RE.test(slug)) return apiError('Invalid slug');
  if (!chapterKey) return apiError('Missing chapterKey');
  if (!markdown) return apiError('Content is empty — nothing to save');

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  const bookMd = join(bookDir, 'book', 'book.md');
  if (!existsSync(bookMd)) return apiError('book.md not found', 404);

  try {
    const lines = readFileSync(bookMd, 'utf-8').split('\n');
    // Locate the target chapter's heading and the start of the next chapter.
    let start = -1;
    let end = lines.length;
    for (let i = 0; i < lines.length; i += 1) {
      if (!/^##\s+/.test(lines[i])) continue;
      if (start === -1 && anchorKey(lines[i]) === chapterKey) start = i;
      else if (start !== -1) { end = i; break; }
    }
    if (start === -1) return apiError(`Chapter not found: ${chapterKey}`, 404);

    if (!existsSync(`${bookMd}.bak`)) copyFileSync(bookMd, `${bookMd}.bak`);

    const head = lines.slice(0, start + 1); // through the heading line
    const tail = lines.slice(end);          // from the next heading (or EOF)
    const rebuilt = [...head, '', markdown, '', ...tail].join('\n').replace(/\n{3,}/g, '\n\n');
    writeFileSync(bookMd, rebuilt.endsWith('\n') ? rebuilt : `${rebuilt}\n`);

    return apiOk({ slug, chapterKey, path: bookMd });
  } catch (e) {
    return apiServerError(`Save failed: ${String(e)}`);
  }
};
