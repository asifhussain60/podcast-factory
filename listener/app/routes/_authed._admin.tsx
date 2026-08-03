import { NavLink, Outlet } from "react-router";

import type { Route } from "./+types/_authed._admin";
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
    <div className="min-h-dvh bg-pf-bg">
      {/* Admin is a section of this site, not a separate application, so it
          carries the same masthead — and the way back out that it lacked. */}
      <SiteHeader here="admin" isAdmin />

      <main id="main" className="mx-auto w-full max-w-5xl px-6 pb-16">
        <div className="mb-8 border-t border-pf-rule pt-10">
        <h1 className="font-prose text-3xl text-pf-ink">Access</h1>
        <p className="mt-2 font-ui text-sm text-pf-muted">
          Who may sign in, and which books each person can open.
        </p>
        <nav className="mt-6 flex gap-1 border-b border-pf-rule">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                [
                  "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "border-pf-accent text-pf-ink"
                    : "border-transparent text-pf-muted hover:text-pf-ink",
                ].join(" ")
              }
            >
              {tab.label}
            </NavLink>
            ))}
          </nav>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
