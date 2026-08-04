import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { ReaderToolbar } from "../app/components/reader/ReaderToolbar";
import { DEFAULT_PREFS, LEADING_LABELS, MEASURE_LABELS } from "../app/lib/reading";

/**
 * WHICH SETTING each control drives.
 *
 * This is not a styling test. The three buttons drove line WIDTH until
 * 2026-08-04, while being drawn with arrows pushing left and right — so they
 * looked like a spacing control and moved the wrong axis, and nothing failed,
 * because both settings are a number written to the same store by the same
 * function. The only way that is caught is by asserting what each control SAYS
 * it does next to what it writes.
 */

const html = renderToStaticMarkup(
  createElement(
    StaticRouter,
    { location: "/book/x/read/y" },
    createElement(ReaderToolbar, { bookmarked: false, onToggleBookmark: () => {} }),
  ),
);

describe("the reading toolbar", () => {
  it("gives the three buttons to line SPACING", () => {
    expect(html).toContain('aria-label="Line spacing"');

    for (const label of Object.values(LEADING_LABELS)) {
      expect(html).toContain(`aria-label="${label} line spacing"`);
    }
  });

  it("shows which spacing is on", () => {
    const on = LEADING_LABELS[DEFAULT_PREFS.leading as keyof typeof LEADING_LABELS];
    // The pressed attribute and the label are on the same element, so they can
    // only both be right for the same button.
    expect(html).toMatch(
      new RegExp(`aria-pressed="true"[^>]*aria-label="${on} line spacing"`),
    );
  });

  it("gives the select to line WIDTH, with every step in it", () => {
    expect(html).toContain('title="Line width"');
    for (const label of Object.values(MEASURE_LABELS)) {
      expect(html).toContain(`>${label}</option>`);
    }
  });

  it("never states a setting's value in a bare word", () => {
    // Spacing and width each have a "Wide". A button announcing just "Wide"
    // beside a select whose value is "Wide" is the confusion that took line
    // width off this toolbar once already; every button says which setting it
    // belongs to.
    expect(html).not.toContain('aria-label="Wide"');
    expect(html).not.toContain('aria-label="Normal"');
    expect(html).not.toContain('title="Wide"');
  });
});
