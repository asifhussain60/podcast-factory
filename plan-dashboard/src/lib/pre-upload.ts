/**
 * pre-upload.ts — server-side reader for the /pre-upload review utility.
 *
 * Reads (1) the pronunciation listen-checklist.md for a book and (2) the
 * ambiguity-items.json (per-book, in _system/). All writes go through the
 * /api/pre-upload API endpoint so file-mutation logic stays in one place.
 */

import { join } from 'node:path';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { findContent, slugToTitle } from './content-paths';

// ─── Checklist ─────────────────────────────────────────────────────────────

export interface ChecklistTerm {
  n: number;
  term: string;
  rendered: string;
  ok: '' | 'y' | 'n';
  fix: string;
}

export interface ChecklistData {
  slug: string;
  title: string;
  terms: ChecklistTerm[];
  checklistPath: string;
  preamble: string;
}

const CHECKLIST_REL = '_system/probe/EP00-pronunciation-probe/listen-checklist.md';

function parseChecklistTable(md: string): ChecklistTerm[] {
  const terms: ChecklistTerm[] = [];
  const lines = md.split('\n');
  let inTable = false;
  let headerPassed = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('|')) {
      if (inTable) break;
      continue;
    }
    if (!inTable) {
      if (trimmed.includes('term') && trimmed.includes('rendered')) {
        inTable = true;
        headerPassed = false;
      }
      continue;
    }
    if (!headerPassed) {
      if (trimmed.startsWith('|---') || trimmed.startsWith('| ---')) {
        headerPassed = true;
      }
      continue;
    }
    const cells = trimmed.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
    if (cells.length < 3) continue;
    const n = parseInt(cells[0] ?? '0', 10);
    if (isNaN(n)) continue;
    const term = cells[1] ?? '';
    const rendered = cells[2] ?? '';
    const okRaw = (cells[3] ?? '').trim().toLowerCase();
    const ok: '' | 'y' | 'n' = okRaw === 'y' ? 'y' : okRaw === 'n' ? 'n' : '';
    const fix = cells[4] ?? '';
    terms.push({ n, term, rendered, ok, fix });
  }
  return terms;
}

function extractPreamble(md: string): string {
  const lines = md.split('\n');
  const preamble: string[] = [];
  for (const line of lines) {
    if (line.trim().startsWith('|')) break;
    preamble.push(line);
  }
  return preamble.join('\n').trim();
}

export async function getChecklist(slug: string): Promise<ChecklistData | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const bookDir = ref.dir;
  const checklistPath = join(bookDir, CHECKLIST_REL);
  if (!existsSync(checklistPath)) return null;
  const raw = await readFile(checklistPath, 'utf-8');
  return {
    slug,
    title: slugToTitle(slug),
    terms: parseChecklistTable(raw),
    checklistPath,
    preamble: extractPreamble(raw),
  };
}

// ─── Ambiguity items ────────────────────────────────────────────────────────

export type AmbiguityPriority = 'high' | 'medium' | 'low';
export type AmbiguityType = 'tension' | 'undefined_reference' | 'scaffolding_gap' | 'structural_absence';
export type AmbiguityStatus = 'pending' | 'applied' | 'skipped';

export interface AmbiguityItem {
  id: string;
  priority: AmbiguityPriority;
  type: AmbiguityType;
  description: string;
  episodes: string[];
  section: string;
  framing_hint: string;
  status: AmbiguityStatus;
}

export interface AmbiguityData {
  slug: string;
  title: string;
  items: AmbiguityItem[];
  itemsPath: string;
}

const AMBIGUITY_REL = '_system/ambiguity-items.json';

export async function getAmbiguityItems(slug: string): Promise<AmbiguityData | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const bookDir = ref.dir;
  const itemsPath = join(bookDir, AMBIGUITY_REL);
  if (!existsSync(itemsPath)) return null;
  const raw = await readFile(itemsPath, 'utf-8');
  const parsed = JSON.parse(raw);
  return {
    slug,
    title: slugToTitle(slug),
    items: parsed.items as AmbiguityItem[],
    itemsPath,
  };
}

// ─── Framing section reader ─────────────────────────────────────────────────

export async function getFramingSection(
  slug: string,
  episodeId: string,
  sectionName: string,
): Promise<{ episodeId: string; sectionName: string; content: string; framingPath: string } | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const bookDir = ref.dir;

  const draftsDir = join(bookDir, '_system', 'episode-drafts');
  if (!existsSync(draftsDir)) return null;

  const { readdirSync } = await import('node:fs');
  const entries = readdirSync(draftsDir);
  const match = entries.find((e: string) => e.startsWith(episodeId + '-') || e === episodeId);
  if (!match) return null;

  const framingPath = join(draftsDir, match, '00-framing.md');
  if (!existsSync(framingPath)) return null;

  const raw = await readFile(framingPath, 'utf-8');
  const content = extractSection(raw, sectionName);
  return { episodeId, sectionName, content, framingPath };
}

function extractSection(md: string, sectionName: string): string {
  const lines = md.split('\n');
  const lower = sectionName.toLowerCase().trim();
  let inSection = false;
  const collected: string[] = [];
  for (const line of lines) {
    if (line.startsWith('## ') || line.startsWith('# ')) {
      const head = line.replace(/^#+\s*/, '').toLowerCase().trim();
      if (head === lower) { inSection = true; continue; }
      else if (inSection) break;
    }
    if (inSection) collected.push(line);
  }
  return collected.join('\n').trim();
}
