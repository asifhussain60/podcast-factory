import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";

import { renderNote, sanitizeNote } from "../app/lib/richNote";

/**
 * The one parser `sanitizeNote` (the write gate) and `renderNote` (what every
 * surface displays) both walk. `render(raw)` below turns `renderNote`'s React
 * tree into an HTML string so a test can assert on it without a DOM — the same
 * reason `renderNote` itself never touches one.
 */
function render(raw: string): string {
  return renderToStaticMarkup(createElement("div", null, renderNote(raw)));
}

describe("sanitizeNote", () => {
  it("keeps the seven allowed tokens, nested", () => {
    expect(sanitizeNote("<p><strong><em>x</em></strong></p>")).toBe(
      "<p><strong><em>x</em></strong></p>",
    );
  });

  it("keeps multi-item bullet and numbered lists", () => {
    expect(sanitizeNote("<ul><li>a</li><li>b</li></ul>")).toBe("<ul><li>a</li><li>b</li></ul>");
    expect(sanitizeNote("<ol><li>a</li><li>b</li></ol>")).toBe("<ol><li>a</li><li>b</li></ol>");
  });

  it("keeps br, self-closed or not", () => {
    expect(sanitizeNote("a<br>b")).toBe("a<br>b");
    expect(sanitizeNote("a<br/>b")).toBe("a<br>b");
  });

  it("degrades a disallowed tag to literal, escaped text — never drops it", () => {
    expect(sanitizeNote("<script>alert(1)</script>")).toBe(
      "&lt;script&gt;alert(1)&lt;/script&gt;",
    );
  });

  it("degrades an attribute-bearing payload the same way", () => {
    // Only `< > &` are structurally significant once this is always rendered
    // as HTML TEXT content (never interpolated into an attribute) — a quote
    // character needs no escaping there, so it survives literally.
    expect(sanitizeNote('<img src=x onerror="alert(1)">')).toBe(
      '&lt;img src=x onerror="alert(1)"&gt;',
    );
  });

  it("degrades an unmatched or mismatched close tag to literal text without throwing", () => {
    expect(() => sanitizeNote("</p>hello")).not.toThrow();
    expect(sanitizeNote("</p>hello")).toBe("&lt;/p&gt;hello");
    expect(sanitizeNote("<p>hello</strong></p>")).toBe("<p>hello&lt;/strong&gt;</p>");
  });

  it("degrades a bare '<' with no matching token shape", () => {
    expect(sanitizeNote("a < b")).toBe("a &lt; b");
  });

  it("handles empty input", () => {
    expect(sanitizeNote("")).toBe("");
  });

  it("round-trips legacy plain text, including a literal '<'/'>', unchanged in meaning", () => {
    const legacy = "a note from before this feature, with a < b and c > d in it";
    const sanitized = sanitizeNote(legacy);
    // Same visible characters as before — this is what `render` below asserts.
    expect(render(sanitized)).toBe(render(legacy));
  });
});

describe("renderNote", () => {
  it("renders null for empty/absent input", () => {
    expect(renderNote("")).toBeNull();
    expect(renderNote(null)).toBeNull();
    expect(renderNote(undefined)).toBeNull();
  });

  it("renders real markup for the allowed tokens", () => {
    expect(render("<p><strong>bold</strong> and <em>italic</em></p>")).toBe(
      "<div><p><strong>bold</strong> and <em>italic</em></p></div>",
    );
  });

  it("renders a disallowed payload as inert visible text, never as markup", () => {
    const html = render("<script>alert(1)</script>");
    expect(html).not.toContain("<script>");
    expect(html).toContain("alert(1)");
  });

  it("renders legacy plain text exactly as it always has", () => {
    expect(render("just some words")).toBe("<div>just some words</div>");
  });
});
