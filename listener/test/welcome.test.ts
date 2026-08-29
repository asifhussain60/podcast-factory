import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { loader } from "../app/routes/welcome";
import { cloudflare } from "../app/context";
import { session, type Viewer } from "../app/middleware/session";
import { invite } from "../app/server/people.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * The chooser only appears when there is something to choose BETWEEN.
 *
 * This is the one rule on that page that can strand somebody. The shelf draws
 * its collection control only when a reader's library actually mixes books and
 * sessions, so a reader holding books alone who followed a Sessions tile would
 * land on an empty grid with no visible control to get back out of it. The page
 * prevents that by never being shown to them at all.
 *
 * It is pinned here rather than in the browser sweep because `npm run smoke`
 * has no way to say "expect a redirect to `/`" — a 302 there means "denied, sent
 * to sign-in" — and because Chromium drops a manually-set `Cookie` header when
 * following a redirect, so the sweep's second hop arrives signed out whatever
 * the app did. See the note beside `/welcome` in scripts/routes.mjs.
 */

const NOW = "2026-08-29T12:00:00Z";
const ADMIN = "asifhussain60@gmail.com";
const READER = "reader@example.com";

let t: TestDb;

beforeEach(async () => {
  t = createTestDb();
  await invite(t.db, READER, ADMIN, {}, NOW);
});

afterEach(() => t.close());

const viewer = (): Viewer => ({
  email: READER,
  rawEmail: READER,
  name: "A Reader",
  image: null,
  isAdmin: false,
});

/**
 * Only the two entries the loader reads. A fuller stand-in would be a second
 * description of the request context, and this test is about neither.
 */
function args() {
  const context = {
    get(key: unknown) {
      if (key === cloudflare) return { env: { DB: t.db } };
      if (key === session) return { viewer: viewer() };
      throw new Error("the welcome loader asked for something unexpected");
    },
  };
  return { context } as unknown as Parameters<typeof loader>[0];
}

/**
 * Publish some units, open to everyone, so `visibleUnits` returns them for an
 * invited reader holding no grants of their own. Written as SQL rather than
 * through `setOpenToAll` because this test is about the chooser's rule, not
 * about how a privilege bit is set — and the entitlement resolver is what turns
 * these rows into what the loader counts either way.
 */
function publish(rows: { slug: string; bucket: string }[]) {
  if (rows.length === 0) return;
  t.exec(`
    INSERT INTO content_unit
      (slug, bucket, title, kind, work_slug, sort_order, status, open_to_all)
    VALUES ${rows
      .map(
        (r, i) =>
          `('${r.slug}', '${r.bucket}', '${r.slug}', 'book', NULL, ${(i + 1) * 10}, 'published', 1)`,
      )
      .join(", ")};
  `);
}

/** The loader redirects by throwing, so a Response is the outcome to inspect. */
async function run(): Promise<Response | Awaited<ReturnType<typeof loader>>> {
  try {
    return await loader(args());
  } catch (thrown) {
    if (thrown instanceof Response) return thrown;
    throw thrown;
  }
}

describe("a library holding both kinds", () => {
  it("renders the chooser, with a count for each tile", async () => {
    publish([
      { slug: "ayyuhal-walad", bucket: "Islamic" },
      { slug: "kitab-al-riyad", bucket: "Islamic" },
      { slug: "surah-al-fateha", bucket: "Sessions" },
    ]);

    const result = await run();

    expect(result).not.toBeInstanceOf(Response);
    expect(result).toMatchObject({ books: 2, sessions: 1 });
  });
});

describe("a library holding one kind", () => {
  it("sends a books-only reader straight to the shelf", async () => {
    publish([{ slug: "ayyuhal-walad", bucket: "Islamic" }]);

    const result = await run();

    expect(result).toBeInstanceOf(Response);
    expect((result as Response).headers.get("location")).toBe("/library");
  });

  it("sends a sessions-only reader straight to the shelf", async () => {
    publish([{ slug: "surah-al-fateha", bucket: "Sessions" }]);

    const result = await run();

    expect(result).toBeInstanceOf(Response);
    expect((result as Response).headers.get("location")).toBe("/library");
  });

  // The control: an empty library is one collection short like any other, and
  // must bounce for that reason rather than rendering a chooser with two zeroes.
  it("sends a reader holding nothing straight to the shelf", async () => {
    publish([]);

    const result = await run();

    expect(result).toBeInstanceOf(Response);
    expect((result as Response).headers.get("location")).toBe("/library");
  });
});
