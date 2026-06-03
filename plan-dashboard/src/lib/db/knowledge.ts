/**
 * Server-only SQLite helper for knowledge.db atoms.
 *
 * Opens content/knowledge-base/knowledge.db (shared with the pipeline).
 * Read queries use a readonly connection; write operations (M-3) use a
 * separate writable connection so reads are never blocked by writes.
 * All operations are synchronous (better-sqlite3).
 *
 * NEVER imported from a browser bundle — only from /src/pages/* and /src/pages/api/*.
 */

import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ---------------------------------------------------------------------------
// Canonical atom types — authoritative here; re-exported by corpus-mock-sample
// ---------------------------------------------------------------------------

export type AtomType = 'quran' | 'hadith' | 'term' | 'doctrine' | 'etymology' | 'poetry';
export type Tradition = 'universal' | 'fatimid-ismaili' | 'ismaili';
export type CorpusId = 'quran' | 'hadith' | 'ksessions' | 'wisdom';

export interface MockAtom {
  id: string;
  type: AtomType;
  corpus: CorpusId;
  tradition: Tradition;
  gloss: string;
  source_ref: string;
  arabic?: string;
  text_en: string;
  root?: string;
  concepts: string[];
}

export interface Concept {
  id: string;
  label: string;
  arabic: string;
  translit: string;
  root: string;
  definition: string;
  synonyms: string[];
  family: string[];
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// plan-dashboard/src/lib/db  →  ../../../../  →  repo root  →  content/...
const DB_PATH = path.resolve(__dirname, '../../../../content/knowledge-base/knowledge.db');

let _db: Database.Database | null = null;
let _wdb: Database.Database | null = null;

function getDb(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH, { readonly: true });
  _db.pragma('journal_mode = WAL');
  return _db;
}

