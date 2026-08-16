import { describe, expect, it } from "vitest";

import {
  SIMULATE_COOKIE,
  simulatedEmail,
  startSimulating,
  stopSimulating,
} from "../app/server/simulate.server";

/**
 * The cookie that makes the site show somebody else's library.
 *
 * What is worth pinning here is not that a cookie round-trips. It is the three
 * properties that keep a deliberate lie about who is reading from becoming a way
 * in: the value is normalized before anything looks up a grant with it, a value
 * that is not an address produces nothing at all, and the attributes are the
 * ones that stop a script or another site from setting it.
 *
 * The fourth property — that the cookie is only ever CONSULTED for a real
 * administrator, which is the actual gate — lives in middleware/session.ts and
 * is fired for real by scripts/security-smoke.mjs, because it is a claim about
 * how a request is dispatched rather than about this module.
 */

const req = (cookie?: string) =>
  new Request(
    "https://example.com/",
    cookie ? { headers: { Cookie: cookie } } : undefined,
  );

describe("reading the simulation cookie", () => {
  it("finds the address among other cookies", () => {
    const header = `theme=dark; ${SIMULATE_COOKIE}=${encodeURIComponent("reader@example.com")}; x=1`;
    expect(simulatedEmail(req(header))).toBe("reader@example.com");
  });

  it("normalizes it, so the grant lookup can possibly match", () => {
    // Grants are keyed on the folded form. A raw value here would look up an
    // address that cannot exist and present as "this person has nothing" —
    // a wrong answer that looks exactly like a right one.
    const header = `${SIMULATE_COOKIE}=${encodeURIComponent("A.Reader+book@Gmail.com")}`;
    expect(simulatedEmail(req(header))).toBe("areader@gmail.com");
  });

  it("is nothing when absent", () => {
    expect(simulatedEmail(req())).toBeNull();
    expect(simulatedEmail(req("theme=dark"))).toBeNull();
  });

  it("is nothing when the value is not an address", () => {
    expect(simulatedEmail(req(`${SIMULATE_COOKIE}=`))).toBeNull();
    expect(simulatedEmail(req(`${SIMULATE_COOKIE}=not-an-address`))).toBeNull();
    expect(simulatedEmail(req(`${SIMULATE_COOKIE}=%E0%A4%A`))).toBeNull();
  });
});

describe("writing the simulation cookie", () => {
  const https = new URL("https://podcast-factory.safinaverse.com/admin");
  const local = new URL("http://localhost:5273/admin");

  it("cannot be read or set by a script, or sent from another site", () => {
    const header = startSimulating("reader@example.com", https);
    expect(header).toContain("HttpOnly");
    expect(header).toContain("SameSite=Lax");
    expect(header).toContain("Path=/");
  });

  it("expires on its own, so a forgotten simulation resolves itself", () => {
    expect(startSimulating("reader@example.com", https)).toMatch(/Max-Age=\d+/);
  });

  it("is Secure over https and not over plain-http localhost", () => {
    // Not a preference: a Secure cookie is never stored by a browser on
    // http://localhost, so the development server would silently never simulate.
    expect(startSimulating("reader@example.com", https)).toContain("Secure");
    expect(startSimulating("reader@example.com", local)).not.toContain(
      "Secure",
    );
  });

  it("clears with the same attributes, or the browser keeps the old one", () => {
    const gone = stopSimulating(https);
    expect(gone).toContain("Max-Age=0");
    expect(gone).toContain("Path=/");
    expect(gone).toContain("HttpOnly");
  });

  it("survives an address that needs encoding", () => {
    const header = startSimulating("a+b@example.com", https);
    expect(simulatedEmail(req(header.split(";")[0]))).toBe("a+b@example.com");
  });
});
