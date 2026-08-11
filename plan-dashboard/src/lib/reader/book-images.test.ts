/**
 * A session illustration reaches the browser, or nothing anywhere says it did not.
 *
 * Three surfaces render the same `book.md`, and until 2026-08-11 all three showed
 * a Sessions chapter's diagrams as the literal text `![](images/213/….jpg)` or as
 * a broken picture:
 *
 *   the printed PDF          `renderMd` had no image rule at all
 *   the Composer's read mode same renderer, and served over HTTP besides
 *   the reader view          had the figure rule, but a src relative to `book/`
 *
 * Every one of those failures is silent. The file is on disk, the markdown is
 * correct, the render succeeds, and the page is simply missing a picture — which
 * is why these assertions are about the JOIN between the renderer and the route
 * rather than about either alone.
 */
import { strict as assert } from "node:assert";
import { test, describe } from "node:test";
import { serveBookImages } from "./book-images";
import { renderMarkdown } from "./markdown";
import { renderMd } from "../../../scripts/lib/book-html.mjs";

const GUID = "21ac5722-564f-4aed-beeb-4f61c600508f";

describe("book-relative illustrations are pointed at the studio route", () => {
  test("a book image becomes a request the site can answer", () => {
    const out = serveBookImages(
      `<img src="images/87/${GUID}.jpg" alt="" />`,
      "surah-al-fateha",
    );
    assert.equal(
      out,
      `<img src="/api/studio/book-image?slug=surah-al-fateha&path=87%2F${GUID}.jpg" alt="" />`,
    );
  });

  test("every image on the page is rewritten, not just the first", () => {
    const html = `<img src="images/87/a.jpg" /><p>x</p><img src="images/152/b.jpg" />`;
    const out = serveBookImages(html, "s");
    assert.equal(out.match(/\/api\/studio\/book-image/g)?.length, 2);
    assert.ok(!out.includes('src="images/'));
  });

  test("an absolute src is left exactly as it is", () => {
    // Not a book asset. Prefixing the route onto it would ask the server for a
    // file that was never on disk, and the 404 would look like a missing image
    // rather than a wrong rewrite.
    for (const src of [
      "/api/studio/visual-asset?slug=x&file=y.png",
      "https://example.com/a.jpg",
      "/cover.png",
      "data:image/png;base64,iVBORw0KGgo=",
    ]) {
      const html = `<img src="${src}" />`;
      assert.equal(serveBookImages(html, "s"), html);
    }
  });

  test("the slug and the path are encoded into the query", () => {
    // The path segment carries a slash, which must survive as data rather than
    // becoming another path segment of the route.
    const out = serveBookImages(`<img src="images/87/a b.jpg" />`, "a-b");
    assert.ok(out.includes("path=87%2Fa%20b.jpg"));
  });

  test("prose that merely mentions the word images is untouched", () => {
    const html = "<p>He showed images/87 on the screen.</p>";
    assert.equal(serveBookImages(html, "s"), html);
  });
});

describe("both renderers set a standalone image as the same figure", () => {
  // The PDF renderer and the reader's renderer are separate implementations,
  // shared with the printed book precisely so the page and the PDF cannot
  // disagree about what a paragraph looks like. A figure is a paragraph-level
  // decision and belongs in that guarantee.
  const source = `![](images/213/${GUID}.jpg)`;

  test("the print renderer emits a figure", () => {
    const html = String(renderMd(source, new Map(), {}));
    assert.ok(html.includes('<figure class="md-figure">'));
    assert.ok(html.includes(`src="images/213/${GUID}.jpg"`));
    assert.ok(!html.includes("!["), "the markdown must not survive as text");
  });

  test("the reader's renderer emits the same figure", () => {
    const html = renderMarkdown(source);
    assert.ok(html.includes('<figure class="md-figure">'));
    assert.ok(html.includes(`src="images/213/${GUID}.jpg"`));
  });

  test("an image mid-sentence stays literal in both", () => {
    // A block element opened inside a `<p>` is closed by the browser somewhere
    // nobody chose. Both renderers decline rather than guess.
    const inline = `see ![](images/213/${GUID}.jpg) here`;
    assert.ok(String(renderMd(inline, new Map(), {})).includes("!["));
    assert.ok(renderMarkdown(inline).includes("!["));
  });

  test("a caption is carried by both when the author wrote one", () => {
    const captioned = `![A vs THE](images/87/${GUID}.jpg)`;
    for (const html of [
      String(renderMd(captioned, new Map(), {})),
      renderMarkdown(captioned),
    ]) {
      assert.ok(html.includes("<figcaption>"));
      assert.ok(html.includes("A vs THE"));
    }
  });

  test("a quote character in the alt cannot break out of the attribute", () => {
    const html = String(
      renderMd(`![a"b](images/87/${GUID}.jpg)`, new Map(), {}),
    );
    assert.ok(!/alt="a"b"/.test(html));
    assert.ok(html.includes("&quot;"));
  });
});