function getWriteDb(): Database.Database {
  if (_wdb) return _wdb;
  _wdb = new Database(DB_PATH);
  _wdb.pragma('journal_mode = WAL');
  _wdb.pragma('foreign_keys = ON');
  return _wdb;
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

// ---------------------------------------------------------------------------
// Write operations (M-3) — writable connection
// ---------------------------------------------------------------------------

const ALLOWED_LEVELS = new Set(['general', 'advanced', 'taveel', 'mamsool', 'mabda_maad', 'haqaiq']);
const ALLOWED_TYPES = new Set(['quran', 'hadith', 'term', 'doctrine', 'etymology', 'poetry']);
const ALLOWED_TRADITIONS = new Set(['universal', 'fatimid-ismaili', 'ismaili']);

export interface UpdateAtomInput {
  text_en?: string;
  content_level?: string | null;
  tags?: string[];
}

export interface CreateAtomInput {
  type: string;
  text_en: string;
  tradition: string;
  content_level?: string;
  tags?: string[];
}

export function updateAtom(id: string, input: UpdateAtomInput): LiveAtom {
  if (input.content_level !== undefined && input.content_level !== null
    && !ALLOWED_LEVELS.has(input.content_level)) {
    throw new Error(`Invalid content_level: ${input.content_level}`);
  }
  const db = getWriteDb();
  const row = db.prepare(
    'SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?',
  ).get(id) as AtomRow | undefined;
  if (!row) throw new Error(`Atom not found: ${id}`);

  let body: Record<string, unknown> = {};
  try { body = JSON.parse(row.body) as Record<string, unknown>; } catch { /* malformed */ }

  db.transaction(() => {
    if (input.text_en !== undefined) {
      body.text_en = input.text_en;
    }
    if (input.tags !== undefined) {
      body.topic_tags = input.tags;
    }
    db.prepare(
      'UPDATE atoms SET body = ?, content_level = ?, updated_at = strftime(\'%Y-%m-%dT%H:%M:%SZ\', \'now\') WHERE id = ?',
    ).run(JSON.stringify(body), input.content_level !== undefined ? input.content_level : row.content_level, id);
  })();

  const updated = db.prepare(
    'SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?',
  ).get(id) as AtomRow;
  return rowToAtom(updated);
}

export function createAtom(input: CreateAtomInput): LiveAtom {
  if (!ALLOWED_TYPES.has(input.type)) throw new Error(`Invalid type: ${input.type}`);
  if (!ALLOWED_TRADITIONS.has(input.tradition)) throw new Error(`Invalid tradition: ${input.tradition}`);
  if (!input.text_en.trim()) throw new Error('text_en must not be empty');
  if (input.content_level && !ALLOWED_LEVELS.has(input.content_level)) {
    throw new Error(`Invalid content_level: ${input.content_level}`);
  }
  const db = getWriteDb();
  const id = `${input.type}:user:${Date.now()}`;
  const body = {
    text_en: input.text_en,
    tradition: input.tradition,
    topic_tags: input.tags ?? [],
    binder_slug: 'user',
    chapter_slug: '',
  };
  db.prepare(`
    INSERT INTO atoms (id, type, tradition, content_level, body, confidence)
    VALUES (?, ?, ?, ?, ?, 1.0)
  `).run(id, input.type, input.tradition, input.content_level ?? null, JSON.stringify(body));
  const row = db.prepare(
    'SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?',
  ).get(id) as AtomRow;
  return rowToAtom(row);
}

// ---------------------------------------------------------------------------
// Section depth operations (Wave N) — stable ordinal-based IDs per chapter
// ---------------------------------------------------------------------------

export interface SectionDepth {
  section_ordinal: number;
  section_slug: string;
  depth_level: string;
  source: 'pipeline' | 'human';
}

export function getSectionDepths(bookSlug: string, chapterId: string): SectionDepth[] {
  const db = getDb();
  return db.prepare(
    'SELECT section_ordinal, section_slug, depth_level, source FROM section_depths WHERE book_slug = ? AND chapter_id = ? ORDER BY section_ordinal',
  ).all(bookSlug, chapterId) as SectionDepth[];
}

export function upsertSectionDepth(
  bookSlug: string,
  chapterId: string,
  ordinal: number,
  slug: string,
  depthLevel: string,
  source: 'pipeline' | 'human' = 'human',
): SectionDepth {
  if (!ALLOWED_LEVELS.has(depthLevel)) throw new Error(`Invalid depth_level: ${depthLevel}`);
  const db = getWriteDb();
  db.prepare(`
    INSERT INTO section_depths (book_slug, chapter_id, section_ordinal, section_slug, depth_level, source)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(book_slug, chapter_id, section_ordinal)
    DO UPDATE SET section_slug = excluded.section_slug,
                  depth_level  = excluded.depth_level,
                  source       = excluded.source,
                  updated_at   = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
  `).run(bookSlug, chapterId, ordinal, slug, depthLevel, source);
  return db.prepare(
    'SELECT section_ordinal, section_slug, depth_level, source FROM section_depths WHERE book_slug = ? AND chapter_id = ? AND section_ordinal = ?',
  ).get(bookSlug, chapterId, ordinal) as SectionDepth;
}

// ---------------------------------------------------------------------------
// Lookup levels (Wave N) — Kashkole provenance for the 6-rung ladder
// ---------------------------------------------------------------------------

export interface LookupLevel {
  level_id: number;
  level_name: string;
  code_id: string | null;
  ordering: number;
  is_base_rung: boolean;
  color_hex: string | null;
}

export function getLookupLevels(): LookupLevel[] {
  const db = getDb();
  const rows = db.prepare(
    'SELECT level_id, level_name, code_id, ordering, is_base_rung, color_hex FROM lookup_levels ORDER BY ordering',
  ).all() as (Omit<LookupLevel, 'is_base_rung'> & { is_base_rung: number })[];
  return rows.map((r) => ({ ...r, is_base_rung: r.is_base_rung === 1 }));
}
