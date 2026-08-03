import { reactRouter } from "@react-router/dev/vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// Plugin order matters and matches Cloudflare's own react-router starter:
// cloudflare must register the workerd environment before reactRouter binds
// the SSR build to it.
//
// No vite-tsconfig-paths — Vite 8 resolves tsconfig `paths` natively, and the
// plugin now warns that it is redundant.
export default defineConfig({
  // 5273, not Vite's default 5173 — that one is taken by an unrelated project
  // on this machine, and plan-dashboard already owns 4322/4323.
  server: { port: 5273, strictPort: true },
  resolve: { tsconfigPaths: true },
  plugins: [
    cloudflare({ viteEnvironment: { name: "ssr" } }),
    tailwindcss(),
    reactRouter(),
  ],
});
