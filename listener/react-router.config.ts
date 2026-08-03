import type { Config } from "@react-router/dev/config";

export default {
  // Server rendering stays on: it is what lets one <audio> element live in the
  // root layout and survive every navigation, and it puts the API routes in the
  // same Worker as the UI. It is NOT here for SEO — the site is invite-only.
  ssr: true,

  // With ssr:true the default is `lazy`, which stands up an unauthenticated
  // /__manifest endpoint. That endpoint answers BEFORE route matching
  // (server-runtime/server.js:91-93, ahead of matchServerRoutes at :98), so no
  // middleware can gate it. Blocking it is not an option either — lazy
  // discovery depends on it for client navigation.
  //
  // `initial` removes the endpoint entirely. It does not make the route table
  // secret: the same table then ships inside build/client/assets/manifest-*.js,
  // which the asset server hands out before the Worker runs. That is accepted.
  // Route ids are not secrets, slugs are route *params* rather than routes, and
  // every real check is server-side. This just deletes one surface.
  routeDiscovery: { mode: "initial" },
} satisfies Config;
