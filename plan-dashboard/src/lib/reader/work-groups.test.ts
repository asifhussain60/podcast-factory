/**
 * The TS leg of the work-group manifest mirror.
 *
 * Every case comes from the SHARED fixture, which the Python leg
 * (scripts/podcast/tests/test_sync_listener_work_groups.py) loads too. That is
 * the point: the two implementations answer "are these books one work?" for the
 * two surfaces a reader actually looks at, and when they disagree the symptom is
 * silent — a set stacked on one site and scattered on the other, with nothing
 * anywhere saying why. That is the bug this pair was born from.
 *
 * The non-fixture cases below are about THIS leg only: the filesystem scan and
 * the volume index, neither of which the Python side has an equivalent for.
 */
import { deepStrictEqual, strictEqual } from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { parseWorkGroupManifest, volumeIndex } from "./work-groups";

const FIXTURES = join(
  fileURLToPath(import.meta.url),
  "..",
  "..",
  "..",
  "..",
  "scripts",
  "lib",
  "work-groups.fixtures.json",
);

interface Fixture {
  cases: {
    name: string;
    defaultSlug: string;
    in: unknown;
    out: unknown;
  }[];
}

const fixture: Fixture = JSON.parse(readFileSync(FIXTURES, "utf-8"));

describe("parseWorkGroupManifest — the shared fixture", () => {
  // A guard on the guard: an empty or truncated fixture file would make every
  // assertion below vacuous while the suite still reported success.
  it("has cases to run", () => {
    strictEqual(fixture.cases.length > 5, true);
  });

  for (const c of fixture.cases) {
    it(c.name, () => {
      deepStrictEqual(parseWorkGroupManifest(c.in, c.defaultSlug), c.out);
    });
  }
});

describe("parseWorkGroupManifest — inputs a YAML file can really produce", () => {
  it("refuses a document that parsed to a list", () => {
    strictEqual(parseWorkGroupManifest([{ slug: "a" }], "w"), null);
  });

  it("refuses an empty document", () => {
    // `yaml.parse("")` is null, which is what an emptied declaration looks like.
    strictEqual(parseWorkGroupManifest(null, "w"), null);
  });

  it("refuses a scalar", () => {
    strictEqual(parseWorkGroupManifest("mukhtasar", "w"), null);
  });
});

describe("volumeIndex", () => {
  const group = {
    workSlug: "w",
    title: "W",
    bucket: "Islamic",
    volumes: [
      { slug: "a", order: 1 },
      { slug: "b", order: 2 },
    ],
  };

  it("maps each volume to its work, title and order", () => {
    const index = volumeIndex([group]);
    deepStrictEqual(index.get("a"), { workSlug: "w", title: "W", order: 1 });
    deepStrictEqual(index.get("b"), { workSlug: "w", title: "W", order: 2 });
  });

  it("leaves a book that is in no group out of the index entirely", () => {
    // The shelf asks "is this a volume?" of every book it draws, so the answer
    // for a standalone one has to be a plain miss rather than a default entry.
    strictEqual(volumeIndex([group]).has("standalone"), false);
  });

  it("gives a volume claimed by two declarations to the first", () => {
    // Two manifests naming one book is a mistake somebody has to fix. Silently
    // handing it to whichever file sorted last would hide it instead.
    const other = { ...group, workSlug: "other", title: "Other" };
    const index = volumeIndex([group, other]);
    strictEqual(index.get("a")?.workSlug, "w");
  });

  it("is empty when nothing is declared", () => {
    strictEqual(volumeIndex([]).size, 0);
  });
});
