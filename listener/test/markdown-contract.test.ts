import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * The one build-time dependency on the admin site, pinned.
 *
 * `renderMarkdown` in plan-dashboard/src/lib/reader/markdown.ts is what turns
 * book prose into HTML for BOTH the printed edition and this site. That is the
 * whole reason the Listener calls it rather than parsing markdown itself — the
 * page and the PDF cannot then disagree about the same paragraph.
 *
 * The risk that creates is silent: someone improves the renderer for the print
 * side, the class names shift, and §7 of app/styles/podcast-factory.css — which
 * styles by those exact class names — stops matching. Nothing fails; Arabic
 * quotations simply stop being centred, or an editorial aside starts rendering
 * as display scripture. This test turns that into a failing build.
 *
 * A changed fixture is not automatically a bug. It means the renderer's contract
 * moved, and §7 has to move with it in the same commit.
 */

const INPUT = new URL("./fixtures/markdown-input.json", import.meta.url);
const EXPECTED = new URL("./fixtures/markdown-expected.json", import.meta.url);

const rendered = (() => {
  const out = execFileSync("node", ["scripts/render-chapters.mjs"], {
    input: readFileSync(INPUT, "utf8"),
    encoding: "utf8",
    cwd: new URL("..", import.meta.url).pathname,
  });

  const payload = JSON.parse(out) as { chapters: { anchor_key: string; html: string }[] };
  return new Map(payload.chapters.map((c) => [c.anchor_key, c.html]));
})();

const expected = JSON.parse(readFileSync(EXPECTED, "utf8")) as Record<string, string>;

describe("the renderer contract", () => {
  for (const [name, html] of Object.entries(expected)) {
    it(name, () => {
      expect(rendered.get(name)).toBe(html);
    });
  }
});

describe("the class names the reading column depends on", () => {
  const CSS = readFileSync(new URL("../app/styles/podcast-factory.css", import.meta.url), "utf8");

  // Read off the fixture rather than listed by hand, so a class that appears in
  // real output and has no rule is caught the moment the fixture records it.
  const emitted = new Set(
    [...Object.values(expected).join("\n").matchAll(/class="([^"]+)"/g)]
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
