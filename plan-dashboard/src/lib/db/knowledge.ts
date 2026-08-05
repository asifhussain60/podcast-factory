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

import Database from "better-sqlite3";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// Canonical atom types — authoritative here; re-exported by corpus-fallback
// ---------------------------------------------------------------------------

export type AtomType =
  "quran" | "hadith" | "term" | "doctrine" | "etymology" | "poetry";
export type Tradition = "universal" | "fatimid-ismaili" | "ismaili";
export type CorpusId = "quran" | "hadith" | "ksessions" | "wisdom";

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
const DB_PATH = path.resolve(
  __dirname,
  "../../../../content/knowledge-base/knowledge.db",
);

let _db: Database.Database | null = null;
let _wdb: Database.Database | null = null;

/**
 * knowledge.db is BUILT BY THE PIPELINE and gitignored (`content/knowledge-base/*.db`),
 * unlike its tracked neighbour mirror.db. It legitimately does not exist on a fresh
 * clone, on CI, or on a machine that has not run the intelligence phases — and the
 * Studio is expected to open anyway.
 *
 * Checked per call rather than cached: the pipeline can create the file while the dev
 * server is running, and a reader that latched "absent" at boot would stay empty until
 * someone restarted it. (The inverse mistake cost an hour on 2026-08-01: moving the
 * file aside under a RUNNING server proved nothing, because sqlite does not notice a
 * file unlinked beneath an open connection.)
 */
export function knowledgeDbAvailable(): boolean {
  return existsSync(DB_PATH);
}

/**
 * Whether a specific table this module reads is actually present.
 *
 * File existence is NOT a sufficient test, and assuming it was made the first
 * version of this guard order-dependent. `annotations.ts` opens the SAME path with
 * a writable connection and calls `ensureTables()`, so the first request to
 * /api/annotations CREATES knowledge.db carrying only the three annotation tables.
 * From that moment `existsSync` answers true while `section_depths` and
 * `action_items` still do not exist, and the reads fail on "no such table" exactly
 * as they did before — but only if the annotations route happened to be hit first.
 * Observed live on 2026-08-01: a smoke run left behind a 4 KB knowledge.db holding
 * annotation_tags, paragraph_annotations and paragraph_notes and nothing else.
 *
 * So a partial database is a NORMAL state here, not corruption, and "the pipeline
 * has not built my tables yet" is the same condition as "no database at all".
 * Both answer empty.
 */
function readableTable(table: string): Database.Database | null {
  if (!knowledgeDbAvailable()) return null;
  const db = getDb();
  const row = db
    .prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?")
    .get(table);
  return row ? db : null;
}

/** Write counterpart: refuse rather than fail mid-statement on a missing table. */
function writableTable(table: string): Database.Database {
  const db = getWriteDb(); // throws KnowledgeDbUnavailableError when the file is absent
  const row = db
    .prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?")
    .get(table);
  if (!row) throw new KnowledgeDbUnavailableError();
  return db;
}

/**
 * Thrown by write paths when the database is absent. Reads degrade to empty instead —
 * "no rows" is a truthful answer for a corpus nobody has built yet — but a WRITE that
 * silently succeeds into nowhere is a lie, so callers must handle this.
 */
export class KnowledgeDbUnavailableError extends Error {
  readonly code = "KNOWLEDGE_DB_UNAVAILABLE";
  constructor() {
    super(
      `knowledge.db not found at ${DB_PATH} — it is built by the pipeline's ` +
        `intelligence phases and is not tracked in git. Reads return empty; writes ` +
        `are refused until it exists.`,
    );
    this.name = "KnowledgeDbUnavailableError";
  }
}

function getDb(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH, { readonly: true });
  _db.pragma("journal_mode = WAL");
  return _db;
}

