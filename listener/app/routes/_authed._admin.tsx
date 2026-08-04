import { NavLink, Outlet } from "react-router";

import type { Route } from "./+types/_authed._admin";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { MetricStrip } from "~/components/admin/MetricStrip";
import { cloudflare } from "~/context";
import { requireAdmin } from "~/middleware/admin";
import { listCatalogForAdmin, peopleTallies } from "~/server/access.server";

/**
 * Layer 3 — admin, nested inside the invited gate.
 *
 * Every admin page and (from phase 3) every `/api/admin/*` resource route hangs
 * off this one layout, so the gate is declared once. Resource routes inherit
 * parent middleware — the pipeline flat-maps the entire matched chain
 * (router.js:2283) — which is what makes a single declaration sufficient.
 */
export const middleware: Route.MiddlewareFunction[] = [requireAdmin];

/**
 * The numbers, and the filter counts, loaded ONCE for the whole section.
 *
 * They live here rather than on a page because they describe Access as a whole:
 * the same five tiles are true whichever tab is open, and the third tile —
 * people who can sign in and were given nothing — is the one worth seeing while
 * working on content, which is precisely when it is easiest to forget.
 *
 * This replaces an Overview tab. That tab held these numbers and nothing else, so
 * reaching them cost a click and leaving them cost another, and the screen an
 * administrator actually works on was never the one that opened.
 *
 * `peopleTallies` is queried here and NOT again by the people screen, which reads
 * these counts off this loader for its filter chips. Two queries for one set of
 * numbers is how a chip and a tile come to disagree.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const [tallies, catalog] = await Promise.all([
    peopleTallies(env.DB),
    listCatalogForAdmin(env.DB),
  ]);

  // Works are excluded: a work is a shelf, not something anybody reads. Counting
  // it as content would inflate every content number by the number of series.
  const readable = catalog.filter((u) => u.kind !== "work");

  return {
    tallies,
    content: {
      published: readable.filter((u) => u.status === "published").length,
      openToAll: readable.filter((u) => u.openToAll).length,
      known: readable.length,
    },
  };
}

const TABS = [
  { to: "/admin", label: "People", end: true },
  { to: "/admin/content", label: "Content", end: false },
];

export default function AdminLayout({ loaderData }: Route.ComponentProps) {
  return (
    <div className="pf-shell">
      {/* Admin is a section of this site, not a separate application, so it
          carries the same masthead — and the way back out that it lacked. */}
      <SiteHeader here="admin" isAdmin />

      <main id="main" className="pf-container">
        <div className="pf-masthead pf-masthead--tight">
          <h1 className="pf-title pf-title--sm">Access</h1>
          <p className="pf-note">Who may sign in, and which books each person can open.</p>
        </div>

        <MetricStrip tallies={loaderData.tallies} content={loaderData.content} />

        <nav className="pf-tabs">
          {TABS.map((tab) => (
            <NavLink key={tab.to} to={tab.to} end={tab.end} className="pf-tab">
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <Outlet />
      </main>

      <SiteFooter />
    </div>
  );
}
