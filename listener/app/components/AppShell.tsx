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
  docked = false,
  overlays,
  children,
}: {
  /** Which page this is, so the masthead never offers a link to where you are. */
  here: "library" | "admin" | "book";
  isAdmin?: boolean;
  /**
   * The reading column instead of the page container.
   *
   * The reader sets its own two widths — a 76rem control rail above a 56rem
   * sheet — so its `main` must not also be capped at the page measure. Every
   * other page is one column and takes the container.
   */
  reader?: boolean;
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
  children: React.ReactNode;
}) {
  // Undefined only where there is no `_authed` match at all, which off the real
  // route tree means a test rendering one page in isolation. `SiteFooter` names
  // the site itself in that case, so the fallback is stated once, there.
  const authed = useRouteLoaderData<typeof authedLoader>("routes/_authed");

  return (
    <div className={`pf-shell${docked ? " pf-shell--docked" : ""}`}>
      <SiteHeader here={here} isAdmin={isAdmin} />

      {overlays}

      <main id="main" className={reader ? "pf-reader" : "pf-container"}>
        {children}
      </main>

      <SiteFooter siteName={authed?.siteName} />
    </div>
  );
}
