import { describe, expect, it } from "vitest";

import {
  COLLECTIONS,
  inCollection,
  type Collection,
} from "../app/lib/collection";
import {
  ALL_STUDY_TRACKS,
  inTrack,
  type StudyTrack,
  type TrackChoice,
} from "../app/lib/study-track";

/**
 * The library's two independent filters — "Everything / Books / Sessions"
 * and "Browse by track" — checked against every Collection x Track
 * combination, not just the ones anyone happened to click while testing by
 * hand.
 *
 * The fixture below is not arbitrary: it reproduces the exact shape of a real
 * bug (2026-08-29) where a Sessions-bucket item published with no
 * `study_track` in its meta.yml — content/Sessions/love-of-the-prophet —
 * vanished the instant any single track chip was pressed, while still
 * showing under "Everything"/"All tracks". That data has since been fixed
 * (the item now carries a track like every other unit), but an untracked
 * item is not an impossible state: nothing stops the next Sessions intake
 * from shipping without one, and when it does, this is what should still be
 * true of the filters rather than a fresh case of "I don't see it."
 */
type Unit = { bucket: string; studyTrack: string | null };

const UNITS: Unit[] = [
  { bucket: "Islamic", studyTrack: "theology" },
  { bucket: "Islamic", studyTrack: "shariah" },
  { bucket: "Islamic", studyTrack: "esoteric" },
  { bucket: "Sessions", studyTrack: "theology" },
  // The reproduction case: a session with no track at all.
  { bucket: "Sessions", studyTrack: null },
];

const shownUnder = (collection: Collection, track: TrackChoice): Unit[] =>
  UNITS.filter((u) => inCollection(u.bucket, collection)).filter((u) =>
    inTrack(u.studyTrack, track),
  );

describe("inCollection", () => {
  it("'all' shows every bucket, books and sessions alike", () => {
    for (const u of UNITS) expect(inCollection(u.bucket, "all")).toBe(true);
  });

  it("'books' shows every unnamed bucket and hides the two named ones", () => {
    expect(inCollection("Islamic", "books")).toBe(true);
    expect(inCollection("Technical", "books")).toBe(true);
    expect(inCollection("Fiction", "books")).toBe(true);
    expect(inCollection("Guides", "books")).toBe(true);
    expect(inCollection("Sessions", "books")).toBe(false);
    expect(inCollection("Audiobook", "books")).toBe(false);
  });

  it("'sessions' shows only the Sessions bucket", () => {
    expect(inCollection("Sessions", "sessions")).toBe(true);
    expect(inCollection("Islamic", "sessions")).toBe(false);
    // The split of 2026-09-01: an audiobook used to answer here, when both
    // spoken buckets shared one collection. It has its own now.
    expect(inCollection("Audiobook", "sessions")).toBe(false);
  });

  it("'audiobooks' shows only the Audiobook bucket", () => {
    expect(inCollection("Audiobook", "audiobooks")).toBe(true);
    expect(inCollection("Sessions", "audiobooks")).toBe(false);
    expect(inCollection("Islamic", "audiobooks")).toBe(false);
  });

  it("a bucket the taxonomy has not seen yet still lands with the books", () => {
    // Books are defined as NOT one of the named collections rather than as an
    // enumerated list, so a future bucket is reachable under "Books" from day
    // one rather than invisible under every filter until someone remembers to
    // add it here. The failure mode is silent: nobody reports a book they
    // cannot see.
    expect(inCollection("SomeFutureBucket", "books")).toBe(true);
    expect(inCollection("SomeFutureBucket", "sessions")).toBe(false);
    expect(inCollection("SomeFutureBucket", "audiobooks")).toBe(false);
  });
});

describe("inTrack", () => {
  it("'all' matches every track, including untracked content", () => {
    expect(inTrack("theology", "all")).toBe(true);
    expect(inTrack(null, "all")).toBe(true);
    expect(inTrack(undefined, "all")).toBe(true);
  });

  it("a specific track matches only that exact track", () => {
    expect(inTrack("theology", "theology")).toBe(true);
    expect(inTrack("shariah", "theology")).toBe(false);
  });

  it("untracked content matches no specific track — the reproduction case", () => {
    for (const track of ALL_STUDY_TRACKS) {
      expect(inTrack(null, track)).toBe(false);
      expect(inTrack(undefined, track)).toBe(false);
    }
  });
});

describe("every Collection x Track combination", () => {
  const ALL_TRACK_CHOICES: TrackChoice[] = ["all", ...ALL_STUDY_TRACKS];

  for (const collection of COLLECTIONS) {
    for (const track of ALL_TRACK_CHOICES) {
      it(`collection=${collection} track=${track} matches a hand-computed set`, () => {
        const expected = UNITS.filter((u) => {
          // Hand-computed from the BUCKETS, deliberately — the point of this
          // matrix is to check `inCollection` against an independent reading of
          // the rule, so it must not call the thing it is testing. Rewritten for
          // the three-way split of 2026-09-01; it previously asked only whether
          // a bucket was Sessions, which quietly made "audiobooks" mean "every
          // book" rather than failing.
          const named =
            u.bucket === "Sessions"
              ? "sessions"
              : u.bucket === "Audiobook"
                ? "audiobooks"
                : "books";
          const collectionOk = collection === "all" || named === collection;
          const trackOk = track === "all" || u.studyTrack === track;
          return collectionOk && trackOk;
        });
        expect(shownUnder(collection, track)).toEqual(expected);
      });
    }
  }

  it("'Everything' + 'All tracks' shows the untracked session — never a silent drop", () => {
    const shown = shownUnder("all", "all");
    expect(shown).toContainEqual({ bucket: "Sessions", studyTrack: null });
  });

  it("selecting any single track hides the untracked session", () => {
    // This is the documented, intentional half of the bug fix: an untracked
    // item disappearing under a specific track is not itself wrong — it is
    // the signal that the item needs classifying. What must never happen is
    // for it to also disappear under "Everything"/"All tracks", which is
    // covered above.
    for (const track of ALL_STUDY_TRACKS as StudyTrack[]) {
      const shown = shownUnder("all", track);
      expect(shown.some((u) => u.studyTrack === null)).toBe(false);
    }
  });
});
