import { NavLink, Outlet } from "react-router";

import type { Route } from "./+types/_authed._admin";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { requireAdmin } from "~/middleware/admin";

/**
 * Layer 3 — admin, nested inside the invited gate.
 *
 * Every admin page and (from phase 3) every `/api/admin/*` resource route hangs
 * off this one layout, so the gate is declared once. Resource routes inherit
 * parent middleware — the pipeline flat-maps the entire matched chain
 * (router.js:2283) — which is what makes a single declaration sufficient.
 */
export const middleware: Route.MiddlewareFunction[] = [requireAdmin];

const TABS = [
  { to: "/admin", label: "Overview", end: true },
  { to: "/admin/people", label: "People", end: false },
  { to: "/admin/content", label: "Content", end: false },
];

export default function AdminLayout() {
  return (
    <div className="pf-shell">
      {/* Admin is a section of this site, not a separate application, so it
          carries the same masthead — and the way back out that it lacked. */}
      <SiteHeader here="admin" isAdmin />

      <main id="main" className="pf-container">
        <div className="pf-masthead pf-masthead--tight">
          <h1 className="pf-title pf-title--sm">Access</h1>
          <p className="pf-note">Who may sign in, and which books each person can open.</p>

          <nav className="pf-tabs">
            {TABS.map((tab) => (
              <NavLink key={tab.to} to={tab.to} end={tab.end} className="pf-tab">
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <Outlet />
      </main>

      <SiteFooter />
    </div>
  );
}
