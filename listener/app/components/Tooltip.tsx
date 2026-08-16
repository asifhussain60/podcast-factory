import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

/**
 * One shared delay group for every tooltip on a page — put ONCE, high enough
 * to wrap everything that uses `Tooltip` below (the reader toolbar wraps its
 * own row in it, rather than this module wrapping each instance individually,
 * which would each restart their own delay and defeat the point of a group).
 *
 * 150ms open delay is deliberately short — Radix's own default is 700ms,
 * tuned for a generic web page where a slow tooltip is barely noticed; a
 * reading toolbar is scanned quickly with the pointer, and at the default
 * delay most passes across it show nothing at all. `skipDelayDuration` is
 * the OTHER half of "quick": once one tooltip has shown, moving to the next
 * trigger within that window skips the delay entirely, which is what makes
 * sweeping across a row of buttons feel instant rather than each one paying
 * the same 150ms toll.
 */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <TooltipPrimitive.Provider delayDuration={150} skipDelayDuration={250}>
      {children}
    </TooltipPrimitive.Provider>
  );
}

/**
 * A custom tooltip with its own header and description, replacing the
 * browser's native `title` tooltip — which cannot be styled, cannot carry
 * two lines with different weight, and on most browsers takes the better
 * part of a second to appear (Asif, 2026-08-16: "should appear quickly and
 * not take too long to show").
 *
 * Built on Radix's Tooltip primitive rather than hand-rolled, for one
 * concrete reason: the reader toolbar scrolls horizontally
 * (`.pf-toolbar { overflow-x: auto }`), and per the CSS spec, setting
 * `overflow-x` on an element computes `overflow-y` to `auto` as well — so a
 * tooltip absolutely positioned INSIDE that row would be clipped the moment
 * it tried to float above or below the row's own bounds. Radix renders its
 * content through a portal straight onto `document.body` and measures the
 * trigger's real position there, which is what a from-scratch
 * `position: absolute` tooltip cannot do without reimplementing the same
 * portal-plus-collision-detection machinery this already ships, tested,
 * keyboard-accessible (focus shows it, `Escape` dismisses it) and
 * accessible via `aria-describedby` for free.
 *
 * Deliberately still unstyled at the primitive level — every visual choice
 * below (the card surface, the header/description split, the arrow) is
 * this site's own CSS reading the same `--l-*`/`--pf-*` tokens every other
 * floating panel already uses, not a theme borrowed from the library.
 */
export function Tooltip({
  header,
  description,
  children,
}: {
  header: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          className="pf-tooltip"
          sideOffset={8}
          collisionPadding={8}
        >
          <p className="pf-tooltip__header">{header}</p>
          <p className="pf-tooltip__desc">{description}</p>
          <TooltipPrimitive.Arrow className="pf-tooltip__arrow" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
