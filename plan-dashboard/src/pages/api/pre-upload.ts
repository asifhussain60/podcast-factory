/**
 * POST /api/pre-upload — save checklist corrections or apply an ambiguity fix.
 *
 * Actions:
 *   { action: 'save-checklist', slug, terms: ChecklistTerm[] }
 *   { action: 'apply-fix', slug, item_id, episode_id, section, fix_text }
 *   { action: 'mark-fix-status', slug, item_id, status }
 */

import type { APIRoute } from 'astro';
import { join } from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { findContent } from '../../lib/content-paths';
import { apiOk, apiError, apiServerError } from '../../lib/api-responses';

export const prerender = false;

// ─── save-checklist ────────────────────────────────────────────────────────

async function saveChecklist(slug: string, terms: Array<{ n: number; term: string; rendered: string; ok: string; fix: string }>): Promise<Response> {
  const ref = await findContent(slug);
  if (!ref) return apiError('Book not found', 404);
  const bookDir = ref.dir;

  const checklistPath = join(bookDir, '_system', 'probe', 'EP00-pronunciation-probe', 'listen-checklist.md');
  if (!existsSync(checklistPath)) return apiError('listen-checklist.md not found', 404);

  const raw = await readFile(checklistPath, 'utf-8');
  const lines = raw.split('\n');

  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    const t = (lines[i] ?? '').trim();
    if (t.startsWith('|') && t.includes('term') && t.includes('rendered')) {
      headerIdx = i;
      break;
    }
  }
  if (headerIdx === -1) return apiError('Could not locate checklist table header');

  const byN = new Map(terms.map(t => [t.n, t]));
  const preamble = lines.slice(0, headerIdx);
  const header = lines[headerIdx]!;
  const sep = lines[headerIdx + 1] ?? '|---|------|----------|-----|-----|';
  const dataLines: string[] = [];

  for (let i = headerIdx + 2; i < lines.length; i++) {
    const line = lines[i] ?? '';
    const trimmed = line.trim();
    if (!trimmed.startsWith('|')) {
      dataLines.push(...lines.slice(i));
      break;
    }
    const cells = trimmed.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
    const n = parseInt(cells[0] ?? '0', 10);
    const upd = byN.get(n);
    if (upd) {
      dataLines.push(`| ${upd.n} | ${upd.term} | ${upd.rendered} | ${upd.ok} | ${upd.fix} |`);
    } else {
      dataLines.push(line);
    }
  }

  const newContent = [...preamble, header, sep, ...dataLines].join('\n');
  await writeFile(checklistPath, newContent, 'utf-8');
  return apiOk({ saved: terms.length });
}

// ─── apply-fix ─────────────────────────────────────────────────────────────

async function applyFix(slug: string, itemId: string, episodeId: string, section: string, fixText: string): Promise<Response> {
  const ref = await findContent(slug);
  if (!ref) return apiError('Book not found', 404);
  const bookDir = ref.dir;

  const { readdirSync } = await import('node:fs');
  const draftsDir = join(bookDir, '_system', 'episode-drafts');
  if (!existsSync(draftsDir)) return apiError('episode-drafts dir missing', 404);

  const entries = readdirSync(draftsDir);
  const match = entries.find((e: string) => e.startsWith(episodeId + '-') || e === episodeId);
  if (!match) return apiError(`No episode-drafts folder for ${episodeId}`, 404);

  const framingPath = join(draftsDir, match, '00-framing.md');
  if (!existsSync(framingPath)) return apiError('00-framing.md not found', 404);

  const raw = await readFile(framingPath, 'utf-8');
  const updated = appendToSection(raw, section, fixText);
  await writeFile(framingPath, updated, 'utf-8');

  await updateItemStatus(bookDir, itemId, 'applied');
  return apiOk({ applied: true, episode: episodeId, section });
}

function appendToSection(md: string, sectionName: string, text: string): string {
  const lower = sectionName.toLowerCase().trim();
  const lines = md.split('\n');
  let insertAt = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? '';
    if (line.startsWith('## ') || line.startsWith('# ')) {
      const head = line.replace(/^#+\s*/, '').toLowerCase().trim();
      if (head === lower) {
        let j = i + 1;
        while (j < lines.length) {
          if ((lines[j] ?? '').startsWith('## ') || (lines[j] ?? '').startsWith('# ')) break;
          j++;
        }
        insertAt = j;
        break;
      }
    }
  }

  if (insertAt === -1) {
    return md.trimEnd() + '\n\n## ' + sectionName + '\n\n' + text + '\n';
  }

  const before = lines.slice(0, insertAt);
  const after = lines.slice(insertAt);
  if ((before[before.length - 1] ?? '').trim() !== '') before.push('');
  return [...before, text, '', ...after].join('\n');
}

// ─── mark-fix-status ───────────────────────────────────────────────────────

async function updateItemStatus(bookDir: string, itemId: string, status: string): Promise<void> {
  const itemsPath = join(bookDir, '_system', 'ambiguity-items.json');
  if (!existsSync(itemsPath)) return;
  const raw = JSON.parse(await readFile(itemsPath, 'utf-8'));
  for (const item of raw.items ?? []) {
    if (item.id === itemId) item.status = status;
  }
  await writeFile(itemsPath, JSON.stringify(raw, null, 2), 'utf-8');
}

// ─── route handler ─────────────────────────────────────────────────────────

export const POST: APIRoute = async ({ request }) => {
  let body: any;
  try { body = await request.json(); } catch { return apiError('Invalid JSON'); }

  const { action, slug } = body;
  if (!action || !slug) return apiError('Missing action or slug');

  try {
    if (action === 'save-checklist') return saveChecklist(slug, body.terms ?? []);
    if (action === 'apply-fix') return applyFix(slug, body.item_id, body.episode_id, body.section, body.fix_text);
    if (action === 'mark-fix-status') {
      const ref = await findContent(slug);
      if (!ref) return apiError('Book not found', 404);
      await updateItemStatus(ref.dir, body.item_id, body.status);
      return apiOk({ updated: body.item_id, status: body.status });
    }
    return apiError(`Unknown action: ${action}`);
  } catch (e) {
    return apiServerError(String(e));
  }
};
