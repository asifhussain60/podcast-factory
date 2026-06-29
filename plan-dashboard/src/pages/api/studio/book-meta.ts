/**
 * book-meta.ts — POST /api/studio/book-meta
 *
 * Patches a single top-level field in a book's meta.yml. Wave M uses it to set
 * `content_level` (general | advanced | taveel | mamsool | mabda_maad | haqaiq, or "" to clear)
 * from the Studio intake content-level selector.
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

// Allowlisted single-field patches. Each field is either an `enum` (fixed value
// set) or `text` (single-line free text with a length cap). SLUG and structural
// identity fields are deliberately ABSENT — renaming is a separate guarded flow,
// never a casual field patch (it moves the folder + git branch + many refs).
type FieldRule =
  | { kind: 'enum'; values: Set<string> }
  | { kind: 'text'; maxLen: number; allowEmpty?: boolean };

const FIELD_RULES: Record<string, FieldRule> = {
  // content_level drives Wave M augmentation gating (existing).
  content_level:  { kind: 'enum', values: new Set(['general', 'advanced', 'taveel', 'mamsool', 'mabda_maad', 'haqaiq', '']) },
  // category is a soft tag (folder/bucket comes from content_profile, NOT category),
  // so it is safe to patch from the site.
  category:       { kind: 'enum', values: new Set(['books', 'lectures', 'articles', 'documents', 'interviews', 'letters', 'asbaaq']) },
  // Safe display fields.
  title:          { kind: 'text', maxLen: 200 },
  short_name:     { kind: 'text', maxLen: 60 },
  author:         { kind: 'text', maxLen: 120, allowEmpty: true },
  original_title: { kind: 'text', maxLen: 200, allowEmpty: true },
};

// Quote a scalar when it contains YAML-significant characters, so a value like
// "Asas al-Taweel -- Volume 1: Adam" (colon) can never corrupt the file.
function yamlScalar(v: string): string {
  if (v === '') return '';
  if (/[:#&*!|>'"%@`{}[\],]/.test(v) || /^\s|\s$/.test(v)) {
    return `"${v.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
  }
  return v;
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return apiError('Invalid JSON body'); }

  const slug = String(body.slug ?? '').trim();
  const field = String(body.field ?? '').trim();
  const value = String(body.value ?? '').trim();

  if (!SLUG_RE.test(slug)) return apiError('Invalid slug');
  const rule = FIELD_RULES[field];
  if (!rule) return apiError(`Field "${field}" is not patchable`);
  if (rule.kind === 'enum') {
    if (!rule.values.has(value)) return apiError(`Invalid value "${value}" for ${field}`);
  } else {
    if (!value && !rule.allowEmpty) return apiError(`${field.replace(/_/g, ' ')} cannot be empty`);
    if (value.length > rule.maxLen) return apiError(`${field.replace(/_/g, ' ')} is too long (max ${rule.maxLen})`);
    if (/[\r\n]/.test(value)) return apiError(`${field.replace(/_/g, ' ')} must be a single line`);
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
      lines[idx] = `${field}: ${yamlScalar(value)}`;
    } else {
      // Append after the first top-level scalar block, or at end. Keep it simple:
      // insert before the first blank line that follows a top-level key, else push.
      const insertAt = lines.findIndex((ln) => ln.trim() === '');
      const newLine = `${field}: ${yamlScalar(value)}`;
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
