import { isRouteErrorResponse, Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";

import type { Route } from "./+types/root";
import { THEME_INIT_SCRIPT } from "~/lib/theme";
import "./app.css";

export const meta: Route.MetaFunction = () => [
  { title: "Podcast Factory" },
  { name: "description", content: "Scholarly books, read and heard." },
  { name: "color-scheme", content: "light dark" },
  // The site is invite-only, so there is nothing here for a crawler.
  { name: "robots", content: "noindex, nofollow" },
];

export const links: Route.LinksFunction = () => [
  { rel: "icon", href: "/favicon.svg", type: "image/svg+xml" },
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
        {/* Must run before first paint — see lib/theme.ts. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
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
    <main id="main" className="mx-auto max-w-2xl px-6 py-24">
      <h1 className="text-3xl">{heading}</h1>
      <p className="mt-3 text-pf-muted">{detail}</p>
      {stack ? (
        <pre className="mt-8 overflow-x-auto rounded-md bg-pf-sunken p-4 text-xs">
          <code>{stack}</code>
        </pre>
      ) : null}
    </main>
  );
}
