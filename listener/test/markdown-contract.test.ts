import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * The build-time dependency on the admin site, pinned. All three of it.
 *
 * `renderMarkdown` in plan-dashboard/src/lib/reader/markdown.ts is what turns
 * book prose into HTML for BOTH the printed edition and this site. That is the
 * whole reason the Listener calls it rather than parsing markdown itself — the
 * page and the PDF cannot then disagree about the same paragraph. Two more
 * joined it when the Scholar Companion reached the reader:
 *
 *   cardMarkdownToHtml     a note's body, for the same reason
 *   sectionKeyFromHeading  the key a chapter's notes are FILED under, which is
 *                          NOT `anchor_key` — it keeps the heading's ordinal
 *
 * The risk they create is silent: someone improves the renderer for the print
 * side, the class names shift, and §7 of app/styles/podcast-factory.css — which
 * styles by those exact class names — stops matching. Nothing fails; Arabic
 * quotations simply stop being centred, or an editorial aside starts rendering
 * as display scripture. The key rule fails even more quietly: it moves by one
 * character and every companion note in the library is filed against a chapter
 * that no longer claims it, so the panel is simply empty and nothing says why.
 * This test turns both into a failing build.
 *
 * A changed fixture is not automatically a bug. It means one of the three
 * contracts moved, and whatever depends on it has to move in the same commit.
 */

const INPUT = new URL("./fixtures/markdown-input.json", import.meta.url);
const EXPECTED = new URL("./fixtures/markdown-expected.json", import.meta.url);

interface Rendered {
  chapters: { anchor_key: string; html: string; section_key?: string }[];
  cards: { id: string; html: string }[];
}

const rendered: Rendered = JSON.parse(
  execFileSync("node", ["scripts/render-chapters.mjs"], {
    input: readFileSync(INPUT, "utf8"),
    encoding: "utf8",
    cwd: new URL("..", import.meta.url).pathname,
  }),
);

const chapters = new Map(rendered.chapters.map((c) => [c.anchor_key, c.html]));
const cards = new Map(rendered.cards.map((c) => [c.id, c.html]));
const sections = new Map(
  rendered.chapters.map((c) => [c.anchor_key, c.section_key]),
);

const expected = JSON.parse(readFileSync(EXPECTED, "utf8")) as {
  chapters: Record<string, string>;
  cards: Record<string, string>;
  sections: Record<string, string>;
};

describe("the prose renderer contract", () => {
  for (const [name, html] of Object.entries(expected.chapters)) {
    it(name, () => {
      expect(chapters.get(name)).toBe(html);
    });
  }
});

describe("the companion card renderer contract", () => {
  for (const [name, html] of Object.entries(expected.cards)) {
    it(name, () => {
      expect(cards.get(name)).toBe(html);
    });
  }
});

describe("the section key a chapter's companion notes are filed under", () => {
  for (const [name, key] of Object.entries(expected.sections)) {
    it(name, () => {
      expect(sections.get(name)).toBe(key);
    });
  }

  // The distinction the whole reconciliation exists for. If these two rules ever
  // agree, the publish step is matching on a coincidence.
  it("keeps the ordinal that the chapter's own key drops", () => {
    expect(
      expected.sections[
        "a numbered chapter heading, which must not become part of the key"
      ],
    ).toBe("3-the-hours-before-dawn");
  });
});

describe("the class names the reading column depends on", () => {
  const CSS = readFileSync(
    new URL("../app/styles/podcast-factory.css", import.meta.url),
    "utf8",
  );

  // Read off the fixture rather than listed by hand, so a class that appears in
  // real output and has no rule is caught the moment the fixture records it.
  // Cards included: their Arabic runs carry a class of their own, and a card is
  // shown on the same page as the prose.
  const emitted = new Set(
    [
      ...[...Object.values(expected.chapters), ...Object.values(expected.cards)]
        .join("\n")
        .matchAll(/class="([^"]+)"/g),
    ]
      .flatMap((m) => m[1].split(/\s+/))
      .filter((c) => c.length > 0),
  );

  for (const cls of emitted) {
    it(`.${cls} is styled`, () => {
      expect(
        CSS,
        `the renderer emits .${cls} and the theme's reading column has no rule for it`,
      ).toContain(`.${cls}`);
    });
  }
});
