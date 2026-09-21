import { describe, expect, it } from "vitest";

import { chapterSignals } from "../app/lib/chapterSignals";
import type { Correction } from "../app/lib/corrections";

const chapters = [
  { anchorKey: "intro" },
  { anchorKey: "one" },
  { anchorKey: "two" },
];
const mark = (anchorKey: string, note: string | null = null) =>
  ({ anchorKey, note }) as never;
const bookmark = (anchorKey: string) => ({ anchorKey }) as never;
const fix = (anchorKey: string, status: Correction["status"]) =>
  ({ anchorKey, status }) as Correction;

describe("chapterSignals", () => {
  it("tells a highlight from a note by whether it carries text", () => {
    const s = chapterSignals(
      chapters,
      {
        annotations: [mark("one"), mark("one", "why"), mark("one", "   ")],
        bookmarks: [bookmark("one")],
      },
      null,
      null,
    );
    expect(s.get("one")).toMatchObject({
      highlights: 2,
      notes: 1,
      bookmarks: 1,
    });
    expect(s.get("two")).toMatchObject({
      highlights: 0,
      notes: 0,
      bookmarks: 0,
    });
  });

  it("counts corrections only when it is GIVEN them — a reader gets none", () => {
    const list = [
      fix("one", "open"),
      fix("one", "suggested"),
      fix("one", "accepted"),
    ];
    const mod = chapterSignals(
      chapters,
      { annotations: [], bookmarks: [] },
      list,
      null,
    );
    expect(mod.get("one")).toMatchObject({ open: 2, decided: 1 });
    const reader = chapterSignals(
      chapters,
      { annotations: [], bookmarks: [] },
      null,
      null,
    );
    expect(reader.get("one")).toMatchObject({ open: 0, decided: 0 });
  });

  it("derives reading state from position: earlier is done, the current one is part", () => {
    const at = { anchorKey: "one", fraction: 0.4, chaptersDone: 1 };
    const s = chapterSignals(
      chapters,
      { annotations: [], bookmarks: [] },
      null,
      at,
    );
    expect([
      s.get("intro")!.state,
      s.get("one")!.state,
      s.get("two")!.state,
    ]).toEqual(["done", "part", "none"]);
  });

  it("shows nothing as read when there is no progress at all", () => {
    const s = chapterSignals(
      chapters,
      { annotations: [], bookmarks: [] },
      null,
      null,
    );
    expect([...s.values()].every((x) => x.state === "none")).toBe(true);
  });

  it("ignores marks in a chapter the book no longer has", () => {
    const s = chapterSignals(
      chapters,
      { annotations: [mark("gone")], bookmarks: [] },
      null,
      null,
    );
    expect(s.has("gone")).toBe(false);
  });
});
