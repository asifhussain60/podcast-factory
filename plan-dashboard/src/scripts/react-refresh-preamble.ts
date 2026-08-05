/**
 * react-refresh-preamble.ts — dev-only React Fast Refresh bootstrap for pages
 * that use React WITHOUT declaring an Astro island.
 *
 * WHY THIS EXISTS. @vitejs/plugin-react rewrites every module that exports a
 * React component to call `window.$RefreshReg$` / `$RefreshSig$` at load, and
 * those globals are installed by a preamble script. In an Astro app that
 * preamble is injected as a "before-hydration" script (see
 * node_modules/@astrojs/react/dist/index.js), which Astro only emits on pages
 * that render at least one hydrated island.
 *
 * The Book Composer has none. Every React surface it shows — the Companion
 * panel, the AI tools, the details tab — is mounted imperatively with
 * `createRoot`, because each one is handed a live ProseMirror editor and a
 * chapter that changes under it, and an island cannot be given new props after
 * mount. The page nonetheless booted for months, because two unrelated
 * `client:only="react"` panels happened to sit in its drawer and dragged the
 * preamble in with them. Removing those panels (2026-07-29) took the preamble
 * with them, and book-composer.ts died on its first React import — the whole
 * page rendered as inert server HTML with no chapter, no editor and no panel.
 *
 * So the dependency is declared here instead of inherited by accident. Import
 * this FIRST from any page script that pulls in React; ES module imports are
 * evaluated in order, so the globals exist before the components load.
 *
 * Dev only. Fast Refresh does not exist in a production build, `import.meta.env.DEV`
 * is statically false there, and the whole block is dropped.
 */
declare global {
  interface Window {
    $RefreshReg$?: () => void;
    $RefreshSig$?: () => (type: unknown) => unknown;
  }
}

if (import.meta.env.DEV) {
  // SYNCHRONOUS, and that is the whole design. `import "preamble"; import
  // "book-composer"` does NOT make the second wait for the first if the first
  // has a top-level await: per the module evaluation algorithm an async
  // dependency only suspends its PARENT, and the sibling after it evaluates
  // immediately — so an awaited runtime import here still lost the race to
  // react-dom, and the page failed exactly as it did with no preamble at all.
  // These two assignments are the only part the component modules need: their
  // injected epilogue throws "can't detect preamble" when $RefreshReg$ is
  // missing, and calls $RefreshSig$ while the module body runs.
  window.$RefreshReg$ = () => {};
  window.$RefreshSig$ = () => (type: unknown) => type;

  // Best-effort, deliberately NOT awaited: this is what lets an edited React
  // component re-render in place instead of reloading the page. If it lands
  // after react-dom has registered, the worst case is that a React edit on this
  // page costs a full reload — a dev-time convenience, never correctness. The
  // specifier is a dev-only virtual module, so @vite-ignore keeps the production
  // build from trying to resolve a path that has no file.
  // Held in a variable, not written inline: `/@react-refresh` is a module Vite
  // synthesizes at request time and no file on disk answers to it, so a literal
  // specifier fails `astro check` with "cannot find module" even though the
  // import resolves perfectly in the browser.
  const runtimeSpecifier = "/@react-refresh";
  void import(/* @vite-ignore */ runtimeSpecifier)
    .then((m: { injectIntoGlobalHook?: (w: Window) => void }) =>
      m.injectIntoGlobalHook?.(window),
    )
    .catch(() => {
      /* fast refresh unavailable — the page still runs */
    });
}

export {};
