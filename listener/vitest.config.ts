import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Deliberately standalone rather than extending vite.config.ts: that config
// installs the Cloudflare plugin, which owns the "ssr" environment and refuses
// the `resolve.external` list Vitest injects. These are pure unit tests over
// server-side logic (email folding, entitlement resolution, route-tree shape),
// so they need Node and nothing else. Anything that genuinely needs workerd
// belongs in the smoke script, not here.
export default defineConfig({
  // The `~/` alias tsconfig declares. Without it a server module that imports a
  // shared helper resolves in the app and in the build, and only fails under
  // Vitest — which reads as "the test is broken" rather than "the config is".
  resolve: {
    alias: { "~": fileURLToPath(new URL("./app", import.meta.url)) },
  },
  test: {
    environment: "node",
    // `.tsx` as well, for the one test that renders a route to static markup to
    // assert which panel a reader is sent. Still Node and still no DOM:
    // `renderToStaticMarkup` runs no effects, which is the point — it produces
    // the page as the server hands it over.
    include: ["test/**/*.test.ts", "test/**/*.test.tsx"],
  },
});
