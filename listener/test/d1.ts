import { DatabaseSync } from "node:sqlite";
import { readdirSync, readFileSync } from "node:fs";

/**
 * A minimal D1Database over node:sqlite, so the entitlement tests exercise the
 * REAL SQL against a real SQLite engine rather than a hand-rolled fake.
 *
 * That matters more than it sounds: the resolver's correctness lives entirely in
 * one SQL expression, and a mock that returns canned rows would test the mock.
 * This also runs the actual migrations, so a CHECK constraint or trigger that
 * would reject a row in production rejects it here too.
 *
 * Only the surface access.server.ts uses is implemented — prepare/bind/first/
 * all/run and batch. Anything else throws rather than pretending.
 */
export interface TestDb {
  db: D1Database;
  exec(sql: string): void;
  close(): void;
}

/**
 * Every migration, in the order wrangler applies them.
 *
 * Read from the directory rather than listed, because a list is a second place
 * to remember. Four test files each carried their own subset, and the day a
 * migration added a column the queries needed, every one of them failed with
 * `no such column` — a message about the fixture, not about the code under test.
 * The schema a test runs against should be the schema production runs against,
 * and there is no case in this suite where a partial one was the point.
 */
function allMigrations(): string[] {
  const dir = new URL("../migrations/", import.meta.url);
  return (
    readdirSync(dir)
      .filter((name) => name.endsWith(".sql"))
      // SEEDS are excluded, and only seeds. A migration that creates a table
      // describes the shape production has and every test wants it; a migration
      // that INSERTS rows describes what production happens to contain, and a test
      // builds its own — `0003_seed_catalog` puts a row in `content_unit` for
      // every book in the repo, which collides with the fixtures the marks tests
      // insert under the same slugs.
      .filter((name) => !name.includes("_seed"))
      .sort()
  );
}

export function createTestDb(migrations?: string[]): TestDb {
  const sqlite = new DatabaseSync(":memory:");

  for (const name of migrations?.map((m) => `${m}.sql`) ?? allMigrations()) {
    const sql = readFileSync(
      new URL(`../migrations/${name}`, import.meta.url),
      "utf8",
    );
    sqlite.exec(sql);
  }

  const prepare = (sql: string): D1PreparedStatement => {
    let bound: unknown[] = [];

    const stmt: Partial<D1PreparedStatement> = {
      bind(...values: unknown[]) {
        bound = values;
        return stmt as D1PreparedStatement;
      },
      async first<T>(): Promise<T | null> {
        const row = sqlite.prepare(sql).get(...(bound as never[]));
        return (row as T | undefined) ?? null;
      },
      async all<T>() {
        const results = sqlite.prepare(sql).all(...(bound as never[])) as T[];
        return { results, success: true, meta: {} } as never;
      },
      async run() {
        sqlite.prepare(sql).run(...(bound as never[]));
        return { success: true, meta: {} } as never;
      },
    };

    return stmt as D1PreparedStatement;
  };

  const db = {
    prepare,
    async batch(statements: D1PreparedStatement[]) {
      // D1 batches are atomic. Mirroring that here means a test can catch a
      // constraint violation leaving half a change behind.
      sqlite.exec("BEGIN");
      try {
        const out = [];
        for (const s of statements) out.push(await s.run());
        sqlite.exec("COMMIT");
        return out as never;
      } catch (error) {
        sqlite.exec("ROLLBACK");
        throw error;
      }
    },
  } as unknown as D1Database;

  return {
    db,
    exec: (sql: string) => sqlite.exec(sql),
    close: () => sqlite.close(),
  };
}
