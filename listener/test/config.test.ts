import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { normalizeEmail } from "../app/server/email.server";

/**
 * Assertions over configuration that is security-relevant but easy to change by
 * accident. Each of these guards a specific way the design fails silently.
 */

const read = (p: string) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

const AUTH = read("app/server/auth.server.ts");
const WRANGLER = read("wrangler.jsonc");
const RR_CONFIG = read("react-router.config.ts");
const ACCESS = read("app/server/access.server.ts");
const SEED = read("migrations/0003_seed_catalog.sql");

describe("Better Auth configuration", () => {
  it("keeps the session cookie cache disabled", () => {
    // With it on, getSession answers from a signed cookie without touching the
    // database — so revoking an invite would keep working for the whole cache
    // window even though the gate re-checks every request.
    expect(AUTH).toMatch(/cookieCache:\s*\{\s*enabled:\s*false\s*\}/);
  });

  it("keeps self-service email change disabled", () => {
    // `user.email` IS the privilege bit: admin is an email comparison and grants
    // key on email. A self-service email change is a self-service privilege
    // change.
    expect(AUTH).toMatch(/changeEmail:\s*\{\s*enabled:\s*false\s*\}/);
  });

  it("requests only the three identity scopes from Google", () => {
    const scopes = /scope:\s*\[([^\]]*)\]/.exec(AUTH)?.[1] ?? "";
    expect(scopes).toContain("openid");
    expect(scopes).toContain("email");
    expect(scopes).toContain("profile");
    expect(scopes).not.toMatch(/drive|calendar|contacts|gmail/i);
  });
});

describe("admin identity", () => {
  it("pairs ADMIN_EMAIL with the seeded invite and the database triggers", () => {
    // Three places name the administrator and all three must agree: the Worker
    // var the check compares against, the invite row that lets that person past
    // the gate ABOVE the admin gate, and the triggers that stop the address
    // being squatted. A mismatch either locks Asif out or leaves a hole.
    const configured = /"ADMIN_EMAIL":\s*"([^"]+)"/.exec(WRANGLER)?.[1];
    expect(configured, "ADMIN_EMAIL must be set in wrangler.jsonc").toBeTruthy();

    const normalized = normalizeEmail(configured!);
    expect(SEED, "the admin needs a seeded invite or the app ships locked").toContain(
      `('${normalized}', `,
    );
    expect(read("migrations/0002_access.sql")).toContain(`NEW.email = '${normalized}'`);
  });

  it("sets ADMIN_EMAIL in every named environment", () => {
    // Wrangler REPLACES rather than merges `vars` in a named environment, so an
    // env that omits it would leave the admin check comparing against undefined.
    const envBlocks = WRANGLER.split(/"env"\s*:/)[1] ?? "";
    const named = [...envBlocks.matchAll(/"vars"\s*:\s*\{/g)];
    for (let i = 0; i < named.length; i++) {
      expect(envBlocks).toContain('"ADMIN_EMAIL"');
    }
    expect(named.length, "staging environment should declare its own vars").toBeGreaterThan(0);
  });
});

describe("route discovery", () => {
  it("does not stand up an unauthenticated /__manifest endpoint", () => {
    // With ssr:true the default is `lazy`, which serves /__manifest BEFORE route
    // matching (server.js:91-93) where no middleware can gate it.
    expect(RR_CONFIG).toMatch(/routeDiscovery:\s*\{\s*mode:\s*"initial"\s*\}/);
  });
});

describe("privilege bits", () => {
  it("writes open_to_all and status only through the admin-session path", () => {
    // The phase-3 publish endpoint will authenticate with a bearer token, not a
    // session. If it could write these columns, leaking that token would let an
    // attacker open every book to everyone. This asserts the ONLY writer of
    // open_to_all is the dedicated admin function.
    const writers = [...ACCESS.matchAll(/UPDATE content_unit SET ([^\s]+)/g)].map((m) => m[1]);
    expect(writers).toEqual(["open_to_all"]);
    expect(ACCESS).toContain("export async function setOpenToAll");
  });

  it("keeps the published filter inside the resolver, not in callers", () => {
    // Hoisting it to callers is how a draft with open_to_all=1 leaks through a
    // request that skipped whichever caller remembered to apply it.
    expect(ACCESS).toMatch(/WHERE u\.status = 'published'/);
  });
});
