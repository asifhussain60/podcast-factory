import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { createTestDb, type TestDb } from "./d1";

/**
 * The index and the table it mirrors stay in step.
 *
 * `search_fts` is an external-content FTS5 table maintained by three triggers,
 * which is what lets the publisher's existing delete-and-reinsert maintain it
 * for free. The hazard that arrangement carries is silence: if the triggers stop
 * firing — or a later migration rebuilds `search_passage` by DROP and RENAME,
 * which 0008 and 0011 both did to `media_asset` — nothing raises. Search just
 * returns fewer results every day, and the page looks like a complete answer.
 *
 * So the triggers are exercised here against real SQLite through the real
 * migrations, rather than trusted.
 */

let t: TestDb;

const rows = (sql: string) =>
  (t.db as unknown as { prepare(q: string): { first<T>(): Promise<T> } })
    .prepare(sql)
    .first<{ n: number }>();

beforeEach(() => {
  t = createTestDb();
});

afterEach(() => t.close());

const insert = (id: number, body: string, arabic = "") =>
  t.exec(
    `INSERT INTO search_passage (id, slug, kind, quote, body_fold, arabic_fold)
     VALUES (${id}, 'a-book', 'chapter', 'quote ${id}', '${body}', '${arabic}');`,
  );

describe("the triggers", () => {
  it("indexes a passage when it is inserted", async () => {
    insert(1, "the intellect is the pen");
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'intellect'`,
        )
      ).n,
    ).toBe(1);
  });

  it("drops it from the index when the row goes", async () => {
    insert(1, "the intellect is the pen");
    t.exec(`DELETE FROM search_passage WHERE id = 1;`);
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'intellect'`,
        )
      ).n,
    ).toBe(0);
  });

  it("re-indexes it when the text changes", async () => {
    insert(1, "the intellect is the pen");
    t.exec(
      `UPDATE search_passage SET body_fold = 'the soul is the tablet' WHERE id = 1;`,
    );
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'intellect'`,
        )
      ).n,
    ).toBe(0);
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'tablet'`,
        )
      ).n,
    ).toBe(1);
  });

  it("leaves the index carrying exactly as many rows as the table", async () => {
    for (let i = 1; i <= 25; i++) insert(i, `passage number ${i}`);
    t.exec(`DELETE FROM search_passage WHERE id % 5 = 0;`);

    const table = (await rows(`SELECT count(*) AS n FROM search_passage`)).n;
    const index = (await rows(`SELECT count(*) AS n FROM search_fts`)).n;
    expect(index).toBe(table);
    expect(table).toBe(20);
  });

  it("survives a whole book being republished, which is what the publisher does", async () => {
    for (let i = 1; i <= 10; i++) insert(i, `first pass ${i}`);
    t.exec(`DELETE FROM search_passage WHERE slug = 'a-book';`);
    for (let i = 11; i <= 18; i++) insert(i, `second pass ${i}`);

    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'first'`,
        )
      ).n,
    ).toBe(0);
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'second'`,
        )
      ).n,
    ).toBe(8);
    expect((await rows(`SELECT count(*) AS n FROM search_fts`)).n).toBe(8);
  });
});

describe("the index is searchable in both scripts", () => {
  it("matches Arabic in its own column", async () => {
    insert(1, "the protective friend", "الله ولي الذين امنوا");
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'arabic_fold : (ولي)'`,
        )
      ).n,
    ).toBe(1);
  });

  it("keeps a column-scoped query out of the other columns", async () => {
    insert(1, "the protective friend", "الله ولي");
    expect(
      (
        await rows(
          `SELECT count(*) AS n FROM search_fts WHERE search_fts MATCH 'arabic_fold : (friend)'`,
        )
      ).n,
    ).toBe(0);
  });
});
