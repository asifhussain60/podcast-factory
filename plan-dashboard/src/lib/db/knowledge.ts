/**
 * Server-only SQLite helper for knowledge.db atoms.
 *
 * Opens content/knowledge-base/knowledge.db (shared with the pipeline) in
 * read-only mode for queries. The write path lives in /api/corpus/atom.ts
 * (M-3). All operations are synchronous (better-sqlite3).
 *
 * NEVER imported from a browser bundle — only from /src/pages/* and /src/pages/api/*.
 */

import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { MockAtom, AtomType, Tradition, CorpusId } from '../../data/corpus-mock-sample';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// plan-dashboard/src/lib/db  →  ../../../../  →  repo root  →  content/...
const DB_PATH = path.resolve(__dirname, '../../../../content/knowledge-base/knowledge.db');

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH, { readonly: true });
  _db.pragma('journal_mode = WAL');
  return _db;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AtomFilters {
  type?: string;
  tradition?: string;
  content_level?: string;
  q?: string;
  page?: number;
  pageSize?: number;
  includeQuran?: boolean;
}

interface AtomRow {
  id: string;
  type: string;
  tradition: string;
  content_level: string | null;
  body: string;
}

export type LiveAtom = MockAtom & { content_level?: string };

// ---------------------------------------------------------------------------
// Row → MockAtom mapping
// ---------------------------------------------------------------------------

function rowToAtom(row: AtomRow): LiveAtom {
  let body: Record<string, unknown> = {};
  try { body = JSON.parse(row.body) as Record<string, unknown>; } catch { /* malformed */ }

  const rawText = typeof body.text_en === 'string' ? body.text_en : '';
  // Strip leading markdown headings for a clean gloss.
  const gloss = rawText.replace(/^#+\s+/, '').split('\n')[0].slice(0, 120) || row.id;
  const binderSlug = typeof body.binder_slug === 'string' ? body.binder_slug : '';
  const chapterSlug = typeof body.chapter_slug === 'string' ? body.chapter_slug : '';
  const sourceRef = [binderSlug, chapterSlug].filter(Boolean).join(' · ');
  const topicTags = Array.isArray(body.topic_tags) ? (body.topic_tags as string[]) : [];

  return {
    id: row.id,
    type: row.type as AtomType,
    tradition: (row.tradition || 'universal') as Tradition,
    corpus: (['quran', 'hadith', 'ksessions', 'wisdom'].includes(binderSlug) ? binderSlug : 'wisdom') as CorpusId,
    gloss,
    source_ref: sourceRef,
    text_en: rawText.slice(0, 2000),
    concepts: topicTags,
    arabic: typeof body.arabic === 'string' ? body.arabic : undefined,
    root: typeof body.root === 'string' ? body.root : undefined,
    content_level: row.content_level ?? undefined,
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface ListAtomsResult {
  atoms: LiveAtom[];
  total: number;
  page: number;
  pageSize: number;
  facets: {
    byType: Record<string, number>;
    byTradition: Record<string, number>;
    byLevel: Record<string, number>;
  };
}

export function listAtoms(filters: AtomFilters = {}): ListAtomsResult {
  const db = getDb();
  const {
    type,
    tradition,
    content_level,
    q,
    page = 0,
    pageSize = 500,
    includeQuran = false,
  } = filters;

  const where: string[] = [];
  const params: unknown[] = [];

  if (!includeQuran) { where.push("type != 'quran'"); }
  if (type) { where.push('type = ?'); params.push(type); }
  if (tradition) { where.push('tradition = ?'); params.push(tradition); }
  if (content_level) { where.push('content_level = ?'); params.push(content_level); }
  if (q) { where.push('body LIKE ?'); params.push(`%${q}%`); }

  const clause = where.length ? `WHERE ${where.join(' AND ')}` : '';

  const countRow = db.prepare(`SELECT count(*) as n FROM atoms ${clause}`)
    .get(...(params as Parameters<typeof db.prepare>[0][])) as { n: number };

  const rows = db.prepare(
    `SELECT id, type, tradition, content_level, body FROM atoms ${clause} LIMIT ? OFFSET ?`,
  ).all(...(params as Parameters<typeof db.prepare>[0][]), pageSize, page * pageSize) as AtomRow[];

  // Facet counts over the same filter base (excluding pagination).
  const byTypeRows = db.prepare(
    `SELECT type, count(*) as n FROM atoms ${clause} GROUP BY type`,
  ).all(...(params as Parameters<typeof db.prepare>[0][])) as { type: string; n: number }[];
  const byTradRows = db.prepare(
    `SELECT tradition, count(*) as n FROM atoms ${clause} GROUP BY tradition`,
  ).all(...(params as Parameters<typeof db.prepare>[0][])) as { tradition: string; n: number }[];
  const byLvlRows = db.prepare(
    `SELECT content_level, count(*) as n FROM atoms ${clause} AND content_level IS NOT NULL GROUP BY content_level`,
  ).all(...(params as Parameters<typeof db.prepare>[0][])) as { content_level: string; n: number }[];

  return {
    atoms: rows.map(rowToAtom),
    total: countRow.n,
    page,
    pageSize,
    facets: {
      byType: Object.fromEntries(byTypeRows.map((r) => [r.type, r.n])),
      byTradition: Object.fromEntries(byTradRows.map((r) => [r.tradition, r.n])),
      byLevel: Object.fromEntries(byLvlRows.map((r) => [r.content_level, r.n])),
    },
  };
}

export function getAtom(id: string): LiveAtom | undefined {
  const db = getDb();
  const row = db.prepare(
    'SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?',
  ).get(id) as AtomRow | undefined;
  return row ? rowToAtom(row) : undefined;
}

export function listTags(): string[] {
  const db = getDb();
  const rows = db.prepare(`
    SELECT DISTINCT value as tag
    FROM atoms, json_each(json_extract(body, '$.topic_tags'))
    WHERE json_extract(body, '$.topic_tags') IS NOT NULL
    ORDER BY value
  `).all() as { tag: string }[];
  return rows.map((r) => r.tag);
}

export function dbTotals(): { total: number; byType: Record<string, number>; byTradition: Record<string, number> } {
  const db = getDb();
  const total = (db.prepare('SELECT count(*) as n FROM atoms').get() as { n: number }).n;
  const byTypeRows = db.prepare('SELECT type, count(*) as n FROM atoms GROUP BY type').all() as { type: string; n: number }[];
  const byTradRows = db.prepare('SELECT tradition, count(*) as n FROM atoms GROUP BY tradition').all() as { tradition: string; n: number }[];
  return {
    total,
    byType: Object.fromEntries(byTypeRows.map((r) => [r.type, r.n])),
    byTradition: Object.fromEntries(byTradRows.map((r) => [r.tradition, r.n])),
  };
}
