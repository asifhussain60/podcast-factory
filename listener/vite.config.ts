import { reactRouter } from "@react-router/dev/vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { localMediaDevPlugin } from "./scripts/local-media-plugin.mts";

// Plugin order matters and matches Cloudflare's own react-router starter:
// cloudflare must register the workerd environment before reactRouter binds
// the SSR build to it. localMediaDevPlugin goes FIRST, ahead of even that —
// its middleware has to claim `/media/*` before @cloudflare/vite-plugin's own
// routing does, and Vite installs each plugin's `configureServer` middleware
// in plugins-array order (2026-08-16, see the plugin's own docstring for why
// `/media/*` needs a local-disk path at all).
//
// No vite-tsconfig-paths — Vite 8 resolves tsconfig `paths` natively, and the
// plugin now warns that it is redundant.
export default defineConfig({
  // 5273, not Vite's default 5173 — that one is taken by an unrelated project
  // on this machine, and plan-dashboard already owns 4322/4323.
  server: { port: 5273, strictPort: true },
  resolve: { tsconfigPaths: true },
  // Only ever reached through a dynamic `import()` (RichNoteEditor.tsx, kept
  // out of SSR on purpose). Vite's dev-time dep optimizer discovers a
  // dynamically-imported dependency graph lazily, on first hit, in its own
  // pass — and that pass produced a SECOND copy of `react` alongside the one
  // every statically-imported route already shares, which is exactly what
  // "Invalid hook call… more than one copy of React" means. Listing these
  // here puts them in the SAME up-front optimize pass as everything else, so
  // `@tiptap/react`'s `useEditor` resolves the one shared `react` instance.
  optimizeDeps: {
    include: ["@tiptap/core", "@tiptap/react", "@tiptap/starter-kit"],
  },
  plugins: [
    localMediaDevPlugin(),
    cloudflare({ viteEnvironment: { name: "ssr" } }),
    tailwindcss(),
    reactRouter(),
  ],
});
