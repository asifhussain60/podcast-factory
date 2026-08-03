import { defineConfig } from "vitest/config";

// Deliberately standalone rather than extending vite.config.ts: that config
// installs the Cloudflare plugin, which owns the "ssr" environment and refuses
// the `resolve.external` list Vitest injects. These are pure unit tests over
// server-side logic (email folding, entitlement resolution, route-tree shape),
// so they need Node and nothing else. Anything that genuinely needs workerd
// belongs in the smoke script, not here.
export default defineConfig({
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
