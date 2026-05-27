/**
 * Server-only SQLite helper for paragraph annotations.
 *
 * Opens content/knowledge-base/knowledge.db (shared with the pipeline),
 * creates the two annotation tables on first use, and seeds the five
 * default tags. All operations are synchronous (better-sqlite3).
 *
 * NEVER imported from a browser bundle — only from /src/pages/api/* routes.
 */

import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// plan-dashboard/src/lib/db  →  ../../..  →  plan-dashboard  →  ../content/...
const DB_PATH = path.resolve(__dirname, '../../../../content/knowledge-base/knowledge.db');

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH);
  _db.pragma('journal_mode = WAL');
  _db.pragma('foreign_keys = ON');
  ensureTables(_db);
  return _db;
}

// ---------------------------------------------------------------------------
// Schema bootstrap
// ---------------------------------------------------------------------------

const DEFAULT_TAGS: { label: string; color: string; icon: string; sort_order: number }[] = [
  { label: 'esoteric',             color: '#7c3aed', icon: 'Eye',               sort_order: 0 },
  { label: 'reality',              color: '#0284c7', icon: 'Globe',             sort_order: 1 },
  { label: 'sharia',               color: '#0f766e', icon: 'Scale',             sort_order: 2 },
  { label: 'mark for deletion',    color: '#e11d48', icon: 'Trash2',            sort_order: 3 },
  { label: 'mark for improvement', color: '#d97706', icon: 'Lightbulb',         sort_order: 4 },
];

