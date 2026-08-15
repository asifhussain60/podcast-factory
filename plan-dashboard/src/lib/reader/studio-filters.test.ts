/**
 * The rule these tests exist for: A CHIP'S NUMBER IS WHAT PRESSING IT SHOWS.
 *
 * It has been broken twice, both times in ways that looked right in the only
 * state anyone checked — every facet on "All". So the cases below deliberately
 * assert the CROSS PRODUCT, not one facet at a time.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ALL,
  FACETS,
  contextualCount,
  isWideOpen,
  matches,
  satisfies,
  shownCount,
  wideOpen,
  type Chosen,
  type FilterUnit,
} from "./studio-filters";

/** A shelf shaped like the real one: two buckets, three statuses, five tracks,
 *  and one series deck that carries `always` instead of a status. */
const SHELF: FilterUnit[] = [
  { bucket: "Islamic", status: "published", track: "theology" },
  { bucket: "Islamic", status: "published", track: "esoteric" },
  { bucket: "Islamic", status: "in-the-works", track: "shariah" },
  { bucket: "Islamic", status: "in-the-works", track: "shariah" },
  { bucket: "Islamic", status: "up-next", track: "history" },
  { bucket: "Islamic", status: "up-next", track: "reality" },
  { bucket: "Islamic", status: "always", track: "esoteric" }, // series deck
  { bucket: "Sessions", status: "published", track: "theology" },
  { bucket: "Sessions", status: "in-the-works" }, // no track recorded
];

const pick = (over: Partial<Chosen>): Chosen => ({ ...wideOpen(), ...over });

describe("studio filters — a facet on its own", () => {
  it("shows everything when nothing is chosen", () => {
    assert.equal(shownCount(SHELF, wideOpen()), SHELF.length);
    assert.ok(isWideOpen(wideOpen()));
  });

  it("narrows to one bucket", () => {
    assert.equal(shownCount(SHELF, pick({ bucket: "Sessions" })), 2);
  });

  it("treats a unit with no track as matching no track but every 'all'", () => {
    const untracked = SHELF[8];
    assert.ok(satisfies(untracked, "track", ALL));
    assert.equal(satisfies(untracked, "track", "theology"), false);
  });
});

describe("studio filters — a series deck is never hidden by status", () => {
  // A deck has no single status of its own; its volumes each carry theirs. If
  // this regresses, choosing any status makes the deck vanish with no way back.
  const deck = SHELF[6];

  it("satisfies every status value", () => {
    for (const status of ["published", "in-the-works", "up-next"]) {
      assert.ok(satisfies(deck, "status", status), status);
    }
  });

  it("is still filtered by its bucket and its track", () => {
    assert.equal(satisfies(deck, "bucket", "Sessions"), false);
    assert.equal(satisfies(deck, "track", "theology"), false);
    assert.ok(satisfies(deck, "track", "esoteric"));
  });

  it("appears under every status filter", () => {
    for (const status of ["published", "in-the-works", "up-next"]) {
      assert.ok(matches(deck, pick({ status })), status);
    }
  });
});

describe("studio filters — the promise: count equals outcome", () => {
  // THE regression test. Every chip, in every facet, from a wide-open state AND
  // with each of the other facets pinned — the configuration that hid the bug.
  const VALUES: Record<string, string[]> = {
    bucket: ["Islamic", "Sessions"],
    status: ["published", "in-the-works", "up-next"],
    track: ["theology", "esoteric", "shariah", "history", "reality"],
  };

  const contexts: Chosen[] = [
    wideOpen(),
    pick({ status: "published" }),
    pick({ bucket: "Islamic" }),
    pick({ track: "esoteric" }),
    pick({ bucket: "Islamic", status: "published" }),
  ];

  for (const context of contexts) {
    const label = FACETS.filter((f) => context[f] !== ALL)
      .map((f) => `${f}=${context[f]}`)
      .join(" ");
    for (const facet of FACETS) {
      for (const value of VALUES[facet]) {
        it(`${facet}=${value} promises what it shows${label ? ` (with ${label})` : ""}`, () => {
          const promised = contextualCount(SHELF, context, facet, value);
          const actual = shownCount(SHELF, { ...context, [facet]: value });
          assert.equal(promised, actual);
        });
      }
    }
  }
});

describe("studio filters — the specific failures that shipped", () => {
  it("Shariah reports 0, not 2, once Published is chosen", () => {
    // The exact defect Asif hit: no Shariah book is published, but the chip
    // said 2 because it was counted against the whole shelf in isolation.
    const withPublished = pick({ status: "published" });
    assert.equal(contextualCount(SHELF, withPublished, "track", "shariah"), 0);
    assert.equal(
      shownCount(SHELF, { ...withPublished, track: "shariah" }),
      0,
      "and pressing it really does show nothing, which is why 0 is the honest number",
    );
  });

  it("a track count is unaffected by the facet it belongs to", () => {
    // Including the chip's own facet in its test would make every unchosen
    // chip in a narrowed group report zero.
    const withTheology = pick({ track: "theology" });
    assert.equal(contextualCount(SHELF, withTheology, "track", "esoteric"), 2);
  });

  it("counts a series deck once, not once per volume", () => {
    // The units this operates on are what the shelf DRAWS. A deck standing in
    // for six volumes contributes one, which is what its chip's number means.
    assert.equal(contextualCount(SHELF, wideOpen(), "track", "esoteric"), 2);
  });
});
