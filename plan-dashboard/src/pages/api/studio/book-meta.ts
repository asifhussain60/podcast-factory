/**
 * book-meta.ts — POST /api/studio/book-meta
 *
 * Patches a single top-level field in a book's meta.yml. Wave L-7 uses it to set
 * `content_level` (history | shariah | esoteric | realities, or "" to clear) from
 * the Studio intake content-level selector.
 *
 * Body: { slug, field, value }
 *   field — currently only "content_level" is allowed (allowlist below).
 *   value — one of the allowed content levels, or "" to remove the field.
 *
 * Line-level patch (not parse-and-redump) so existing comments and formatting in
 * meta.yml are preserved. Resolves the book dir via findContent (drafts only).
 */
import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { findContent } from '../../../lib/content-paths';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

// Allowlisted single-field patches. content_level drives Wave L augmentation gating.
const FIELD_ALLOWED_VALUES: Record<string, Set<string>> = {
  content_level: new Set(['history', 'shariah', 'esoteric', 'realities', '']),
};

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return apiError('Invalid JSON body'); }

  const slug = String(body.slug ?? '').trim();
  const field = String(body.field ?? '').trim();
  const value = String(body.value ?? '').trim();

  if (!SLUG_RE.test(slug)) return apiError('Invalid slug');
  if (!(field in FIELD_ALLOWED_VALUES)) return apiError(`Field "${field}" is not patchable`);
  if (!FIELD_ALLOWED_VALUES[field].has(value)) {
    return apiError(`Invalid value "${value}" for ${field}`);
  }

  const ref = await findContent(slug);
  if (!ref) return apiError(`Content "${slug}" not found`, 404);

  const metaPath = join(ref.dir, 'meta.yml');
  if (!existsSync(metaPath)) return apiError('meta.yml not found for this book', 404);

  try {
    const original = readFileSync(metaPath, 'utf8');
    const lines = original.split('\n');
    // A top-level field line: no leading whitespace, `field:` prefix.
    const fieldLineRe = new RegExp(`^${field}:\\s*.*$`);
    const idx = lines.findIndex((ln) => fieldLineRe.test(ln));

    if (value === '') {
      // Clear: remove the field line entirely (if present).
      if (idx !== -1) lines.splice(idx, 1);
    } else if (idx !== -1) {
      lines[idx] = `${field}: ${value}`;
    } else {
      // Append after the first top-level scalar block, or at end. Keep it simple:
      // insert before the first blank line that follows a top-level key, else push.
      const insertAt = lines.findIndex((ln) => ln.trim() === '');
      const newLine = `${field}: ${value}`;
      if (insertAt === -1) lines.push(newLine);
      else lines.splice(insertAt, 0, newLine);
    }

    const patched = lines.join('\n');
    writeFileSync(metaPath, patched, 'utf8');
    return apiOk({ slug, field, value: value || null });
  } catch (e) {
    return apiServerError(`Failed to patch meta.yml: ${String(e)}`);
  }
};
