// ESLint flat config — closes the gap `CQ-NO-LINT` reported (2026-08-16 repo
// audit): this app had 106 source files with nothing but the type checker
// looking at them. Modelled on plan-dashboard/eslint.config.js (same pinned
// versions, same posture) minus what this app doesn't have — no Astro plugin
// (React Router, not Astro), no packages/* workspace tier.
//
// Posture: correctness rules start as errors; the two React-hooks rules the
// Astro Site ratchets (set-state-in-effect, refs) start as warnings here too,
// pending the same kind of review before flipping — this app has not had that
// review yet, so starting at "error" would be a guess dressed as a gate.
// Formatting is Prettier's job — eslint-config-prettier disables every
// stylistic rule.
import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "**/build/",
      "**/node_modules/",
      ".wrangler/",
      "worker-configuration.d.ts",
      "react-router.config.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-empty": ["warn", { allowEmptyCatch: true }],
      "@typescript-eslint/no-unused-expressions": [
        "error",
        { allowShortCircuit: true, allowTernary: true },
      ],
      // Arabic-script literals appear in test fixtures and companion content.
      "no-irregular-whitespace": ["error", { skipRegExps: true }],
    },
  },
  {
    // Dev/build/test scripts — smoke, controls, security-smoke, the local
    // media plugin. Node-side, not app code; same Node-global allowance
    // plan-dashboard's scripts/**/*.mjs block uses.
    files: ["scripts/**/*.{mjs,mts,ts}"],
    languageOptions: {
      globals: {
        process: "readonly",
        console: "readonly",
        Buffer: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        fetch: "readonly",
        crypto: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        AbortController: "readonly",
        TextDecoder: "readonly",
        TextEncoder: "readonly",
        document: "readonly",
        window: "readonly",
        // Playwright's page.evaluate() callbacks in smoke.mjs/controls.mjs/
        // shots.mjs run in a real browser context.
        getComputedStyle: "readonly",
        Node: "readonly",
        PointerEvent: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "test/**/*.ts"],
    languageOptions: {
      globals: {
        process: "readonly",
        console: "readonly",
        Buffer: "readonly",
      },
    },
  },
  eslintConfigPrettier,
);
