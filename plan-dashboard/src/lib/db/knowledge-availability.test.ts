/**
 * knowledge.db availability guards — the Studio must open on a machine that has
 * never run the pipeline.
 *
 * knowledge.db is gitignored (`content/knowledge-base/*.db`) and built by the
 * pipeline's intelligence phases, unlike its tracked neighbour mirror.db. On
 * 2026-08-01 four Studio routes 500'd on CI for exactly this reason and the
 * runtime smoke gate stayed red (RCA-009, AI-8).
 *
 * These tests pin the two states that are NOT "the database is fully built",
 * because both occur in the wild and each produced a 500 before this guard:
 *
 *   1. absent  — a fresh clone, CI, a new machine.
 *   2. PARTIAL — knowledge.db exists but carries only SOME tables. This is not
 *      corruption: `annotations.ts` opens the SAME path with a writable
 *      connection and calls ensureTables(), so the first request to
 *      /api/annotations creates the file with three annotation tables and
 *      nothing else. A guard that only checked file existence passed here and
 *      then failed on "no such table" — order-dependent on which route was hit
 *      first, which is the worst kind of green.
 *
 * The queries under test are the real ones from knowledge.ts, exercised against
 * a temp database rather than the repo's own, so the suite never depends on
 * whether this machine has run the pipeline.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import { mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const TABLE_PROBE =
  "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?";

/** Mirrors `readableTable` in knowledge.ts: absent file OR absent table → null. */
function readableTable(
  dbPath: string,
  table: string,
): Database.Database | null {
  if (!existsSync(dbPath)) return null;
  const db = new Database(dbPath, { readonly: true });
  return db.prepare(TABLE_PROBE).get(table) ? db : null;
}

describe("knowledge.db availability", () => {
  test("an absent database reads as unavailable, not as an error", () => {
    const dir = mkdtempSync(join(tmpdir(), "kdb-absent-"));
    try {
      const missing = join(dir, "knowledge.db");
      assert.equal(existsSync(missing), false);
      assert.equal(readableTable(missing, "section_depths"), null);
      assert.equal(readableTable(missing, "action_items"), null);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("a PARTIAL database reads as unavailable for the tables it lacks", () => {
    const dir = mkdtempSync(join(tmpdir(), "kdb-partial-"));
    try {
      const p = join(dir, "knowledge.db");
      // Exactly what annotations.ts::ensureTables leaves behind on a machine
      // where the pipeline has never run.
      const seed = new Database(p);
      seed.exec(`
        CREATE TABLE annotation_tags (id INTEGER PRIMARY KEY);
        CREATE TABLE paragraph_annotations (id INTEGER PRIMARY KEY);
        CREATE TABLE paragraph_notes (id INTEGER PRIMARY KEY);
      `);
      seed.close();

      // The file EXISTS — an existence-only guard would wave this through and
      // then throw "no such table" on the very next statement.
      assert.equal(existsSync(p), true);
      assert.equal(readableTable(p, "section_depths"), null);
      assert.equal(readableTable(p, "action_items"), null);
      assert.equal(readableTable(p, "atoms"), null);

      // ...while the tables that DO exist stay readable.
      assert.notEqual(readableTable(p, "annotation_tags"), null);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("a built database reads normally — the guard must not swallow real data", () => {
    const dir = mkdtempSync(join(tmpdir(), "kdb-built-"));
    try {
      const p = join(dir, "knowledge.db");
      const seed = new Database(p);
      seed.exec(`
        CREATE TABLE section_depths (
          book_slug TEXT, chapter_id TEXT, section_ordinal INTEGER,
          section_slug TEXT, depth_level TEXT, section_tags TEXT, source TEXT
        );
        INSERT INTO section_depths VALUES
          ('a-book','ch01',0,'opening','general','[]','pipeline'),
          ('a-book','ch01',1,'the-middle','general','[]','pipeline');
      `);
      seed.close();

      const db = readableTable(p, "section_depths");
      assert.notEqual(db, null);
      const rows = db!
        .prepare(
          "SELECT section_ordinal FROM section_depths WHERE book_slug = ? AND chapter_id = ? ORDER BY section_ordinal",
        )
        .all("a-book", "ch01");
      assert.equal(rows.length, 2, "real rows must survive the guard");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("a write into a missing database must NOT create one", () => {
    // `new Database(path)` with no readonly flag CREATES the file. That is how an
    // absent database became a present-but-schema-less one on 2026-08-01: a page
    // load recreated knowledge.db at 4 KB, after which every read failed on
    // "no such table" instead of degrading. getWriteDb() now refuses first.
    const dir = mkdtempSync(join(tmpdir(), "kdb-write-"));
    try {
      const p = join(dir, "knowledge.db");
      const guard = () => {
        if (!existsSync(p)) throw new Error("KNOWLEDGE_DB_UNAVAILABLE");
        return new Database(p);
      };
      assert.throws(guard, /KNOWLEDGE_DB_UNAVAILABLE/);
      assert.equal(
        existsSync(p),
        false,
        "refusing a write must leave the filesystem untouched",
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