function ensureTables(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS annotation_tags (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      tag_label  TEXT    NOT NULL UNIQUE,
      tag_color  TEXT    NOT NULL DEFAULT '#6b7280',
      tag_icon   TEXT    NOT NULL DEFAULT 'Tag',
      is_default INTEGER NOT NULL DEFAULT 0,
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS paragraph_annotations (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      book_slug  TEXT    NOT NULL,
      chapter_id TEXT    NOT NULL,
      para_idx   INTEGER NOT NULL,
      tag_id     INTEGER NOT NULL REFERENCES annotation_tags(id) ON DELETE CASCADE,
      note       TEXT,
      created_at TEXT    DEFAULT (datetime('now')),
      UNIQUE (book_slug, chapter_id, para_idx, tag_id)
    );

    CREATE TABLE IF NOT EXISTS paragraph_notes (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      book_slug  TEXT    NOT NULL,
      chapter_id TEXT    NOT NULL,
      para_idx   INTEGER NOT NULL,
      note       TEXT    NOT NULL,
      updated_at TEXT    DEFAULT (datetime('now')),
      UNIQUE (book_slug, chapter_id, para_idx)
    );

    CREATE INDEX IF NOT EXISTS idx_pa_book_chapter
      ON paragraph_annotations (book_slug, chapter_id);

    CREATE INDEX IF NOT EXISTS idx_pn_book_chapter
      ON paragraph_notes (book_slug, chapter_id);
  `);

  // Seed defaults (idempotent — INSERT OR IGNORE)
  const insert = db.prepare(
    `INSERT OR IGNORE INTO annotation_tags (tag_label, tag_color, tag_icon, is_default, sort_order)
     VALUES (?, ?, ?, 1, ?)`
  );
  for (const t of DEFAULT_TAGS) {
    insert.run(t.label, t.color, t.icon, t.sort_order);
  }
}

// ---------------------------------------------------------------------------
// Tag operations
// ---------------------------------------------------------------------------

export interface AnnotationTag {
  id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
  is_default: number;
  sort_order: number;
}

export function getTags(): AnnotationTag[] {
  return getDb()
    .prepare(`SELECT * FROM annotation_tags ORDER BY sort_order, tag_label`)
    .all() as AnnotationTag[];
}

export function createTag(label: string, color: string, icon = 'Tag'): AnnotationTag {
  const db = getDb();
  const maxOrder = (db.prepare(`SELECT COALESCE(MAX(sort_order),0) AS m FROM annotation_tags`).get() as { m: number }).m;
  const info = db
    .prepare(`INSERT INTO annotation_tags (tag_label, tag_color, tag_icon, is_default, sort_order) VALUES (?,?,?,0,?)`)
    .run(label, color, icon, maxOrder + 1);
  return db.prepare(`SELECT * FROM annotation_tags WHERE id = ?`).get(info.lastInsertRowid) as AnnotationTag;
}

export function deleteTag(id: number): void {
  getDb().prepare(`DELETE FROM annotation_tags WHERE id = ? AND is_default = 0`).run(id);
}

// ---------------------------------------------------------------------------
// Annotation operations
// ---------------------------------------------------------------------------

export interface Annotation {
  id: number;
  book_slug: string;
  chapter_id: string;
  para_idx: number;
  tag_id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
  note: string | null;
  created_at: string;
}

export interface ParagraphNote {
  id: number;
  book_slug: string;
  chapter_id: string;
  para_idx: number;
  note: string;
  updated_at: string;
}

export function getAnnotations(bookSlug: string, chapterId: string): Annotation[] {
  return getDb()
    .prepare(
      `SELECT pa.*, at.tag_label, at.tag_color, at.tag_icon
       FROM paragraph_annotations pa
       JOIN annotation_tags at ON at.id = pa.tag_id
       WHERE pa.book_slug = ? AND pa.chapter_id = ?
       ORDER BY pa.para_idx, pa.created_at`
    )
    .all(bookSlug, chapterId) as Annotation[];
}

/** Toggle: inserts if absent, deletes if present. Returns the new state. */
export function toggleAnnotation(
  bookSlug: string,
  chapterId: string,
  paraIdx: number,
  tagId: number,
  note?: string
): { added: boolean; id: number | null } {
  const db = getDb();
  const existing = db
    .prepare(`SELECT id FROM paragraph_annotations WHERE book_slug=? AND chapter_id=? AND para_idx=? AND tag_id=?`)
    .get(bookSlug, chapterId, paraIdx, tagId) as { id: number } | undefined;

  if (existing) {
    db.prepare(`DELETE FROM paragraph_annotations WHERE id = ?`).run(existing.id);
    return { added: false, id: null };
  }

  const info = db
    .prepare(`INSERT INTO paragraph_annotations (book_slug, chapter_id, para_idx, tag_id, note) VALUES (?,?,?,?,?)`)
    .run(bookSlug, chapterId, paraIdx, tagId, note ?? null);
  return { added: true, id: Number(info.lastInsertRowid) };
}

export function deleteAnnotation(id: number): void {
  getDb().prepare(`DELETE FROM paragraph_annotations WHERE id = ?`).run(id);
}

export function clearChapterAnnotations(bookSlug: string, chapterId: string): void {
  const db = getDb();
  db.prepare(`DELETE FROM paragraph_annotations WHERE book_slug = ? AND chapter_id = ?`).run(bookSlug, chapterId);
  db.prepare(`DELETE FROM paragraph_notes WHERE book_slug = ? AND chapter_id = ?`).run(bookSlug, chapterId);
}

export function getParagraphNotes(bookSlug: string, chapterId: string): ParagraphNote[] {
  return getDb()
    .prepare(
      `SELECT *
       FROM paragraph_notes
       WHERE book_slug = ? AND chapter_id = ?
       ORDER BY para_idx ASC`
    )
    .all(bookSlug, chapterId) as ParagraphNote[];
}

export function upsertParagraphNote(
  bookSlug: string,
  chapterId: string,
  paraIdx: number,
  note: string
): void {
  const text = note.trim();
  const db = getDb();

  if (!text) {
    db.prepare(
      `DELETE FROM paragraph_notes WHERE book_slug=? AND chapter_id=? AND para_idx=?`
    ).run(bookSlug, chapterId, paraIdx);
    return;
  }

  db.prepare(
    `INSERT INTO paragraph_notes (book_slug, chapter_id, para_idx, note, updated_at)
     VALUES (?, ?, ?, ?, datetime('now'))
     ON CONFLICT(book_slug, chapter_id, para_idx)
     DO UPDATE SET note = excluded.note, updated_at = datetime('now')`
  ).run(bookSlug, chapterId, paraIdx, text);
}

export function getChapterAnnotationSnapshot(bookSlug: string, chapterId: string): {
  annotations: Annotation[];
  notes: ParagraphNote[];
} {
  return {
    annotations: getAnnotations(bookSlug, chapterId),
    notes: getParagraphNotes(bookSlug, chapterId),
  };
}
