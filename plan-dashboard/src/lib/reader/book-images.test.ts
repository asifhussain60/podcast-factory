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
import { readFileSync } from "node:fs";
import { test, describe } from "node:test";
import { serveBookImages } from "./book-images";
import { renderMarkdown, renderEditSeed } from "./markdown";
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

describe("the Composer's edit-mode seed also gets its images rewritten", () => {
  // Read mode and the reader view were fixed 2026-08-11 (see the file header);
  // the edit-mode seed (`renderEditSeed`, fed to TipTap) went through
  // `serveBookImages` too late for that fix and stayed on a `book/`-relative
  // src, so a chapter's pictures were still invisible the moment an author
  // opened it in the editor. Guards composer.ts wiring both renders the same
  // way rather than just one of them.
  test("a book-relative src in the edit seed becomes the studio route", () => {
    const seed = renderEditSeed(`![](images/213/${GUID}.jpg)`);
    const out = serveBookImages(seed, "surah-al-fateha");
    assert.ok(
      out.includes(
        `/api/studio/book-image?slug=surah-al-fateha&path=213%2F${GUID}.jpg`,
      ),
    );
    assert.ok(!out.includes(`src="images/213/${GUID}.jpg"`));
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

describe("a centered Composer image is actually centered, not just full-width", () => {
  // History: under the old width-percentage model, `width: fit-content` on
  // the figure and `width: var(--img-w, 100%)` on the <img> chased each
  // other — the img's percentage basis WAS the figure's own box, so a
  // browser could only break that circularity by stretching the figure to
  // the column's full width, leaving `margin-inline: auto` centering a box
  // with nothing to spare (verified live 2026-08-14: a resized image sat
  // flush left in a full-width figure). Switching the resize unit from width
  // to height (same day, see image-layout.mjs's header) removed the
  // circularity at its root instead: the <img>'s width is now `auto`,
  // derived from its own aspect ratio against a fixed height, never a
  // percentage of the figure that contains it — so plain `fit-content` +
  // `margin-inline: auto` centers it correctly with no special-casing.
  const css = readFileSync(
    new URL("../../styles/book-composer.css", import.meta.url),
    "utf8",
  );

  test("the image sizes off its own height, never a percentage of its box", () => {
    const rule = css.match(/\.cx-image-figure img\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /width:\s*auto/);
    assert.match(rule, /height:\s*var\(--img-h,\s*350px\)/);
    assert.doesNotMatch(rule, /width:\s*var\(--img-w/);
  });

  test("center align centers a shrink-wrapped box, not a full-width one", () => {
    const rule =
      css.match(/\.cx-image-figure\[data-align="center"\]\s*\{[^}]*\}/)?.[0] ??
      "";
    assert.notEqual(rule, "");
    assert.match(rule, /margin-inline:\s*auto/);
    const figureRule = css.match(/\.cx-image-figure\s*\{[^}]*\}/)?.[0] ?? "";
    assert.match(figureRule, /width:\s*fit-content/);
  });
});

describe("the Astro reader keeps markdown figures at a standard plate size", () => {
  const css = readFileSync(
    new URL("../../styles/book-reader.css", import.meta.url),
    "utf8",
  );

  test("the figure gets a shared cap across chapters", () => {
    const rule = css.match(/\.bookv-body \.md-figure\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /width:\s*min\(100%, 34rem\)/);
  });

  test("the image is responsive without being forced full-column", () => {
    const rule =
      css.match(/\.bookv-body \.md-figure img\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    // `var(--img-h, auto)` (2026-08-14, height not width — see
    // image-layout.mjs's header): a Composer resize sets --img-h inline;
    // nobody having resized this image (every image before that existed)
    // must still fall back to `auto`, which is the same guarantee this test
    // asserted before the custom property existed.
    assert.match(rule, /height:\s*var\(--img-h,\s*auto\)/);
    assert.match(rule, /width:\s*auto/);
    assert.match(rule, /max-width:\s*100%/);
    assert.doesNotMatch(rule, /(^|[;\s{])width\s*:\s*100%/);
  });
});

describe("Composer headings keep their requested hierarchy", () => {
  const css = readFileSync(
    new URL("../../styles/book-composer.css", import.meta.url),
    "utf8",
  );

  test("Heading 1 is large, bold, and theme-coloured maroon", () => {
    const rule = css.match(/\.cx-prose h3\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /font-size:\s*1\.45em/);
    assert.match(rule, /font-weight:\s*700/);
    assert.match(rule, /color:\s*var\(--cx-heading-1, #800000\)/);
  });

  test("Heading 2 is navy blue and smaller than Heading 1", () => {
    const rule = css.match(/\.cx-prose h4\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /font-size:\s*1\.18em/);
    assert.match(rule, /color:\s*var\(--cx-heading-2, #1f3a5f\)/);
  });

  test("Heading 3 uses the quieter tertiary heading colour", () => {
    const rule = css.match(/\.cx-prose h5\s*\{[^}]*\}/)?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /font-size:\s*1\.04em/);
    assert.match(rule, /color:\s*var\(--cx-heading-3, #2f6f5e\)/);
  });

  test("light, sepia, and dark paper modes provide their own heading inks", () => {
    for (const paper of ["light", "sepia", "dark"]) {
      const rule =
        css.match(
          new RegExp(
            `\\.cx-edit-host\\[data-paper="${paper}"\\]\\s*\\{[^}]*\\}`,
          ),
        )?.[0] ?? "";
      assert.notEqual(rule, "");
      assert.match(rule, /--cx-heading-1:\s*#[0-9a-f]{6}/i);
      assert.match(rule, /--cx-heading-2:\s*#[0-9a-f]{6}/i);
      assert.match(rule, /--cx-heading-3:\s*#[0-9a-f]{6}/i);
    }
  });
});

describe("inline Arabic keeps regular weight", () => {
  const composerCss = readFileSync(
    new URL("../../styles/book-composer.css", import.meta.url),
    "utf8",
  );
  const typographyCss = readFileSync(
    new URL("../../styles/quote-typography.css", import.meta.url),
    "utf8",
  );

  test("the shared token is regular, not bold", () => {
    assert.match(typographyCss, /--q-ar-inline-weight:\s*400/);
    assert.doesNotMatch(typographyCss, /--q-ar-inline-weight:\s*700/);
  });

  test("Composer inline Arabic falls back to regular weight", () => {
    const rule =
      composerCss.match(
        /\.cx-body \.ar-inline,[\s\S]*?\.cx-prose \.ar-raw\s*\{[^}]*\}/,
      )?.[0] ?? "";
    assert.notEqual(rule, "");
    assert.match(rule, /font-weight:\s*var\(--q-ar-inline-weight,\s*400\)/);
  });
});
