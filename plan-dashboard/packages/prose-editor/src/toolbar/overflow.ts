/**
 * overflow.ts — decide which controls move into the "More" menu.
 *
 * Deliberately NOT the shape the editor this package replaces used, which kept
 * four hand-maintained parallel arrays — one per breakpoint — plus a fifth list
 * for shortcuts. Five places to forget one button, and two of them were in fact
 * forgotten.
 *
 * Here there are no breakpoint lists at all. Each control carries a priority;
 * when the bar does not fit, the highest priority numbers leave first. A new
 * button cannot be forgotten from a breakpoint list because there is none.
 *
 * The pure planning function is separated from the DOM so it can be tested with
 * exact widths — a headless DOM has no layout, and a measurement port beats
 * asserting against a shim that always returns zero.
 */

export interface MeasurePort {
  /** Width available to lay controls out in. */
  available(): number;
  /** Width of one control, by id. */
  widthOf(id: string): number;
  /** Width the "More" button itself occupies when shown. */
  overflowButtonWidth(): number;
}

export interface OverflowItem {
  id: string;
  /** Lower survives longer. */
  priority: number;
}

export interface OverflowPlan {
  visible: string[];
  overflowed: string[];
}

export function planOverflow(
  items: readonly OverflowItem[],
  measure: MeasurePort,
): OverflowPlan {
  const available = measure.available();
  const widths = new Map(items.map((i) => [i.id, measure.widthOf(i.id)]));
  const total = items.reduce((sum, i) => sum + (widths.get(i.id) ?? 0), 0);

  // Everything fits, or we have no width information to act on (a headless or
  // not-yet-laid-out DOM reports zero). Doing nothing is the safe reading:
  // showing every control is never worse than hiding one for no reason.
  if (available <= 0 || total <= available) {
    return { visible: items.map((i) => i.id), overflowed: [] };
  }

  // Highest priority number leaves first; ties break by later declaration, so
  // the order the host wrote is respected among equals.
  const byDeparture = items
    .map((item, index) => ({ ...item, index }))
    .sort((a, b) => b.priority - a.priority || b.index - a.index);

  const overflowed = new Set<string>();
  let used = total + measure.overflowButtonWidth();
  for (const item of byDeparture) {
    if (used <= available) break;
    overflowed.add(item.id);
    used -= widths.get(item.id) ?? 0;
  }

  return {
    visible: items.filter((i) => !overflowed.has(i.id)).map((i) => i.id),
    overflowed: items.filter((i) => overflowed.has(i.id)).map((i) => i.id),
  };
}
