import { describe, expect, it } from "vitest";

import { needsUnderline } from "../app/components/reader/useCorrectionMarks";
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
