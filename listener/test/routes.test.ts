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

  it("puts requireUnitAccess on every route that names a book", async () => {
    // Being inside `_authed` proves the caller is INVITED; it says nothing about
    // whether they were given THIS book. Every `book/:slug` route therefore
    // needs its own gate, and it must be middleware rather than a loader — the
    // `_routes` single-fetch filter can skip a loader.
    //
    // Written as a check on the route FILES rather than on routes.ts, because
    // the declaration lives in the file, and the failure this catches is a new
    // per-book surface (a resource route, a print view) that inherits the
    // invited gate and quietly serves any book to anyone signed in.
    const { readFile } = await import("node:fs/promises");

    for (const [, urlPath, file] of SOURCE.matchAll(/route\("(book\/[^"]*)",\s*"([^"]+)"/g)) {
      const text = await readFile(`app/${file}`, "utf8");
      expect(
        /middleware[^=]*=\s*\[[^\]]*requireUnitAccess/.test(text),
        `${urlPath} (${file}) does not declare requireUnitAccess as middleware`,
      ).toBe(true);
    }
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

    // `.ts` as well as `.tsx`. Resource routes are plain `.ts` — the marks
    // endpoint is one — and the original glob could not see them, so a boundary
    // exported from one would have gone unnoticed by the test written to
    // prevent exactly that.
    for await (const entry of glob("app/routes/**/*.{ts,tsx}")) {
      const text = readFileSync(entry, "utf8");
      if (/export\s+(function|const)\s+ErrorBoundary/.test(text)) offenders.push(entry);
    }

    expect(offenders, "only app/root.tsx may export an ErrorBoundary").toEqual([]);
  });
});
