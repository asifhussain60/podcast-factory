import { useRouteLoaderData } from "react-router";

import type { loader as authedLoader } from "~/routes/_authed";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";

/**
 * Every signed-in page, from the masthead down to the floor.
 *
 * `PublicShell` makes this argument for the two pages you can reach without
 * signing in; this is the same argument for the five behind the gate. The shell
 * was written out at each of them — `pf-shell`, then `SiteHeader`, then
 * `main#main.pf-container`, then `SiteFooter` — which is four copies of a
 * structure with nothing holding them in step, and the shared vocabulary was
 * CLASS NAMES rather than a component, so they went on looking identical while
 * they drifted. Three ways they had already drifted:
 *
 *   1. The reading page had no shell at all, so from inside a chapter there was
 *      no footer, no theme control and no way to sign out.
 *   2. Four of the five called `<SiteFooter />` bare, so a configured
 *      `PUBLIC_SITE_NAME` appeared on the library and nowhere else.
 *   3. Only the reader knew the docked-Companion modifier belongs on the shell.
 *
 * The site name is READ here rather than passed in, from the loader on the
 * layout every one of these pages hangs off. Passing it meant five loaders each
 * repeating the same line, which is the same duplication one level down.
 */
export function AppShell({
  here,
  isAdmin = false,
  reader = false,
  flush = false,
  docked = false,
  overlays,
  collection,
  children,
}: {
  /** Which page this is, so the masthead never offers a link to where you are. */
  here:
    "library" | "welcome" | "admin" | "book" | "about" | "search" | "downloads";
  isAdmin?: boolean;
  /**
   * The reading column instead of the page container.
   *
   * The reader sets its own page and prose widths, including a full-canvas
   * widest view, so its `main` must not also be capped at the page measure.
   * Every other page is one column and takes the container.
   */
  reader?: boolean;
  /**
   * No page container at all — `main` runs edge to edge and the PAGE owns its
   * own bands and gutters.
   *
   * For a page built out of full-bleed sections, which the container cannot
   * express: it caps and pads every child alike, so a tinted hero would stop
   * short of both edges with the page colour showing beside it. Escaping it from
   * the inside is the usual trick and is wrong here — `width: 100vw` counts the
   * scrollbar, so the page it is meant to widen scrolls sideways on any platform
   * that reserves one.
   *
   * Distinct from `reader`, which is not "no cap" but two nested caps of its
   * own. A page passes one or the other, never both.
   */
  flush?: boolean;
  /**
   * The Companion stands beside the text rather than over it, and the page lays
   * out in the width it leaves. A question about the SHELL, not about `main`:
   * the masthead and the footer have to clear the panel too.
   */
  docked?: boolean;
  /**
   * Fixed furniture belonging to the shell rather than to the page — the
   * reader's progress bar and its two edge panels. They are siblings of `main`
   * because one of them is a `nav` landmark that is not part of the page's
   * content, and because the docked rule reaches for the scrim from `.pf-shell`.
   */
  overlays?: React.ReactNode;
  /**
   * Which collection this page is showing, or undefined for the library's own
   * pages — see `lib/collection.ts`.
   *
   * On the SHELL rather than on `main`, because a page belongs to a collection
   * whole: its masthead title, its tabs, its pills and the links in its header
   * are all part of the one thing being looked at, and colouring the middle
   * while the edges stayed blue would read as a mistake rather than as a scheme.
   * The library grid is the one place both collections appear at once, and there
   * the attribute is per CARD instead.
   */
  collection?: "sessions";
  children: React.ReactNode;
}) {
  // Undefined only where there is no `_authed` match at all, which off the real
  // route tree means a test rendering one page in isolation. `SiteFooter` names
  // the site itself in that case, so the fallback is stated once, there.
  const authed = useRouteLoaderData<typeof authedLoader>("routes/_authed");

  return (
    <div
      className={`pf-shell${docked ? " pf-shell--docked" : ""}`}
      data-collection={collection}
    >
      <SiteHeader here={here} isAdmin={isAdmin} />

      {overlays}

      <main
        id="main"
        className={reader ? "pf-reader" : flush ? "pf-flush" : "pf-container"}
      >
        {children}
      </main>

      <SiteFooter siteName={authed?.siteName} />
    </div>
  );
}
