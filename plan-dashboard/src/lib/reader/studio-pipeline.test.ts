/**
 * Regression test for classifyStatusBucket's lane split. Before this, EVERY
 * completed phase — book or Sessions — went through the book pipeline's own
 * PHASE_ORDER. A Sessions phase name is never in that list, so the lookup
 * always missed and rule 3 ("unknown phase proves real work") always fired:
 * a Sessions book that had done nothing but its first automated step still
 * showed as in-the-works. Neither shipped Sessions book was ever new enough
 * to expose it.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { classifyStatusBucket } from "./studio-pipeline";

describe("classifyStatusBucket — published status wins outright", () => {
  it("is published regardless of phase or lane", () => {
    assert.equal(classifyStatusBucket("published", "0a"), "published");
    assert.equal(
      classifyStatusBucket("published", "sessions-ingest", "sessions_lane"),
      "published",
    );
  });

  it("is up-next when nothing has completed yet", () => {
    assert.equal(classifyStatusBucket(undefined, null), "up-next");
    assert.equal(
      classifyStatusBucket(undefined, null, "sessions_lane"),
      "up-next",
    );
  });
});

describe("classifyStatusBucket — book pipeline lane (unchanged)", () => {
  it("buckets the automated ingest/refine phases as up-next", () => {
    assert.equal(classifyStatusBucket(undefined, "0a"), "up-next");
    assert.equal(classifyStatusBucket(undefined, "0b"), "up-next");
  });

  it("buckets anything past refine as in-the-works", () => {
    assert.equal(classifyStatusBucket(undefined, "0c"), "in-the-works");
    assert.equal(classifyStatusBucket(undefined, "finalize"), "in-the-works");
  });

  it("still treats an unrecognized phase as proof of real work", () => {
    assert.equal(
      classifyStatusBucket(undefined, "0book-render"),
      "in-the-works",
    );
  });
});

describe("classifyStatusBucket — Sessions lane, gated on pipeline_mode", () => {
  it("never falls through to the book pipeline's PHASE_ORDER", () => {
    // sessions-ingest and sessions-articulate are not book phases; if this
    // regresses to phaseIndex(), both come back -1 and both read in-the-works.
    assert.equal(
      classifyStatusBucket(undefined, "sessions-ingest", "sessions_lane"),
      "up-next",
    );
  });

  it("is up-next through the automated ingest + transcribe steps", () => {
    assert.equal(
      classifyStatusBucket(undefined, "sessions-ingest", "sessions_lane"),
      "up-next",
    );
    assert.equal(
      classifyStatusBucket(undefined, "sessions-transcribe", "sessions_lane"),
      "up-next",
    );
  });

  it("is in-the-works from articulation onward — real per-book authoring", () => {
    for (const phase of [
      "sessions-articulate",
      "sessions-preface",
      "sessions-apparatus",
    ]) {
      assert.equal(
        classifyStatusBucket(undefined, phase, "sessions_lane"),
        "in-the-works",
        phase,
      );
    }
  });

  it("a book classified without pipeline_mode still uses the book lane", () => {
    // sessions-articulate isn't a book phase either — absent the lane flag,
    // it must fall through to the book pipeline's "unknown phase" rule, not
    // be silently treated as a Sessions phase.
    assert.equal(
      classifyStatusBucket(undefined, "sessions-articulate"),
      "in-the-works",
    );
  });
});
