// The reading-floor lint (lint-html-views.mjs, REQ-010) only inspects PROSE selectors (p, li, dt, figcaption...), so
// a class selector like `.wb-kv dd { font-size: .8rem }` or `.cx-note { font-size: 13px }` slips through: the UI
// audit of 2026-09-19 counted ~180 such declarations (book-composer.css 94, studio-pipeline.css 65, intelligence.css
// 24) against 22 reported warnings. Many are legitimately small chrome (chips, badges), so this does not call them
// wrong — it counts them per stylesheet so the number can only fall.
import assert from "node:assert/strict";
import { test } from "node:test";
import { countSubFloorFontSizes, FLOOR_REM } from "./font-floor.mjs";

test("the floor is the standard's own 1.2rem", () => {
  assert.equal(FLOOR_REM, 1.2);
});

test("a rem/em size under the floor is counted, at or over it is not", () => {
  assert.equal(
    countSubFloorFontSizes(
      ".a{font-size:.8rem}.b{font-size:1.2rem}.c{font-size:1.5rem}",
    ),
    1,
  );
  assert.equal(countSubFloorFontSizes(".a{font-size:0.5em}"), 1);
});

test("px is compared against the same floor at a 16px root", () => {
  assert.equal(
    countSubFloorFontSizes(
      ".a{font-size:13px}.b{font-size:19.2px}.c{font-size:20px}",
    ),
    1,
  );
});

test("dynamic values are never guessed at", () => {
  assert.equal(
    countSubFloorFontSizes(
      ".a{font-size:var(--x)}.b{font-size:clamp(.5rem,1vw,1rem)}.c{font-size:calc(1rem - 2px)}.d{font-size:120%}",
    ),
    0,
  );
});

test("!important, spacing and newlines do not change the answer", () => {
  assert.equal(
    countSubFloorFontSizes(".a {\n  font-size :  0.9rem !important;\n}"),
    1,
  );
});

test("comments and selectors mentioning font-size are not declarations", () => {
  assert.equal(
    countSubFloorFontSizes(
      "/* font-size: .5rem; */ .font-size-note{color:red}",
    ),
    0,
  );
});

test("every declaration counts, including several in one rule and inside media queries", () => {
  const css =
    "@media (max-width:600px){.a{font-size:.7rem}} .b{font-size:.7rem;} .c{font-size:.9rem}";
  assert.equal(countSubFloorFontSizes(css), 3);
});
