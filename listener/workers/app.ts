import { createRequestHandler, RouterContextProvider } from "react-router";

import { cloudflare } from "../app/context";
import { createAuth } from "../app/server/auth.server";

const requestHandler = createRequestHandler(
  () => import("virtual:react-router/server-build"),
  import.meta.env.MODE,
);

const ALLOWED_METHODS = new Set([
  "GET",
  "HEAD",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "OPTIONS",
]);

/**
 * Layer 0 — everything decided before React Router sees a request.
 *
 * The important move is the first one: `/api/auth/*` goes straight to Better
 * Auth and never enters the route tree. Sign-in has to work while signed out, so
 * if it lived inside the tree the authentication gate would need a carve-out —
 * and carve-outs get widened. With the handler lifted out, every remaining route
 * sits behind the gate with no exceptions at all, which is what lets
 * app/routes.ts stand as the policy.
 */
export default {
  async fetch(request, env, ctx) {
    // A non-standard method reaches the router only to be answered 405, and a
    // 405 distinguishes a route that exists from one that does not. A 404 says
    // nothing either way. (queryRoute throws 405 before the middleware pipeline,
    // so this cannot be fixed downstream.)
    if (!ALLOWED_METHODS.has(request.method)) {
      return new Response(null, { status: 404 });
    }

    const url = new URL(request.url);
    if (url.pathname === "/api/auth" || url.pathname.startsWith("/api/auth/")) {
      const auth = createAuth(env);
      return withSecurityHeaders(await auth.handler(request));
    }

    // Fresh per request: bindings are request-scoped, and a provider shared
    // across requests would leak one visitor's context into another's.
    const context = new RouterContextProvider();
    context.set(cloudflare, { env, ctx });

    return withSecurityHeaders(await requestHandler(request, context));
  },
} satisfies ExportedHandler<Env>;

/**
 * Headers that are cheap, apply to everything, and would otherwise have to be
 * remembered per route.
 *
 * No Content-Security-Policy yet. The theme bootstrap in root.tsx is an inline
 * script, so a real policy needs a nonce threaded through it; a policy carrying
 * 'unsafe-inline' would be decoration rather than protection. Worth doing
 * properly, in its own change.
 */
function withSecurityHeaders(response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "same-origin");
  headers.set("X-Frame-Options", "DENY");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
