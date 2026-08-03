import { NavLink, Outlet } from "react-router";

import type { Route } from "./+types/_authed._admin";
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
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="mb-8">
        <p className="text-xs uppercase tracking-widest text-pf-faint">Podcast Factory</p>
        <h1 className="mt-1 font-prose text-3xl text-pf-ink">Access</h1>
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
      </header>
      <Outlet />
    </div>
  );
}
