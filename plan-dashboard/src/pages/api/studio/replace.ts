/**
 * POST /api/studio/replace
 *
 * Find-and-replace across a book's canonical chapter text files
 * (content/<Bucket>/<slug>/chapters/<id>.txt — the same source the Studio
 * editor reads and the reader renders).
 *
 * Body: {
 *   slug:    string,
 *   scope:   'chapter' | 'book',
 *   chapter?: string,                 // required when scope === 'chapter'
 *   pairs:   { find: string; replace: string }[],
 *   apply?:  boolean                  // false (default) = preview/count only, no writes
 * }
 * Returns: { ok, applied, total, results: { chapter, count }[] }
 *
 * Matching is literal and case-sensitive. Pairs are applied IN ORDER (a later
 * pair sees the result of an earlier one), matching ordinary find-and-replace.
 * On apply each changed file is copied to <id>.txt.bak (one-step local undo)
 * before overwrite; the files are git-tracked, so git is the deeper safety net.
 */

import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync, copyFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { findContentDirSync } from '../../../lib/content-paths';

export const prerender = false;

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

interface Pair { find: string; replace: string }

/** Count non-overlapping literal occurrences of `needle` in `hay`. */
function countOccurrences(hay: string, needle: string): number {
  if (!needle) return 0;
  let n = 0;
  let i = hay.indexOf(needle);
  while (i !== -1) {
    n += 1;
    i = hay.indexOf(needle, i + needle.length);
  }
  return n;
}

/** Apply every pair in order; return the rewritten text and the total match count. */
function applyPairs(text: string, pairs: Pair[]): { text: string; count: number } {
  let out = text;
  let count = 0;
  for (const p of pairs) {
    if (!p.find) continue;
    count += countOccurrences(out, p.find);
    out = out.split(p.find).join(p.replace);
  }
  return { text: out, count };
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try { body = await request.json(); }
  catch { return json({ ok: false, error: 'Invalid JSON' }, 400); }

  const slug = String(body.slug ?? '').trim();
  const scope = String(body.scope ?? '').trim();
  const chapter = String(body.chapter ?? '').trim();
  const apply = body.apply === true;
  const pairsRaw = Array.isArray(body.pairs) ? body.pairs : [];

  if (!SLUG_RE.test(slug)) return json({ ok: false, error: 'Invalid slug' }, 400);
  if (scope !== 'chapter' && scope !== 'book') return json({ ok: false, error: 'scope must be chapter|book' }, 400);

  const pairs: Pair[] = pairsRaw
    .filter((p): p is { find: unknown; replace?: unknown } => !!p && typeof (p as { find?: unknown }).find === 'string')
    .map((p) => ({ find: String(p.find), replace: typeof p.replace === 'string' ? p.replace : '' }))
    .filter((p) => p.find.trim() !== '');
  if (pairs.length === 0) return json({ ok: false, error: 'at least one non-empty find term required' }, 400);

  const dir = findContentDirSync(slug);
  if (!dir) return json({ ok: false, error: `book not found: ${slug}` }, 404);
  const chaptersDir = join(dir, 'chapters');
  if (!existsSync(chaptersDir)) return json({ ok: false, error: 'no chapters/ directory for this book' }, 404);

  // Resolve the target file(s).
  let files: string[];
  if (scope === 'chapter') {
    if (!SLUG_RE.test(chapter)) return json({ ok: false, error: 'Invalid chapter slug' }, 400);
    const f = join(chaptersDir, `${chapter}.txt`);
    if (!existsSync(f)) return json({ ok: false, error: `chapter file not found: ${chapter}.txt` }, 404);
    files = [f];
  } else {
    files = readdirSync(chaptersDir)
      .filter((n) => n.endsWith('.txt') && !n.endsWith('.bak'))
      .sort()
      .map((n) => join(chaptersDir, n));
  }

  try {
    const results: { chapter: string; count: number }[] = [];
    let total = 0;
    for (const f of files) {
      const id = f.slice(f.lastIndexOf('/') + 1).replace(/\.txt$/, '');
      const text = readFileSync(f, 'utf8');
      const { text: next, count } = applyPairs(text, pairs);
      if (count > 0) {
        results.push({ chapter: id, count });
        total += count;
        if (apply && next !== text) {
          copyFileSync(f, `${f}.bak`); // one-step local undo (gitignored)
          writeFileSync(f, next, 'utf8');
        }
      }
    }
    return json({ ok: true, applied: apply, total, results });
  } catch (e) {
    return json({ ok: false, error: String(e) }, 500);
  }
};
