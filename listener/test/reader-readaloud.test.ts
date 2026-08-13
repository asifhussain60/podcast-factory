import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  readAlongBlockIndex,
  readAlongTargetScrollY,
} from "../app/routes/book.$slug.read.$chapter";
import type { Cue } from "../app/components/player/Transcript";

const cues: Cue[] = [
  { startS: 0, endS: 10, text: "First paragraph", speaker: null, blockIndex: 0 },
  { startS: 12, endS: 20, text: "Second paragraph", speaker: null, blockIndex: 1 },
  { startS: 24, endS: 32, text: "Fourth visible block", speaker: null, blockIndex: 3 },
];

const css = readFileSync(
  new URL("../app/styles/podcast-factory.css", import.meta.url),
  "utf8",
);

describe("chapter read-aloud follow-along", () => {
  it("does not highlight anything until this chapter is the active audio", () => {
    expect(readAlongBlockIndex(false, cues, 5)).toBe(-1);
    expect(readAlongBlockIndex(true, null, 5)).toBe(-1);
    expect(readAlongBlockIndex(true, [], 5)).toBe(-1);
  });

  it("maps the current audio position to the narrated chapter block", () => {
    expect(readAlongBlockIndex(true, cues, 0)).toBe(0);
    expect(readAlongBlockIndex(true, cues, 15)).toBe(1);
    expect(readAlongBlockIndex(true, cues, 28)).toBe(3);
  });

  it("keeps the previous paragraph highlighted through a spoken pause", () => {
    expect(readAlongBlockIndex(true, cues, 11)).toBe(0);
    expect(readAlongBlockIndex(true, cues, 23)).toBe(1);
  });

  it("centers the active paragraph inside the visible viewport above the player", () => {
    expect(
      readAlongTargetScrollY({
        rect: { top: 500, height: 160 },
        scrollY: 1_000,
        viewportHeight: 900,
        playerHeight: 140,
      }),
    ).toBe(1_200);
  });

  it("never asks the page to scroll before the top", () => {
    expect(
      readAlongTargetScrollY({
        rect: { top: 40, height: 120 },
        scrollY: 0,
        viewportHeight: 700,
        playerHeight: 120,
      }),
    ).toBe(0);
  });

  it("styles the active paragraph as a visible read-along target", () => {
    const rule = /\.pf-chapter-body > \.pf-read-aloud \{(?<body>[^}]+)\}/.exec(
      css,
    )?.groups?.body;

    expect(rule).toContain("padding:");
    expect(rule).toContain("border: 1px solid");
    expect(rule).toContain("background:");
    expect(rule).toContain("box-shadow:");
    expect(rule).toContain("scroll-margin-block:");
  });
});
