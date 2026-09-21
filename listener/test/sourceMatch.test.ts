import { describe, expect, it } from "vitest";

import { locateSpan } from "../app/lib/sourceMatch";

const SOURCE =
  "When the shaykh learned of his student's difficulty, the shaykh wrote to his student that patience " +
  "in seeking is the first door, and that no one enters the second except after passing through it.";

describe("locating a quote in the extracted source", () => {
  it("finds an exact passage", () => {
    const span = locateSpan(SOURCE, "patience in seeking is the first door")!;
    expect(SOURCE.slice(span.start, span.end)).toBe(
      "patience in seeking is the first door",
    );
  });

  it("finds a passage that differs by a word or two, which is why a correction exists", () => {
    const span = locateSpan(
      SOURCE,
      "the teacher wrote to his student that patience",
    )!;
    expect(SOURCE.slice(span.start, span.end)).toContain(
      "wrote to his student that patience",
    );
  });

  it("says NO MATCH rather than highlighting the wrong sentence", () => {
    expect(
      locateSpan(SOURCE, "completely unrelated words about weather today"),
    ).toBeNull();
  });

  it("gives up on a single word, and on a source shorter than the quote", () => {
    expect(locateSpan(SOURCE, "patience")).toBeNull();
    expect(
      locateSpan("short text", "a much longer quote than the source itself"),
    ).toBeNull();
  });

  it("ignores case and punctuation", () => {
    const span = locateSpan(SOURCE, "The SHAYKH, wrote to his student!")!;
    expect(SOURCE.slice(span.start, span.end).toLowerCase()).toContain(
      "shaykh wrote to his student",
    );
  });
});
