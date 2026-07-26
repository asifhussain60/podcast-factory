/**
 * Overflow planning, with exact widths.
 *
 * Tested against the pure planner rather than a rendered bar, because a headless
 * DOM has no layout: every element reports zero width, so a "does it fit" test
 * driven through real elements would assert nothing at all.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { planOverflow } from "../src/toolbar/overflow.ts";
import type { MeasurePort } from "../src/toolbar/overflow.ts";

const items = [
  { id: "bold", priority: 30 },
  { id: "italic", priority: 31 },
  { id: "link", priority: 40 },
  { id: "quote", priority: 50 },
  { id: "clear", priority: 80 },
];

function measure(available: number, each = 30, more = 30): MeasurePort {
  return {
    available: () => available,
    widthOf: () => each,
    overflowButtonWidth: () => more,
  };
}

test("everything stays put when it fits", () => {
  const plan = planOverflow(items, measure(1000));
  assert.deepEqual(plan.overflowed, []);
  assert.equal(plan.visible.length, 5);
});

test("the highest priority number leaves first", () => {
  // 5 items x 30 = 150, plus a 30px More button = 180. At 120 available, two
  // must go: `clear` (80) then `quote` (50).
  const plan = planOverflow(items, measure(120));
  assert.deepEqual(plan.overflowed, ["quote", "clear"]);
  assert.deepEqual(plan.visible, ["bold", "italic", "link"]);
});

test("visible order follows the host's declared order, not priority", () => {
  const plan = planOverflow(items, measure(120));
  assert.deepEqual(plan.visible, ["bold", "italic", "link"]);
});

test("nothing is ever dropped — everything is either visible or in the menu", () => {
  // A control that silently disappears is indistinguishable from one that was
  // never built. Even at an absurd width, every id must be accounted for.
  const plan = planOverflow(items, measure(1));
  const all = [...plan.visible, ...plan.overflowed].sort();
  assert.deepEqual(all, items.map((i) => i.id).sort());
});

test("a DOM with no layout yet is treated as 'show everything'", () => {
  // Every element reports zero before first paint. Hiding controls on that
  // basis would mean the bar starts collapsed for no reason.
  const plan = planOverflow(items, measure(0));
  assert.deepEqual(plan.overflowed, []);
});

test("ties break toward keeping the earlier-declared control", () => {
  const tied = [
    { id: "a", priority: 50 },
    { id: "b", priority: 50 },
  ];
  // 2 x 30 = 60 does not fit in 50, and one control (30) plus a 10px More
  // button does — so exactly one departs, and it must be the later one.
  const plan = planOverflow(tied, measure(50, 30, 10));
  assert.deepEqual(plan.overflowed, ["b"]);
});
