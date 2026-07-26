// ESLint flat config — R0 gate of the clean-code hardening plan.
//
// Posture: auto-fixable + high-signal correctness rules start as errors;
// noisier judgment rules start as warnings (advisory) and ratchet to errors
// as R2 decomposes the editor surface. Formatting is Prettier's job —
// eslint-config-prettier disables all stylistic rules.
import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import astro from "eslint-plugin-astro";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist/",
      "node_modules/",
      ".astro/",
      ".visual-qa/",
      "src/data/*.json",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...astro.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Real findings, but the fixes change render timing — R2 (editor
      // decomposition) is where each one is addressed with a browser-verify.
      "react-hooks/set-state-in-effect": "warn",
      // The editor's deliberate mirror-refs-during-render pattern (PM plugins
      // read refs synchronously; the original documents why). The compiler
      // bails silently on the giant component but analyzes the extracted
      // hooks — ratchet to error as the pattern is redesigned post-R2.
      "react-hooks/refs": "warn",
    },
  },
  {
    rules: {
      // Ratchet set — warnings today (pre-R2 the editor surface trips these
      // heavily); flip to "error" as R2 lands.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-empty": ["warn", { allowEmptyCatch: true }],
      // `cond ? add() : delete()` and `x && f()` are established idioms here.
      "@typescript-eslint/no-unused-expressions": [
        "error",
        { allowShortCircuit: true, allowTernary: true },
      ],
      // Arabic-Unicode regex ranges include chars ESLint deems irregular.
      "no-irregular-whitespace": ["error", { skipRegExps: true }],
    },
  },
  {
    // The reusable packages/* workspaces. Held STRICTER than the app: the
    // ratchet above exists because the pre-R2 editor surface trips those rules
    // heavily, and a package published for other projects to consume has no such
    // history to grandfather. A library that ships `any` exports its uncertainty
    // to every consumer.
    files: ["packages/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-empty": ["error", { allowEmptyCatch: true }],
    },
  },
  {
    // Node-side scripts (smoke, snapshots, mermaid render, lint-views).
    // document/window/fetch cover code inside Playwright page.evaluate().
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      globals: {
        process: "readonly",
        console: "readonly",
        Buffer: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        AbortController: "readonly",
        TextDecoder: "readonly",
        TextEncoder: "readonly",
        document: "readonly",
        window: "readonly",
        // Same reason as document/window above: the layout invariants the smoke
        // run asserts are measured INSIDE page.evaluate(), so they read computed
        // styles in the browser context, not in Node.
        getComputedStyle: "readonly",
        Node: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
  eslintConfigPrettier,
);
