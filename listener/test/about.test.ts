import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { ALL_SECTIONS, FAQ, RELEASES, SECTIONS } from "../app/lib/about";

/**
 * The About page's content.
 *
 * A page of hand-written prose cannot be tested for being GOOD, and this does not
 * try. It pins the three things that are structural — the shape the page renders
 * from, the promise it must not make, and the one date format the release list is
 * read by — and leaves the wording to whoever writes it.
 */

describe("what the About page says", () => {
  it("gives every section a unique id, a title and a blurb", () => {
    // The id is the anchor, the filter value and the React key at once. Two
    // sections sharing one would light both chips and jump to the first.
    const ids = ALL_SECTIONS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);

    for (const s of ALL_SECTIONS) {
      expect(s.id, "an id must be URL-safe — it is an anchor").toMatch(/^[a-z][a-z0-9-]*$/);
      expect(s.title.trim()).not.toBe("");
      expect(s.blurb.trim(), `${s.id} has no blurb — it is the answer for a skimmer`).not.toBe("");
      expect(s.entries.length, `${s.id} has no entries`).toBeGreaterThan(0);
    }
  });

  it("gives every entry a question and at least one paragraph of answer", () => {
    for (const s of ALL_SECTIONS) {
      for (const e of s.entries) {
        expect(e.q.trim(), `an entry in ${s.id} has no question`).not.toBe("");
        expect(e.a.length, `"${e.q}" has no answer`).toBeGreaterThan(0);
        for (const p of e.a) expect(p.trim(), `"${e.q}" has an empty paragraph`).not.toBe("");
      }
    }
  });

  it("has no two entries with the same question", () => {
    // The question is the React key for its `details`, within and across sections
    // once search flattens them.
    const all = ALL_SECTIONS.flatMap((s) => s.entries.map((e) => e.q));
    expect(new Set(all).size).toBe(all.length);
  });

  it("carries no markup — the Worker has no renderer for it", () => {
    // Chapter prose is rendered to HTML at publish time precisely so that the
    // Worker holds no markdown implementation. Text here goes into a `<p>` as-is,
    // so a stray `**bold**` or `<em>` would print literally.
    for (const s of ALL_SECTIONS) {
      for (const p of [s.blurb, ...s.entries.flatMap((e) => [e.q, ...e.a])]) {
        expect(p, `markup in "${p.slice(0, 40)}…"`).not.toMatch(/<[a-z/]|\*\*|\[.+\]\(/i);
      }
    }
  });

  it("keeps the FAQ last, where a reader jumps to it", () => {
    expect(ALL_SECTIONS.at(-1)).toBe(FAQ);
    expect(ALL_SECTIONS.slice(0, -1)).toEqual(SECTIONS);
  });

  /**
   * The one thing this page must never describe.
   *
   * The Scholar Companion is readable by a single account — the gate is inside
   * the query in companion.server.ts, so no row and no grant can widen it. An
   * entry describing it would be a promise the site keeps for nobody reading this
   * page, and the page is what a new reader is pointed at.
   */
  it("never promises the Companion, which one account can see", () => {
    const everything = JSON.stringify(ALL_SECTIONS).toLowerCase();
    expect(everything).not.toContain("companion");
    expect(everything).not.toContain("scholar");
  });

  it("names no book, so the page cannot leak what the library holds", () => {
    // It reads nothing from the database by design. This catches the other route
    // in — somebody writing a title into an example.
    const everything = JSON.stringify(ALL_SECTIONS).toLowerCase();
    for (const title of ["ayyuha", "al-walad", "degrees of excellence", "master and the disciple"]) {
      expect(everything, `the About page names "${title}"`).not.toContain(title);
    }
  });
});

describe("the release notes", () => {
  it("dates every entry as YYYY-MM-DD", () => {
    // Rendered into `<time dateTime>` and split by hand into a long date. Any
    // other shape prints the raw string.
    for (const r of RELEASES) {
      expect(r.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(r.items.length, `${r.date} has no items`).toBeGreaterThan(0);
      for (const item of r.items) expect(item.trim()).not.toBe("");
    }
  });

  it("runs newest first", () => {
    const dates = RELEASES.map((r) => r.date);
    expect(dates).toEqual([...dates].sort().reverse());
  });

  it("has no repeated date", () => {
    // The date is the list key, and two entries for one day is two answers to
    // what changed that day.
    const dates = RELEASES.map((r) => r.date);
    expect(new Set(dates).size).toBe(dates.length);
  });
});

describe("the deploy notices when this file falls behind", () => {
  /**
   * The check in scripts/podcast/deploy_listener.sh names this file by path. A
   * rename would leave it comparing a file that does not exist, which it reports
   * — but it would report it on every deploy forever, and a warning that is
   * always on is a warning nobody reads.
   */
  it("is still at the path the deploy script watches", () => {
    const script = readFileSync(
      new URL("../../scripts/podcast/deploy_listener.sh", import.meta.url),
      "utf8",
    );
    expect(script).toContain('ABOUT="listener/app/lib/about.ts"');
  });

  it("never blocks the deploy", () => {
    // publish_to_library.py runs that script at the end of every book publish, so
    // a stale help page must not be able to stop a finished book from shipping.
    const script = readFileSync(
      new URL("../../scripts/podcast/deploy_listener.sh", import.meta.url),
      "utf8",
    );
    // Bounded by the NEXT step, not by a landmark further down the file. It
    // used to end at "--- The Worker", and on 2026-08-05 the branch-sweep
    // commit inserted a "Production branch" step in between -- one that MUST
    // `die` when main will not merge. The slice then spanned both steps and
    // this test failed over a `die` belonging to a step it does not govern,
    // while the step it names still ended with "Deploying anyway -- this never
    // blocks." A gate that fails over a rule it is not measuring is worse than
    // no gate; ending at the next `step "` makes it immune to whatever is
    // inserted after this one.
    const from = script.indexOf('step "What\'s new"');
    const next = script.indexOf('step "', from + 1);
    const step = script.slice(from, next === -1 ? script.indexOf("--- The Worker") : next);
    expect(step).not.toMatch(/\bdie\b|\bexit 1\b/);
  });
});
