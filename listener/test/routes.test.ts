import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * The route tree IS the access policy, so it gets a test.
 *
 * This catches the failure mode that actually happens: someone adds a route to
 * app/routes.ts at the top level, it looks fine, and it is silently ungated. A
 * grep for `env.DB` would not catch that; neither would a code review that was
 * looking at the new page rather than at its position.
 *
 * It reads the source rather than importing it because @react-router/dev/routes
 * is a build-time module.
 */

const SOURCE = readFileSync(new URL("../app/routes.ts", import.meta.url), "utf8");

/**
 * The complete list of routes reachable without signing in. Adding to it is a
 * deliberate act that shows up in a diff of this file.
 */
const PUBLIC_ROUTE_FILES = [
  "routes/sign-in.tsx",
  "routes/sign-out.tsx",
  "routes/no-access.tsx",
  "routes/favicon.ico.ts",
];

/** Every `"routes/..."` string, in source order. */
function routeFiles(source: string): string[] {
  return [...source.matchAll(/"(routes\/[^"]+)"/g)].map((m) => m[1]);
}

/** The slice of the file from the `_authed` layout to the end. */
function authedRegion(source: string): string {
  const start = source.indexOf('layout("routes/_authed.tsx"');
  expect(start, "routes.ts must declare the _authed layout").toBeGreaterThan(-1);
  return source.slice(start);
}

describe("route tree", () => {
  it("gates every route except the declared public ones", () => {
    const gated = new Set(routeFiles(authedRegion(SOURCE)));

    for (const file of routeFiles(SOURCE)) {
      if (PUBLIC_ROUTE_FILES.includes(file)) continue;
      if (file === "routes/_authed.tsx") continue;

      expect(
        gated.has(file),
        `${file} sits outside the _authed layout. Either nest it, or add it to ` +
          `PUBLIC_ROUTE_FILES here and be sure it is meant to be readable by anyone.`,
      ).toBe(true);
    }
  });

  it("keeps every admin route inside the admin layout", () => {
    const adminStart = SOURCE.indexOf('layout("routes/_authed._admin.tsx"');
    expect(adminStart).toBeGreaterThan(-1);
    const adminRegion = SOURCE.slice(adminStart);

    // Anything whose URL begins with admin must live in that region. `/api/auth`
    // is answered in workers/app.ts and never appears here at all.
    for (const [, urlPath, file] of SOURCE.matchAll(/route\("(admin[^"]*)",\s*"([^"]+)"/g)) {
      expect(
        adminRegion.includes(`"${file}"`),
        `${urlPath} (${file}) is not inside the admin layout`,
      ).toBe(true);
    }
  });

  it("does not route /api/auth — the Worker answers it before the router", () => {
    // If this ever appears here it means sign-in was moved into the tree, which
    // would force a carve-out in the authentication gate.
    expect(SOURCE).not.toMatch(/route\("api\/auth/);
  });
});

describe("error boundaries", () => {
  it("exist only on root", async () => {
    // A denied 404 renders findNearestBoundary(matches, routeId) — a CHILD
    // boundary when one exists — while a genuinely unmatched path renders
    // root's with empty loaderData. Two boundaries means two visibly different
    // 404s, and the difference reveals which slugs are real.
    const { glob } = await import("node:fs/promises");
    const offenders: string[] = [];

    for await (const entry of glob("app/routes/**/*.tsx")) {
      const text = readFileSync(entry, "utf8");
      if (/export\s+(function|const)\s+ErrorBoundary/.test(text)) offenders.push(entry);
    }

    expect(offenders, "only app/root.tsx may export an ErrorBoundary").toEqual([]);
  });
});
