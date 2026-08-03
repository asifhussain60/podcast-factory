import { isRouteErrorResponse, Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";

import type { Route } from "./+types/root";
import { withSession } from "~/middleware/session";
import { READING_INIT_SCRIPT } from "~/lib/reading";
import { THEME_INIT_SCRIPT } from "~/lib/theme";
import "./app.css";

// Layer 1. Resolves the session into context for every matched request and
// gates nothing — the sign-in page needs it too. See middleware/session.ts for
// why it must always set a value.
export const middleware: Route.MiddlewareFunction[] = [withSession];

export const meta: Route.MetaFunction = () => [
  { title: "Podcast Factory" },
  { name: "description", content: "Scholarly books, read and heard." },
  { name: "color-scheme", content: "light dark" },
  // The site is invite-only, so there is nothing here for a crawler.
  { name: "robots", content: "noindex, nofollow" },
  // Not for search — for the person who pastes an invitation link into a chat
  // and would otherwise send a bare URL with no indication of what it is.
  { property: "og:title", content: "Podcast Factory" },
  { property: "og:description", content: "Scholarly books, read and heard." },
  { property: "og:image", content: "/brand/og.png" },
];

export const links: Route.LinksFunction = () => [
  // The SVG is the real icon — it follows the OS between light and dark. The
  // PNG is the fallback for the places that will not take an SVG at all, and
  // the apple-touch one is what iOS puts on a home screen. Both come out of
  // `npm run brand`.
  { rel: "icon", href: "/favicon.svg", type: "image/svg+xml" },
  { rel: "icon", href: "/brand/icon-32.png", type: "image/png", sizes: "32x32" },
  { rel: "apple-touch-icon", href: "/brand/icon-180.png" },
  // The two faces above the fold. Arabic and OpenDyslexic load on demand.
  {
    rel: "preload",
    href: "/fonts/ibm-plex-sans-latin-wght-normal.woff2",
    as: "font",
    type: "font/woff2",
    crossOrigin: "anonymous",
  },
  {
    rel: "preload",
    href: "/fonts/literata-latin-opsz-normal.woff2",
    as: "font",
    type: "font/woff2",
    crossOrigin: "anonymous",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning covers THIS element's own attributes only, not
    // the subtree. It is required because the inline script below stamps
    // `data-theme` before React hydrates, and the server cannot know which
    // theme to render — so the two necessarily disagree on that one attribute.
    // Without it React logs a hydration mismatch on every single page load.
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <Meta />
        <Links />
        {/* Both must run before first paint. The theme one prevents a light
            flash; the reading one prevents a stored 23px setting rendering at
            19px and jumping mid-paragraph on hydration, which loses the
            reader's place. See lib/theme.ts and lib/reading.ts. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: READING_INIT_SCRIPT }} />
      </head>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}

/**
 * The ONLY error boundary in the application.
 *
 * No route under a gate may export its own, and the reason is precise: a denied
 * request throws a 404 from middleware, at which point `matches` is the full
 * chain and React Router renders `findNearestBoundary(matches, routeId)` — a
 * child boundary if one exists. A genuinely unmatched path short-circuits with
 * only the root match and empty loaderData (router.js:1472-1486). Two boundaries
 * means two visibly different 404s, and the difference tells an attacker which
 * slugs are real.
 *
 * For the same reason nothing here may read loader data or session context:
 * neither exists on the hard-404 path, and touching them would turn that 404
 * into a 500 — the same tell by another route.
 */
export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let heading = "Something went wrong";
  let detail = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    heading = error.status === 404 ? "Not found" : `Error ${error.status}`;
    detail =
      error.status === 404
        ? "That page does not exist."
        : error.statusText || detail;
  } else if (import.meta.env.DEV && error instanceof Error) {
    detail = error.message;
    stack = error.stack;
  }

  return (
    <main id="main" className="pf-container pf-container--narrow pf-error">
      <h1 className="pf-title">{heading}</h1>
      <p className="pf-lede">{detail}</p>
      {stack ? (
        <pre className="pf-stack">
          <code>{stack}</code>
        </pre>
      ) : null}
    </main>
  );
}
