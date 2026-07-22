/**
 * articulation.test.ts — the Composer's freeze-machine-text warning map.
 *
 * RCA-001 AI-3: a Composer save of a chapter whose base never passed
 * articulation freezes calqued machine text as "human-authored" forever. These
 * tests pin the classification that drives the advisory warning — most
 * importantly that the exact incident shapes (report says skipped/reverted;
 * composer-edit taken before articulation succeeded) DO warn, and that a book
 * without a fluency report does not warn at all.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { articulationWarningsFrom } from "./articulation.ts";

const KEYS = ["on knowledge", "on patience"];

function report(chapters: object[]): unknown {
  return { schema: "podcast.book-fluency/v3", chapters };
}

test("no fluency report → no warnings (the contract does not apply)", () => {
  assert.deepEqual(articulationWarningsFrom(null, KEYS), {});
  assert.deepEqual(articulationWarningsFrom({}, KEYS), {});
  assert.deepEqual(articulationWarningsFrom({ chapters: "bogus" }, KEYS), {});
});

test("a kept adapted chapter is safe; skipped and reverted warn", () => {
  const warnings = articulationWarningsFrom(
    report([
      { title: "1. On Knowledge", status: "adapted" },
      { title: "2. On Patience", status: "skipped" },
    ]),
    KEYS,
  );
  assert.equal(warnings["on knowledge"], undefined);
  assert.match(warnings["on patience"], /skipped/);

  const reverted = articulationWarningsFrom(
    report([{ title: "On Patience", status: "reverted" }]),
    ["on patience"],
  );
  assert.match(reverted["on patience"], /reverted/);
});

test("partial keeps warning — part of the chapter is still the machine base", () => {
  const warnings = articulationWarningsFrom(
    report([{ title: "On Patience", status: "partial" }]),
    ["on patience"],
  );
  assert.match(warnings["on patience"], /part/);
});

test("composer-edit is judged by what the pass said before the takeover", () => {
  const warnings = articulationWarningsFrom(
    report([
      // Frozen AFTER a kept adaptation — the human took over articulated prose.
      {
        title: "On Knowledge",
        status: "composer-edit",
        superseded_status: "adapted",
      },
      // Frozen BEFORE articulation ever succeeded — the RCA-001 incident shape.
      { title: "On Patience", status: "composer-edit" },
    ]),
    KEYS,
  );
  assert.equal(warnings["on knowledge"], undefined);
  assert.match(warnings["on patience"], /before articulation/);
});

test("a chapter the report has never heard of warns as unknown, not safe", () => {
  const warnings = articulationWarningsFrom(
    report([{ title: "On Knowledge", status: "adapted" }]),
    KEYS,
  );
  assert.match(warnings["on patience"], /no record/);
});

test("titles map through anchorKey — numbering and case cannot orphan a record", () => {
  const warnings = articulationWarningsFrom(
    report([{ title: "2. ON PATIENCE", status: "reverted" }]),
    ["on patience"],
  );
  assert.match(warnings["on patience"], /reverted/);
});
