/**
 * The text-colour palette exists in three places that cannot import each other:
 * the TypeScript registry (the UI), the plain .mjs the PDF build runs under, and
 * the stylesheet that says what each id LOOKS like. A palette entry added to one
 * and forgotten in another does not throw — it renders as unstyled text in one
 * surface and colour in the others, which is precisely the class of drift this
 * repo pins with tests rather than trusts to comments.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { TEXT_INKS, TEXT_INK_IDS, DEFAULT_TEXT_INK } from "./text-ink";
import { TEXT_INK_IDS as MJS_IDS } from "../../../scripts/lib/text-colour.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

test("the .mjs the PDF build uses lists the same inks as the UI", () => {
  assert.deepEqual([...MJS_IDS], [...TEXT_INK_IDS]);
});

test("the default ink is one of the inks", () => {
  assert.ok(TEXT_INK_IDS.includes(DEFAULT_TEXT_INK));
});

for (const file of [
  "src/styles/quote-typography.css",
  "src/styles/book-print.css",
]) {
  test(`${file} declares a colour for every ink`, () => {
    const css = readFileSync(join(ROOT, file), "utf-8");
    for (const ink of TEXT_INKS) {
      const rule = new RegExp(
        `\\.ink-${ink.id}\\s*\\{[^}]*color:\\s*([^;]+);`,
        "i",
      );
      const m = css.match(rule);
      assert.ok(m, `.ink-${ink.id} has no rule in ${file}`);
      // The swatch the palette draws must BE the colour the page prints, or the
      // menu is showing one thing and the book another.
      assert.equal(
        m[1].trim().toLowerCase(),
        ink.swatch.toLowerCase(),
        `.ink-${ink.id} in ${file} disagrees with the palette swatch`,
      );
    }
  });
}