function getWriteDb(): Database.Database {
  if (_wdb) return _wdb;
  // `new Database(path)` CREATES the file when it is missing. That turned an absent
  // database into a present-but-schema-less one, so the write failed on "no such
  // table" and every later READ failed the same way — a missing file quietly upgraded
  // into a corrupt one. Refuse instead.
  if (!knowledgeDbAvailable()) throw new KnowledgeDbUnavailableError();
  _wdb = new Database(DB_PATH);
  _wdb.pragma("journal_mode = WAL");
  _wdb.pragma("foreign_keys = ON");
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
  try {
    body = JSON.parse(row.body) as Record<string, unknown>;
  } catch {
    /* malformed */
  }

  const rawText = typeof body.text_en === "string" ? body.text_en : "";
  // Strip leading markdown headings for a clean gloss.
  const gloss =
    rawText
      .replace(/^#+\s+/, "")
      .split("\n")[0]
      .slice(0, 120) || row.id;
  const binderSlug =
    typeof body.binder_slug === "string" ? body.binder_slug : "";
  const chapterSlug =
    typeof body.chapter_slug === "string" ? body.chapter_slug : "";
  const sourceRef = [binderSlug, chapterSlug].filter(Boolean).join(" · ");
  const topicTags = Array.isArray(body.topic_tags)
    ? (body.topic_tags as string[])
    : [];

  return {
    id: row.id,
    type: row.type as AtomType,
    tradition: (row.tradition || "universal") as Tradition,
    corpus: (["quran", "hadith", "ksessions", "wisdom"].includes(binderSlug)
      ? binderSlug
      : "wisdom") as CorpusId,
    gloss,
    source_ref: sourceRef,
    text_en: rawText.slice(0, 2000),
    concepts: topicTags,
    arabic: typeof body.arabic === "string" ? body.arabic : undefined,
    root: typeof body.root === "string" ? body.root : undefined,
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
  const db = readableTable("atoms");
  if (!db)
    return {
      atoms: [],
      total: 0,
      page: 0,
      pageSize: 0,
      facets: { byType: {}, byTradition: {}, byLevel: {} },
    };
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

  if (!includeQuran) {
    where.push("type != 'quran'");
  }
  if (type) {
    where.push("type = ?");
    params.push(type);
  }
  if (tradition) {
    where.push("tradition = ?");
    params.push(tradition);
  }
  if (content_level) {
    where.push("content_level = ?");
    params.push(content_level);
  }
  if (q) {
    where.push("body LIKE ?");
    params.push(`%${q}%`);
  }

  const clause = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const countRow = db
    .prepare(`SELECT count(*) as n FROM atoms ${clause}`)
    .get(...(params as Parameters<typeof db.prepare>[0][])) as { n: number };

  const rows = db
    .prepare(
      `SELECT id, type, tradition, content_level, body FROM atoms ${clause} LIMIT ? OFFSET ?`,
    )
    .all(
      ...(params as Parameters<typeof db.prepare>[0][]),
      pageSize,
      page * pageSize,
    ) as AtomRow[];

  // Facet counts over the same filter base (excluding pagination).
  const byTypeRows = db
    .prepare(`SELECT type, count(*) as n FROM atoms ${clause} GROUP BY type`)
    .all(...(params as Parameters<typeof db.prepare>[0][])) as {
    type: string;
    n: number;
  }[];
  const byTradRows = db
    .prepare(
      `SELECT tradition, count(*) as n FROM atoms ${clause} GROUP BY tradition`,
    )
    .all(...(params as Parameters<typeof db.prepare>[0][])) as {
    tradition: string;
    n: number;
  }[];
  const byLvlRows = db
    .prepare(
      `SELECT content_level, count(*) as n FROM atoms ${clause} AND content_level IS NOT NULL GROUP BY content_level`,
    )
    .all(...(params as Parameters<typeof db.prepare>[0][])) as {
    content_level: string;
    n: number;
  }[];

  return {
    atoms: rows.map(rowToAtom),
    total: countRow.n,
    page,
    pageSize,
    facets: {
      byType: Object.fromEntries(byTypeRows.map((r) => [r.type, r.n])),
      byTradition: Object.fromEntries(
        byTradRows.map((r) => [r.tradition, r.n]),
      ),
      byLevel: Object.fromEntries(byLvlRows.map((r) => [r.content_level, r.n])),
    },
  };
}

export function getAtom(id: string): LiveAtom | undefined {
  const db = readableTable("atoms");
  if (!db) return undefined;
  const row = db
    .prepare(
      "SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?",
    )
    .get(id) as AtomRow | undefined;
  return row ? rowToAtom(row) : undefined;
}

export function listTags(): string[] {
  const db = readableTable("atoms");
  if (!db) return [];
  const rows = db
    .prepare(
      `
    SELECT DISTINCT value as tag
    FROM atoms, json_each(json_extract(body, '$.topic_tags'))
    WHERE json_extract(body, '$.topic_tags') IS NOT NULL
    ORDER BY value
  `,
    )
    .all() as { tag: string }[];
  return rows.map((r) => r.tag);
}

export function dbTotals(): {
  total: number;
  byType: Record<string, number>;
  byTradition: Record<string, number>;
} {
  const db = readableTable("atoms");
  if (!db) return { total: 0, byType: {}, byTradition: {} };
  const total = (
    db.prepare("SELECT count(*) as n FROM atoms").get() as { n: number }
  ).n;
  const byTypeRows = db
    .prepare("SELECT type, count(*) as n FROM atoms GROUP BY type")
    .all() as { type: string; n: number }[];
  const byTradRows = db
    .prepare("SELECT tradition, count(*) as n FROM atoms GROUP BY tradition")
    .all() as { tradition: string; n: number }[];
  return {
    total,
    byType: Object.fromEntries(byTypeRows.map((r) => [r.type, r.n])),
    byTradition: Object.fromEntries(byTradRows.map((r) => [r.tradition, r.n])),
  };
}

// ---------------------------------------------------------------------------
// Write operations (M-3) — writable connection
// ---------------------------------------------------------------------------

// Atom content_level — Kashkole 6-rung ladder; must stay stable for existing knowledge atoms.
const ALLOWED_ATOM_LEVELS = new Set([
  "general",
  "advanced",
  "taveel",
  "mamsool",
  "mabda_maad",
  "haqaiq",
]);

// Section depth_level — per-content-profile vocabulary for Studio section annotations.
const ALLOWED_DEPTH_LEVELS = new Set([
  // islamic_scholarly
  "narrative",
  "sharia",
  "esoteric",
  "origins",
  "reality",
  // consumer_explainer (site)
  "website",
  "application",
  "platform",
  "api",
  // technical
  "coding",
  "agentic_ai",
  "architecture",
  "devops",
  "security",
  "data_ml",
  // fiction (narrative shared with islamic_scholarly)
  "character",
  "theme",
  "world",
  "conflict",
  "voice",
]);
const ALLOWED_TYPES = new Set([
  "quran",
  "hadith",
  "term",
  "doctrine",
  "etymology",
  "poetry",
]);
const ALLOWED_TRADITIONS = new Set(["universal", "fatimid-ismaili", "ismaili"]);

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
  if (
    input.content_level !== undefined &&
    input.content_level !== null &&
    !ALLOWED_ATOM_LEVELS.has(input.content_level)
  ) {
    throw new Error(`Invalid content_level: ${input.content_level}`);
  }
  const db = writableTable("atoms");
  const row = db
    .prepare(
      "SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?",
    )
    .get(id) as AtomRow | undefined;
  if (!row) throw new Error(`Atom not found: ${id}`);

  let body: Record<string, unknown> = {};
  try {
    body = JSON.parse(row.body) as Record<string, unknown>;
  } catch {
    /* malformed */
  }

  db.transaction(() => {
    if (input.text_en !== undefined) {
      body.text_en = input.text_en;
    }
    if (input.tags !== undefined) {
      body.topic_tags = input.tags;
    }
    db.prepare(
      "UPDATE atoms SET body = ?, content_level = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
    ).run(
      JSON.stringify(body),
      input.content_level !== undefined
        ? input.content_level
        : row.content_level,
      id,
    );
  })();

  const updated = db
    .prepare(
      "SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?",
    )
    .get(id) as AtomRow;
  return rowToAtom(updated);
}

export function createAtom(input: CreateAtomInput): LiveAtom {
  if (!ALLOWED_TYPES.has(input.type))
    throw new Error(`Invalid type: ${input.type}`);
  if (!ALLOWED_TRADITIONS.has(input.tradition))
    throw new Error(`Invalid tradition: ${input.tradition}`);
  if (!input.text_en.trim()) throw new Error("text_en must not be empty");
  if (input.content_level && !ALLOWED_ATOM_LEVELS.has(input.content_level)) {
    throw new Error(`Invalid content_level: ${input.content_level}`);
  }
  const db = writableTable("atoms");
  const id = `${input.type}:user:${Date.now()}`;
  const body = {
    text_en: input.text_en,
    tradition: input.tradition,
    topic_tags: input.tags ?? [],
    binder_slug: "user",
    chapter_slug: "",
  };
  db.prepare(
    `
    INSERT INTO atoms (id, type, tradition, content_level, body, confidence)
    VALUES (?, ?, ?, ?, ?, 1.0)
  `,
  ).run(
    id,
    input.type,
    input.tradition,
    input.content_level ?? null,
    JSON.stringify(body),
  );
  const row = db
    .prepare(
      "SELECT id, type, tradition, content_level, body FROM atoms WHERE id = ?",
    )
    .get(id) as AtomRow;
  return rowToAtom(row);
}

// ---------------------------------------------------------------------------
// Section depth operations (Wave N) — stable ordinal-based IDs per chapter
// ---------------------------------------------------------------------------

export interface SectionDepth {
  section_ordinal: number;
  section_slug: string;
  depth_level: string;
  section_tags: string[];
  source: "pipeline" | "human";
}

type SectionDepthRow = Omit<SectionDepth, "section_tags"> & {
  section_tags: string;
};

function rowToSectionDepth(row: SectionDepthRow): SectionDepth {
  let tags: string[];
  try {
    tags = JSON.parse(row.section_tags || "[]");
  } catch {
    tags = [];
  }
  return { ...row, section_tags: tags };
}

export function getSectionDepths(
  bookSlug: string,
  chapterId: string,
): SectionDepth[] {
  const db = readableTable("section_depths");
  if (!db) return [];
  const rows = db
    .prepare(
      "SELECT section_ordinal, section_slug, depth_level, section_tags, source FROM section_depths WHERE book_slug = ? AND chapter_id = ? ORDER BY section_ordinal",
    )
    .all(bookSlug, chapterId) as SectionDepthRow[];
  return rows.map(rowToSectionDepth);
}

export function upsertSectionDepth(
  bookSlug: string,
  chapterId: string,
  ordinal: number,
  slug: string,
  depthLevel: string,
  source: "pipeline" | "human" = "human",
  tags: string[] = [],
): SectionDepth {
  if (!ALLOWED_DEPTH_LEVELS.has(depthLevel))
    throw new Error(`Invalid depth_level: ${depthLevel}`);
  const tagsJson = JSON.stringify(tags);
  const db = writableTable("section_depths");
  db.prepare(
    `
    INSERT INTO section_depths (book_slug, chapter_id, section_ordinal, section_slug, depth_level, section_tags, source)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(book_slug, chapter_id, section_ordinal)
    DO UPDATE SET section_slug = excluded.section_slug,
                  depth_level  = excluded.depth_level,
                  section_tags = excluded.section_tags,
                  source       = excluded.source,
                  updated_at   = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
  `,
  ).run(bookSlug, chapterId, ordinal, slug, depthLevel, tagsJson, source);
  return rowToSectionDepth(
    db
      .prepare(
        "SELECT section_ordinal, section_slug, depth_level, section_tags, source FROM section_depths WHERE book_slug = ? AND chapter_id = ? AND section_ordinal = ?",
      )
      .get(bookSlug, chapterId, ordinal) as SectionDepthRow,
  );
}

// ---------------------------------------------------------------------------
// Action items — deferred AI action-item queue (editor stamps, CLI drains)
// ---------------------------------------------------------------------------

export type ActionScope = "paragraph" | "term";
export type ActionStatus = "pending" | "resolved" | "dismissed";

export interface ActionItem {
  id: number;
  scope: ActionScope;
  para_ordinal: number;
  term_text: string;
  anchor_text: string;
  action_kind: string;
  note: string | null;
  status: ActionStatus;
  result: string | null;
  source: "human" | "pipeline";
}

const ACTION_ITEM_COLS =
  "id, scope, para_ordinal, term_text, anchor_text, action_kind, note, status, result, source";

export function getActionItems(
  bookSlug: string,
  chapterId: string,
): ActionItem[] {
  const db = readableTable("action_items");
  if (!db) return [];
  return db
    .prepare(
      `SELECT ${ACTION_ITEM_COLS} FROM action_items WHERE book_slug = ? AND chapter_id = ? ORDER BY para_ordinal, id`,
    )
    .all(bookSlug, chapterId) as ActionItem[];
}

/** Insert (or update note/anchor on conflict) one action item. Identity is
 *  (book, chapter, para_ordinal, term_text, action_kind) — re-stamping is a no-op
 *  beyond refreshing the anchor text + note. */
export function upsertActionItem(input: {
  bookSlug: string;
  chapterId: string;
  scope: ActionScope;
  paraOrdinal: number;
  termText?: string;
  anchorText?: string;
  actionKind: string;
  note?: string;
  source?: "human" | "pipeline";
}): ActionItem {
  const termText = input.termText ?? "";
  const anchorText = input.anchorText ?? "";
  const source = input.source ?? "human";
  const db = writableTable("action_items");
  db.prepare(
    `
    INSERT INTO action_items (book_slug, chapter_id, scope, para_ordinal, term_text, anchor_text, action_kind, note, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(book_slug, chapter_id, para_ordinal, term_text, action_kind)
    DO UPDATE SET anchor_text = excluded.anchor_text,
                  note        = excluded.note,
                  updated_at  = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
  `,
  ).run(
    input.bookSlug,
    input.chapterId,
    input.scope,
    input.paraOrdinal,
    termText,
    anchorText,
    input.actionKind,
    input.note ?? null,
    source,
  );
  return db
    .prepare(
      `SELECT ${ACTION_ITEM_COLS} FROM action_items WHERE book_slug = ? AND chapter_id = ? AND para_ordinal = ? AND term_text = ? AND action_kind = ?`,
    )
    .get(
      input.bookSlug,
      input.chapterId,
      input.paraOrdinal,
      termText,
      input.actionKind,
    ) as ActionItem;
}

/** Remove one action item by its row id (scoped to book+chapter for safety). */
export function deleteActionItem(
  bookSlug: string,
  chapterId: string,
  id: number,
): boolean {
  const db = writableTable("action_items");
  const info = db
    .prepare(
      "DELETE FROM action_items WHERE book_slug = ? AND chapter_id = ? AND id = ?",
    )
    .run(bookSlug, chapterId, id);
  return info.changes > 0;
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
  const db = readableTable("lookup_levels");
  if (!db) return [];
  const rows = db
    .prepare(
      "SELECT level_id, level_name, code_id, ordering, is_base_rung, color_hex FROM lookup_levels ORDER BY ordering",
    )
    .all() as (Omit<LookupLevel, "is_base_rung"> & { is_base_rung: number })[];
  return rows.map((r) => ({ ...r, is_base_rung: r.is_base_rung === 1 }));
}
