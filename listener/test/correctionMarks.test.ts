import { describe, expect, it } from "vitest";

import {
  correctionAt,
  needsUnderline,
} from "../app/components/reader/useCorrectionMarks";
import type { Status } from "../app/lib/corrections";

const ALL: Status[] = ["suggested", "open", "accepted", "applied", "dismissed"];

describe("needsUnderline", () => {
  it("underlines only what is still waiting for a decision", () => {
    expect(ALL.filter(needsUnderline)).toEqual(["suggested", "open"]);
  });

  it("comes off the moment an admin accepts or dismisses it — not on the next republish", () => {
    expect(needsUnderline("accepted")).toBe(false);
    expect(needsUnderline("dismissed")).toBe(false);
    expect(needsUnderline("applied")).toBe(false);
  });
});

/** A rectangle, shaped enough to stand in for `Range.getClientRects()` in a test with no DOM. */
const rect = (left: number, top: number, right: number, bottom: number) =>
  ({ left, top, right, bottom }) as DOMRect;
const rangeAt = (id: string, ...rects: DOMRect[]) => ({
  id,
  range: { getClientRects: () => rects } as unknown as Range,
});

describe("correctionAt", () => {
  it("finds the correction whose painted rectangle contains the click", () => {
    const marked = [
      rangeAt("a", rect(0, 0, 50, 20)),
      rangeAt("b", rect(0, 20, 50, 40)),
    ];
    expect(correctionAt(10, 10, marked)).toBe("a");
    expect(correctionAt(10, 30, marked)).toBe("b");
  });

  it("answers nothing for a click between two lines a wrapped passage spans", () => {
    // Two rects for ONE correction that wraps onto a second line, with a real gap between them —
    // exactly what getBoundingClientRect() would collapse into one box a click in the gap falls
    // inside of. getClientRects() keeps them separate, and a click strictly between them hits
    // neither.
    const marked = [rangeAt("a", rect(0, 0, 200, 20), rect(0, 40, 80, 60))];
    expect(correctionAt(10, 30, marked)).toBeNull();
    expect(correctionAt(10, 10, marked)).toBe("a");
    expect(correctionAt(10, 50, marked)).toBe("a");
  });

  it("is null when nothing is painted there", () => {
    expect(
      correctionAt(500, 500, [rangeAt("a", rect(0, 0, 10, 10))]),
    ).toBeNull();
  });
});
