/**
 * Redirect-target validation, shared by the sign-in page (which renders it into
 * a hidden field) and the gate middleware (which builds it).
 *
 * It lives here, apart from the middleware, because the sign-in COMPONENT uses
 * it — and anything the component imports is bundled for the browser. Keeping it
 * in app/middleware/authed.ts dragged access.server.ts across the client
 * boundary, which the build refuses outright. That refusal is the point of the
 * `.server.ts` convention.
 */

/**
 * Reduce an untrusted `?next=` to a same-origin path, or "/".
 *
 * The second check is the one that matters: `//evil.example` is protocol-
 * relative and a browser resolves it as an absolute URL, so a bare
 * `startsWith("/")` test leaves an open redirect wide open.
 */
export function safeNext(candidate: string | null | undefined): string {
  if (!candidate) return "/";
  if (!candidate.startsWith("/")) return "/";
  if (candidate.startsWith("//")) return "/";
  // A backslash is normalised to a forward slash by some URL parsers, so
  // "/\evil.example" can escape the origin in the same way.
  if (candidate.startsWith("/\\")) return "/";
  return candidate;
}
