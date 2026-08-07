import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { ReaderToolbar } from "../app/components/reader/ReaderToolbar";
import {
  DEFAULT_PREFS,
  LEADING_LABELS,
  MEASURE_LABELS,
} from "../app/lib/reading";

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
    createElement(ReaderToolbar, {
      bookmarked: false,
      onToggleBookmark: () => {},
    }),
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
    const on =
      LEADING_LABELS[DEFAULT_PREFS.leading as keyof typeof LEADING_LABELS];
    // The pressed attribute and the label are on the same element, so they can
    // only both be right for the same button.
    expect(html).toMatch(
      new RegExp(`aria-pressed="true"[^>]*aria-label="${on} line spacing"`),
    );
  });

  it("gives its own three buttons to PAGE WIDTH, with every step in them", () => {
    expect(html).toContain('aria-label="Page width"');

    for (const label of Object.values(MEASURE_LABELS)) {
      expect(html).toContain(`aria-label="${label} page width"`);
    }
  });

  it("shows which width is on", () => {
    const on =
      MEASURE_LABELS[DEFAULT_PREFS.measure as keyof typeof MEASURE_LABELS];
    expect(html).toMatch(
      new RegExp(`aria-pressed="true"[^>]*aria-label="${on} page width"`),
    );
  });

  it("draws width as a page and spacing as lines, never the same family", () => {
    // Three times now this control has been misread because it borrowed the
    // drawing of the setting beside it. The spacing buttons are Font Awesome
    // line stacks; the width buttons are a <rect> outline and nothing else. If
    // width ever grows an <svg> full of lines again, this fails.
    const widthButtons =
      html.match(/aria-label="[^"]* page width"[\s\S]*?<\/button>/g) ?? [];
    expect(widthButtons).toHaveLength(Object.keys(MEASURE_LABELS).length);
    for (const button of widthButtons) {
      expect(button).toContain("<rect");
      expect(button).not.toContain("<path");
    }
  });

  it("never states a setting's value in a bare word", () => {
    // Every button says which setting it belongs to. Two controls stating a
    // value in the same word with nothing to separate them is what took the
    // width control off this toolbar once already.
    for (const bare of Object.values(LEADING_LABELS).concat(
      Object.values(MEASURE_LABELS),
    )) {
      expect(html).not.toContain(`aria-label="${bare}"`);
      expect(html).not.toContain(`title="${bare}"`);
    }
  });

  it("shares no word between the spacing scale and the width scale", () => {
    // The rule the labels are chosen to satisfy, asserted rather than trusted:
    // Compact/Normal/Wide against Standard/Wider/Widest. A future edit that
    // renamed a width step "Wide" would reintroduce the collision in a place no
    // screenshot would show.
    const spacing = new Set(Object.values(LEADING_LABELS));
    for (const width of Object.values(MEASURE_LABELS)) {
      expect(spacing.has(width)).toBe(false);
    }
  });
});
