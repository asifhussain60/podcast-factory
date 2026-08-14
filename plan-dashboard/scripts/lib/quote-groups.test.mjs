/**
 * quote-groups.test.mjs — pins collectGroupRuns against its browser mirror.
 *
 * TWO implementations answer "which blocks merge into one card": the real
 * export in quote-groups.mjs (imported directly by book-html.mjs, the PDF and
 * the Composer's Read view) and a copy-mirrored local function of the same
 * name in src/lib/reader/markdown.ts (client-bundled, cannot import the .mjs).
 * Both are pinned against ONE shared fixture file here, closing a gap that
 * predates this feature: nothing pinned book-html.mjs against markdown.ts for
 * anything they share until this file existed.
 *
 * Drift here is silent: the browser Read view would merge a run of quote
 * cards the PDF renders separately, or the reverse.
 *
 * Run: node --test plan-dashboard/scripts/lib/quote-groups.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  collectGroupRuns,
  writeQuoteGroup,
  readQuoteGroups,
} from "./quote-groups.mjs";
import { collectGroupRuns as readerImpl } from "../../src/lib/reader/markdown.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(
  readFileSync(join(HERE, "quote-groups.fixtures.json"), "utf8"),
);

test("quote-groups.mjs matches the shared fixtures", () => {
  assert.ok(cases.length > 0, "fixture file is empty");
  for (const { blocks, runOf, why } of cases) {
    assert.deepEqual(collectGroupRuns(blocks), runOf, why);
  }
});

test("the reader's copy matches the shared fixtures", () => {
  for (const { blocks, runOf, why } of cases) {
    assert.deepEqual(readerImpl(blocks), runOf, why);
  }
});

test("writeQuoteGroup round-trips through a real temp book dir", async () => {
  const os = await import("node:os");
  const fs = await import("node:fs");
  const path = await import("node:path");
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "quote-groups-test-"));
  try {
    writeQuoteGroup(tmp, "chapter one", "first line of quote", "g1", "quote");
    writeQuoteGroup(tmp, "chapter one", "the tight gloss line", "g1", "gloss");
    const read = readQuoteGroups(tmp);
    assert.deepEqual(read, {
      "chapter one": {
        "first line of quote": { group: "g1", type: "quote" },
        "the tight gloss line": { group: "g1", type: "gloss" },
      },
    });
    // Clearing one member (group: "") deletes it and preserves the other.
    writeQuoteGroup(tmp, "chapter one", "first line of quote", "", "quote");
    const cleared = readQuoteGroups(tmp);
    assert.deepEqual(cleared, {
      "chapter one": {
        "the tight gloss line": { group: "g1", type: "gloss" },
      },
    });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
