/**
 * Browsers probe /favicon.ico regardless of the <link rel="icon"> we declare.
 * Without this the probe falls through to the router and logs a "No route
 * matches" error on every cold visit — noise that would otherwise become the
 * accepted baseline and hide a real 404 later.
 *
 * A redirect rather than a second copy of the art: one SVG stays the source of
 * truth for the mark.
 */
export function loader() {
  return new Response(null, {
    status: 301,
    headers: {
      Location: "/favicon.svg",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
