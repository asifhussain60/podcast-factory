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

  it("declares no Google scopes, so the defaults are what go out", () => {
    // Naming scopes here APPENDS to Better Auth's defaults rather than
    // replacing them — the authorization URL went out as
    // "email profile openid openid email profile" until this was removed.
    // Better Auth already requests exactly openid/email/profile, which is all
    // sign-in needs, so the correct configuration is none at all.
    expect(AUTH).not.toMatch(/^\s*scope:/m);
  });

  it("never widens beyond identity", () => {
    // Scopes are project-wide on the Google consent screen, which every future
    // Safina app shares. A sensitive scope added here would drag all of them
    // into a verification review.
    //
    // Comments are stripped first: the prose above names Drive and Calendar in
    // order to warn about them, and a check that cannot tell an example from an
    // instruction fires on its own documentation.
    const code = AUTH.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    expect(code).not.toMatch(/drive|calendar|contacts|gmail|cloud-platform|devstorage/i);
    expect(code).not.toMatch(/googleapis\.com\/auth\//);
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

describe("the deploy path cannot carry invented people", () => {
  // A row in `invite` is permission to sign in to the live site, so the hundred
  // fixture readers that make the access screen reviewable are exactly the kind
  // of data that must never travel. Four independent doors, each pinned here
  // because each is one edit away from opening.
  const SEED_PEOPLE = read("scripts/seed-people.mjs");
  const DEPLOY = read("../scripts/podcast/deploy_listener.sh");
  const PUBLISH = read("../scripts/podcast/publish_to_listener.py");

  it("seeds only the local database, with no remote mode to enable", () => {
    const calls = [...SEED_PEOPLE.matchAll(/"d1",\s*\n?\s*"execute",[\s\S]{0,200}?\]/g)];
    expect(calls.length).toBeGreaterThan(0);
    for (const [call] of calls) expect(call).toContain('"--local"');
    expect(SEED_PEOPLE).not.toMatch(/"--remote"/);
  });

  it("carries no fixture address in any migration", () => {
    // Migrations are the one thing the deploy applies to production BEFORE it
    // ships code. A seed written as a migration would hand a hundred fabricated
    // addresses the right to sign in, on the next deploy, silently.
    const { globSync } = require("node:fs") as typeof import("node:fs");
    const files = globSync("migrations/*.sql", {
      cwd: new URL("../", import.meta.url),
    }) as string[];
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      expect(read(file), `${file} names a reserved fixture domain`).not.toMatch(/\.invalid\b/);
    }
  });

  it("never names the invitation tables in the content publisher", () => {
    // publish_to_listener.py is the only writer the deploy runs against
    // production's data. It writes chapters, episodes and media; who may sign in
    // is not its business and must never become its business.
    expect(PUBLISH).not.toMatch(/\binvite\b/);
    expect(PUBLISH).not.toMatch(/\baccess_grant\b/);
  });

  it("verifies production itself, and fails closed when it cannot", () => {
    // The check that makes the three above belt-and-braces rather than the whole
    // argument: it reads the live invitation list and refuses to deploy on a
    // match OR on an answer it could not parse.
    expect(DEPLOY).toContain("Invented people");
    expect(DEPLOY).toMatch(/FROM invite WHERE email LIKE '%\.invalid'/);
    expect(DEPLOY).toMatch(/unparseable\)?\s*\n?\s*.*die|unparseable/);
    // Before the Worker, so a deploy that stops here has changed nothing.
    expect(DEPLOY.indexOf("Invented people")).toBeLessThan(DEPLOY.indexOf('step "Worker"'));
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
