/**
 * The paste sanitizer.
 *
 * An ALLOW-list over a parsed DOM, replacing a 715-line DENY-list of chained
 * regular expressions over an HTML string. The difference these tests are
 * really about: a paste shape nobody anticipated is handled by construction,
 * because the question asked is "is this permitted" rather than "have we seen
 * this before".
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";
import { sanitizeHtml } from "../src/input/paste.ts";

const clean = (html: string, opts = {}) => sanitizeHtml(html, opts, domDoc);

test("Word's inline formatting is stripped, its text kept", () => {
  const word =
    '<p class="MsoNormal" style="margin:0in;font-family:Calibri">' +
    '<span style="font-size:11pt;color:#1F497D">Hello </span>' +
    '<b style="mso-bidi-font-weight:normal">there</b></p>';
  const out = clean(word);
  assert.ok(!out.includes("style="), "no inline style survives");
  assert.ok(!out.includes("MsoNormal"), "no foreign class survives");
  assert.ok(out.includes("Hello"), "the text survives");
  assert.ok(out.includes("<b>there</b>"), "real emphasis survives");
});

test("Google Docs wrappers unwrap without eating their text", () => {
  const gdocs =
    '<b id="docs-internal-guid-1" style="font-weight:normal">' +
    '<p dir="ltr"><span style="font-size:11pt">A line.</span></p></b>';
  const out = clean(gdocs);
  assert.ok(!out.includes("style="));
  assert.ok(!out.includes("docs-internal-guid"));
  assert.ok(out.includes("A line."));
});

test("chrome tags are dropped WITH their content", () => {
  // A <script>'s text is not prose that lost its tag; it must not survive as
  // a paragraph of source code.
  const out = clean(
    "<p>keep</p><script>alert(1)</script><style>p{color:red}</style>",
  );
  assert.ok(out.includes("keep"));
  assert.ok(!out.includes("alert"));
  assert.ok(!out.includes("color:red"));
});

test("unknown tags unwrap — the text was the point, the tag was not", () => {
  const out = clean("<p>before <acme-widget>inner</acme-widget> after</p>");
  assert.ok(!out.includes("acme-widget"));
  assert.ok(out.includes("inner"));
});

test("event handlers and javascript: URLs never survive", () => {
  const out = clean(
    '<p onclick="steal()">x</p><a href="javascript:evil()">y</a>',
  );
  assert.ok(!out.includes("onclick"));
  assert.ok(!out.includes("javascript:"));
});

test("classes are dropped unless the host allows them", () => {
  const html = '<blockquote class="verse note"><p>text</p></blockquote>';
  assert.ok(!clean(html).includes("class="), "nothing allowed by default");

  const kept = clean(html, { allowClasses: ["verse"] });
  assert.ok(kept.includes('class="verse"'), "the allowed one survives");
  assert.ok(!kept.includes("note"), "the other does not");
});

test("a registered extension's markup survives its own paste allowance", () => {
  // Without this, a custom node's parseHTML never gets anything to match, and
  // the failure is invisible until someone pastes.
  const out = clean('<aside class="callout" data-kind="tip">hi</aside>', {
    extensionAllowances: [
      {
        tags: ["aside"],
        attributes: { aside: ["data-kind"] },
        classes: ["callout"],
      },
    ],
  });
  assert.ok(out.includes("<aside"));
  assert.ok(out.includes('class="callout"'));
  assert.ok(out.includes('data-kind="tip"'));
});

test("an ordered list keeps the ordinals it was copied with", () => {
  const out = clean('<ol start="3"><li value="3">c</li></ol>');
  assert.ok(out.includes('start="3"'));
  assert.ok(out.includes('value="3"'));
});

test("comments are removed", () => {
  const out = clean("<p>a<!-- editor bookkeeping -->b</p>");
  assert.ok(!out.includes("bookkeeping"));
});

test("deeply nested foreign markup does not lose the prose inside it", () => {
  const nested =
    '<div style="x"><div><section><span style="y">' +
    "<b>deep</b></span></section></div></div>";
  const out = clean(nested);
  assert.ok(out.includes("<b>deep</b>"));
  assert.ok(!out.includes("style="));
});
